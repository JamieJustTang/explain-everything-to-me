import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'components' / 'daily-journal' / 'journal.py'
SPEC = importlib.util.spec_from_file_location('daily_journal', SCRIPT)
journal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(journal)


class JournalTest(unittest.TestCase):
    def event(self):
        return {'key':'2026-10-03:/example/workspace:question-v1','date':'2026-10-03','kind':'artifact',
                'title':'A draft diagram','detail':'A first draft.','project':'Example',
                'artifact':'diagram.svg','readiness':'discussable','workrefs':['codex/example/1']}

    def test_import_deduplicates_and_preserves_manual_edit(self):
        data = journal.blank()
        event = self.event()
        self.assertEqual(journal.import_events(data, {'events':[event]})['created'], 1)
        item = data['entries'][0]
        journal.action(data, {'action':'update','id':item['id'],**{**event,'title':'My own title','readiness':'private'}})
        event['title'] = 'Changed by agent'
        event['detail'] = 'New verified fact.'
        event['workrefs'] = ['codex/example/2']
        self.assertEqual(journal.import_events(data, {'events':[event]})['updated'], 1)
        self.assertEqual(len(data['entries']), 1)
        self.assertEqual(item['title'], 'My own title')
        self.assertEqual(item['detail'], 'New verified fact.')
        self.assertEqual(item['workrefs'], ['codex/example/1','codex/example/2'])
        event['workrefs'] = ['codex/example/1']
        journal.import_events(data, {'events':[event]})
        self.assertEqual(item['workrefs'], ['codex/example/1','codex/example/2'])

    def test_agent_requires_evidence_and_cannot_claim_shared(self):
        data = journal.blank()
        event = self.event()
        event['workrefs'] = []
        with self.assertRaises(ValueError):
            journal.import_events(data, {'events':[event]})
        event['workrefs'] = ['codex/example/1']
        event['readiness'] = 'shared'
        with self.assertRaises(ValueError):
            journal.import_events(data, {'events':[event]})
        self.assertEqual(data['entries'], [])

    def test_deleted_agent_entry_does_not_reappear(self):
        data = journal.blank()
        event = self.event()
        journal.import_events(data, {'events':[event]})
        journal.action(data, {'action':'delete','id':data['entries'][0]['id']})
        self.assertEqual(journal.import_events(data, {'events':[event]})['skipped'], 1)
        self.assertFalse(data['entries'])

    def test_storage_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.json'
            journal.write(path, journal.blank())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(journal.read(path)['version'], 1)

    def test_narrative_links_to_same_day_artifacts(self):
        data = journal.blank()
        journal.import_events(data, {'events': [self.event()]})
        item = data['entries'][0]
        initial_version = item['updated_at']
        journal.import_events(data, {'events': [self.event()]})
        self.assertEqual(item['updated_at'], initial_version)
        digest = {'date': '2026-10-03', 'title': 'A day with a visible result',
                  'lead': 'The diagram made the question discussable.',
                  'sections': [{'heading': 'A first structure', 'body': f'The diagram [[artifact:{item["id"]}]] connects the main ideas.',
                                'entry_ids': [item['id']]}],
                  'closing': 'Check one boundary next.',
                  'letter': {'salutation': 'Dear researcher', 'body': f'Show [[artifact:{item["id"]}]] to a colleague.',
                             'recipient': 'A colleague', 'suggested_ask': 'What is missing?',
                             'entry_ids': [item['id']]}}
        result = journal.compose(data, digest)
        self.assertEqual(result['entry_versions'][item['id']], item['updated_at'])
        self.assertEqual(data['digests']['2026-10-03']['letter']['entry_ids'], [item['id']])
        digest['sections'][0]['body'] = 'The diagram connects the main ideas.'
        with self.assertRaisesRegex(ValueError, 'inside the prose'):
            journal.compose(data, digest)
        digest['sections'][0]['body'] = f'The diagram [[artifact:{item["id"]}]] connects the main ideas.'
        digest['sections'][0]['entry_ids'] = ['not-an-entry']
        with self.assertRaisesRegex(ValueError, 'same|date'):
            journal.compose(data, digest)

    def test_ready_to_share_can_note_no_artifact(self):
        data = journal.blank()
        data['entries'].append({'id': 'insight', 'date': '2026-10-03', 'artifact': '',
                                'updated_at': journal.timestamp()})
        payload = {'date': '2026-10-03', 'title': 'An insight', 'lead': 'A thought.',
                   'sections': [{'heading': 'A thought', 'body': 'A thought.', 'entry_ids': ['insight']}],
                   'coverage_note': 'Accessible local sessions were reviewed.',
                   'letter': {'body': 'Wait for a visible artifact.', 'entry_ids': ['insight']}}
        result = journal.compose(data, payload)
        self.assertEqual(result['coverage_note'], 'Accessible local sessions were reviewed.')
        self.assertEqual(result['letter']['body'], 'Wait for a visible artifact.')
        data['entries'].append({'id': 'output', 'date': '2026-10-03', 'artifact': 'A diagram',
                                'updated_at': journal.timestamp()})
        with self.assertRaisesRegex(ValueError, 'artifact'):
            journal.compose(data, payload)

    def test_example_artifact_resolution(self):
        self.assertEqual(journal.artifact_file({'artifact_target': 'demo:hypotheses.md'}).name, 'hypotheses.md')
        self.assertIsNone(journal.artifact_file({'artifact_target': 'demo:../journal.py'}))


if __name__ == '__main__':
    unittest.main()
