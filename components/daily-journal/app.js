const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const localDay = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const state = {data:null, date:localDay(), editing:null};
const labels = {progress:'推进',artifact:'留下',insight:'发现',share:'交流'};
const readiness = {private:'还在加工',discussable:'可找人讨论',shared:'已经交流'};
function toast(message){const node=$('#toast');node.textContent=message;node.style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>node.style.display='none',3800);}
function entries(){return (state.data?.entries||[]).filter(entry=>entry.date===state.date).slice().reverse();}
function artifactLink(entry, className='artifact-link') {
  const target=entry.artifact_target||'';
  const external=/^https?:\/\//i.test(target);
  const local=target.startsWith('/')||target.startsWith('demo:');
  const label=esc(entry.artifact||entry.title);
  if (!external&&!local) return entry.artifact?`<span class="artifact-name">${label}</span>`:'';
  const href=external?target:`/api/artifact/${encodeURIComponent(entry.id)}`;
  return `<a class="${className}" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${label}<span aria-hidden="true"> ↗</span></a>`;
}
function paragraphs(value){return String(value||'').split(/\n\s*\n/).filter(Boolean).map(part=>`<p>${esc(part).replace(/\n/g,'<br>')}</p>`).join('');}
function linkedEntries(ids, byId){return (ids||[]).map(id=>byId.get(id)).filter(Boolean).filter(entry=>entry.artifact).map(entry=>artifactLink(entry)).join('');}
function render(){
  const d=new Date(`${state.date}T12:00:00`), items=entries(), byId=new Map(items.map(item=>[item.id,item]));
  const digest=state.data?.digests?.[state.date];
  $('#date-title').textContent=d.toLocaleDateString('zh-CN',{year:'numeric',month:'long',day:'numeric',weekday:'long'});
  $('#count').textContent=items.length;
  for(const kind of ['progress','artifact','insight']) $(`#count-${kind}`).textContent=items.filter(x=>x.kind===kind).length;
  $('#count-discussable').textContent=items.filter(x=>x.readiness==='discussable'||x.readiness==='shared').length;
  $('#headline-text').textContent=digest?.title||(items.length?'素材已留下，今日日志还待撰写。':'今天还没有记录。');
  $('#coverage-text').textContent=digest?.lead||(items.length?'已有条目，但还没有经过原文核对的叙事摘要。':'写下一件小事，轨迹就从这里开始。');
  const stale=digest&&Object.entries(digest.entry_versions||{}).some(([id,version])=>byId.get(id)?.updated_at!==version);
  $('#digest-status').textContent=digest?(stale?'素材有变化 · 建议重写':'已整理成文'):'待撰写';
  $('#digest-body').innerHTML=digest?`${(digest.sections||[]).map((section,index)=>`<section class="essay-section"><span class="section-number">${String(index+1).padStart(2,'0')}</span><h2>${esc(section.heading)}</h2>${paragraphs(section.body)}<div class="essay-links">${linkedEntries(section.entry_ids,byId)}</div></section>`).join('')}<div class="essay-closing"><span class="small-cap">KEEP THIS</span>${paragraphs(digest.closing)}</div>`:'<div class="empty-essay"><h2>这一天，还没有写成文章。</h2><p>条目只是材料。让 Agent 阅读当天会话、核对产物，再写出起因、转折、留下了什么和下一步。</p></div>';
  const letter=digest?.letter;
  $('#letter-body').innerHTML=letter?`<h2>${esc(letter.salutation||'写给你的交流建议')}</h2><div class="letter-prose">${paragraphs(letter.body)}</div>${letter.recipient?`<div class="letter-detail"><span>适合找谁</span><strong>${esc(letter.recipient)}</strong></div>`:''}${letter.suggested_ask?`<div class="letter-detail"><span>可以问什么</span><strong>${esc(letter.suggested_ask)}</strong></div>`:''}<div class="letter-links">${linkedEntries(letter.entry_ids,byId)}</div><p class="letter-note">这里只给建议；不会自动发布或联系他人。</p>`:'<h2>先看清手里的东西</h2><p>当今日日志写好后，这里会给你一封具体的建议信：哪些成果值得展示，适合找谁，以及最好问什么。不会自动发送。</p>';
  $('#entry-list').innerHTML=items.length?items.map(x=>`<article class="entry"><span class="entry-kind ${esc(x.kind)}">${labels[x.kind]||'记录'}</span><div><h3><button data-id="${esc(x.id)}">${esc(x.title)}</button></h3>${x.detail?`<p>${esc(x.detail)}</p>`:''}<div class="entry-meta"><span>${esc(x.project||'未归类')}</span><span>${esc(readiness[x.readiness]||'')}</span>${x.artifact?artifactLink(x):''}${x.workrefs?.length?`<span>证据：${x.workrefs.map(esc).join(' · ')}</span>`:''}</div></div></article>`).join(''):'<div class="empty">还没有这一天的记录。</div>';
  const artifacts=items.filter(x=>x.artifact);
  $('#artifact-list').innerHTML=artifacts.length?artifacts.map(x=>`<div class="mini"><strong>${esc(x.title)}</strong><div>${artifactLink(x)}</div><small>${esc(x.project||'未归类')}</small></div>`).join(''):'<div class="empty">这一天还没有关联产物。</div>';
  const dates=[...new Set((state.data?.entries||[]).map(x=>x.date))].sort().reverse();
  $('#archive-days').innerHTML=dates.length?dates.map(date=>{const daily=state.data.entries.filter(x=>x.date===date);return `<button data-date="${esc(date)}"><strong>${esc(date)}</strong><span>${daily.length} 条记录 · ${daily.filter(x=>x.kind==='artifact').length} 个成果 · ${daily.filter(x=>x.readiness==='discussable'||x.readiness==='shared').length} 个可交流</span></button>`}).join(''):'<div class="empty">还没有过往记录。</div>';
}
async function load(){try{const r=await fetch('/api/data',{cache:'no-store'});if(!r.ok)throw Error('读取日志失败');state.data=await r.json();render();}catch(e){toast(e.message);}}
function edit(entry=null){state.editing=entry;$('#dialog-title').textContent=entry?'编辑这一步':'记下一步';const form=$('#entry-form');for(const field of ['date','kind','title','detail','project','artifact','artifact_target','readiness']) form.elements[field].value=entry?.[field]??({date:state.date,kind:'progress',readiness:'private'}[field]||'');$('#delete-entry').hidden=!entry;$('#editor').showModal();}
async function mutate(payload){const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const body=await r.json();if(!r.ok)throw Error(body.error||'保存失败');state.data=body;render();}
$('#add-entry').addEventListener('click',()=>edit());
$('#entry-list').addEventListener('click',event=>{const b=event.target.closest('[data-id]');if(b)edit(state.data.entries.find(x=>x.id===b.dataset.id));});
$('#entry-form').addEventListener('submit',async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(event.target).entries());values.workrefs=state.editing?.workrefs||[];try{await mutate({action:state.editing?'update':'create',id:state.editing?.id,...values});$('#editor').close();toast('这一步已保存到本机');}catch(e){toast(e.message);}});
$('#delete-entry').addEventListener('click',async()=>{if(!state.editing||!confirm(`删除“${state.editing.title}”？`))return;try{await mutate({action:'delete',id:state.editing.id});$('#editor').close();toast('记录已删除');}catch(e){toast(e.message);}});
for(const id of ['close-dialog','cancel-entry']) $(`#${id}`).addEventListener('click',()=>$('#editor').close());
function shift(days){const d=new Date(`${state.date}T12:00:00`);d.setDate(d.getDate()+days);state.date=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;render();}
$('#archive-days').addEventListener('click',event=>{const button=event.target.closest('[data-date]');if(button){state.date=button.dataset.date;$('#archive-panel').hidden=true;render();}});
$('#prev-day').addEventListener('click',()=>shift(-1));$('#next-day').addEventListener('click',()=>shift(1));$('#back-today').addEventListener('click',()=>{state.date=localDay();render()});$('#today-nav').addEventListener('click',()=>{state.date=localDay();render()});$('#archive-nav').addEventListener('click',()=>{$('#archive-panel').hidden=!$('#archive-panel').hidden;$('#archive-panel').scrollIntoView({behavior:'smooth',block:'start'});});
load();
