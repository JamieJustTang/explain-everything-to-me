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


if __name__ == '__main__':
    unittest.main()
