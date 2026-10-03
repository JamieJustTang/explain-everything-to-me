const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const localDay = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const state = {data:null, date:localDay(), editing:null};
const labels = {progress:'推进',artifact:'留下',insight:'发现',share:'交流'};
const readiness = {private:'还在加工',discussable:'可找人讨论',shared:'已经交流'};
function toast(message){const node=$('#toast');node.textContent=message;node.style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>node.style.display='none',3800);}
function entries(){return (state.data?.entries||[]).filter(entry=>entry.date===state.date).slice().reverse();}
function render(){
  const d=new Date(`${state.date}T12:00:00`), items=entries();
  $('#date-title').textContent=d.toLocaleDateString('zh-CN',{year:'numeric',month:'long',day:'numeric',weekday:'long'});
  $('#count').textContent=items.length;
  for(const kind of ['progress','artifact','insight']) $(`#count-${kind}`).textContent=items.filter(x=>x.kind===kind).length;
  $('#count-discussable').textContent=items.filter(x=>x.readiness==='discussable'||x.readiness==='shared').length;
  const top=items.find(x=>x.kind==='artifact')||items[0];
  $('#headline-text').textContent=top ? `今天留下了：${top.title}` : '今天还没有记录。';
  $('#coverage-text').textContent=top ? `${items.length} 条可回看的记录 · ${items.filter(x=>x.workrefs?.length).length} 条附有会话证据` : '写下一件小事，轨迹就从这里开始。';
  $('#entry-list').innerHTML=items.length ? items.map(x=>`<article class="entry"><span class="entry-kind ${esc(x.kind)}">${labels[x.kind]||'记录'}</span><div><h3><button data-id="${esc(x.id)}">${esc(x.title)}</button></h3>${x.detail?`<p>${esc(x.detail)}</p>`:''}<div class="entry-meta"><span>${esc(x.project||'未归类')}</span><span>${esc(readiness[x.readiness]||'')}</span>${x.artifact?`<span>成果：${esc(x.artifact)}</span>`:''}${x.workrefs?.length?`<span>证据：${x.workrefs.map(esc).join(' · ')}</span>`:''}</div></div></article>`).join('') : '<div class="empty">还没有这一天的记录。你可以手写一条，或让 Agent 在读完会话后整理。</div>';
  const share=items.filter(x=>x.readiness==='discussable'||x.readiness==='shared');
  $('#share-list').innerHTML=share.length?share.map(x=>`<div class="mini"><strong>${esc(x.title)}</strong><small>${esc(readiness[x.readiness])} · ${esc(x.project||'未归类')}</small></div>`).join(''):'<div class="empty">还没有标记为可交流的成果。</div>';
  const artifacts=(state.data?.entries||[]).filter(x=>x.kind==='artifact'||x.artifact).slice(-6).reverse();
  $('#artifact-list').innerHTML=artifacts.length?artifacts.map(x=>`<div class="mini"><strong>${esc(x.title)}</strong><small>${esc(x.date)} · ${esc(x.artifact||'记录已留在本页')}</small></div>`).join(''):'<div class="empty">还没有留下可积累对象。</div>';
  const dates=[...new Set((state.data?.entries||[]).map(x=>x.date))].sort().reverse();
  $('#archive-days').innerHTML=dates.length?dates.map(date=>{const daily=state.data.entries.filter(x=>x.date===date);return `<button data-date="${esc(date)}"><strong>${esc(date)}</strong><span>${daily.length} 条记录 · ${daily.filter(x=>x.kind==='artifact').length} 个成果 · ${daily.filter(x=>x.readiness==='discussable'||x.readiness==='shared').length} 个可交流</span></button>`}).join(''):'<div class="empty">还没有过往记录。</div>';
}
async function load(){try{const r=await fetch('/api/data',{cache:'no-store'});if(!r.ok)throw Error('读取日志失败');state.data=await r.json();render();}catch(e){toast(e.message);}}
function edit(entry=null){state.editing=entry;$('#dialog-title').textContent=entry?'编辑这一步':'记下一步';const form=$('#entry-form');form.elements.date.value=entry?.date||state.date;form.elements.kind.value=entry?.kind||'progress';form.elements.title.value=entry?.title||'';form.elements.detail.value=entry?.detail||'';form.elements.project.value=entry?.project||'';form.elements.artifact.value=entry?.artifact||'';form.elements.readiness.value=entry?.readiness||'private';$('#delete-entry').hidden=!entry;$('#editor').showModal();}
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
