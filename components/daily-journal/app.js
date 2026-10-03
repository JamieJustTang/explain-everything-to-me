const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const localDay = () => { const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
const state = {data:null, date:localDay(), month:localDay().slice(0,7), editing:null};
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
function inlineArtifact(entry){return artifactLink(entry,'inline-citation');}
function paragraphs(value, byId, ids=[]){
  const allowed=new Set(ids);
  const cited=new Set([...String(value||'').matchAll(/\[\[artifact:([\w-]+)\]\]/g)].map(match=>match[1]));
  const missing=ids.map(id=>byId?.get(id)).filter(entry=>entry?.artifact&&!cited.has(entry.id));
  const parts=String(value||'').split(/\n\s*\n/).filter(Boolean);
  return parts.map((part,index)=>{
    let at=0, result='';
    for(const match of part.matchAll(/\[\[artifact:([\w-]+)\]\]/g)){
      result+=esc(part.slice(at,match.index)).replace(/\n/g,'<br>');
      const entry=allowed.has(match[1])?byId?.get(match[1]):null;
      result+=entry?.artifact?inlineArtifact(entry):esc(match[0]);
      at=match.index+match[0].length;
    }
    result+=esc(part.slice(at)).replace(/\n/g,'<br>');
    if(index===parts.length-1&&missing.length) result+=` <span class="legacy-citations">（参见 ${missing.map(inlineArtifact).join('、')}）</span>`;
    return `<p>${result}</p>`;
  }).join('');
}
const EMOJI=['🌱','🌿','🌻','🍀','🌸','🍎','🍋','🍓','🪻','🌼','🦋','🐝','⭐','✨','🪴','🍄','🌙','☀️','🪺','🎈','🧩','📚','✏️','🪁'];
const TYPE_LINE_SECONDS=.84;
function dayEmoji(date){let hash=2166136261;for(const char of date){hash^=char.charCodeAt(0);hash=Math.imul(hash,16777619);}return EMOJI[(hash>>>0)%EMOJI.length];}
function calendar(){
  const [year,month]=state.month.split('-').map(Number), first=new Date(year,month-1,1), count=new Date(year,month,0).getDate();
  const dates=new Set((state.data?.entries||[]).map(item=>item.date));
  $('#calendar-month').textContent=first.toLocaleDateString('zh-CN',{year:'numeric',month:'long'});
  const leading=(first.getDay()+6)%7;
  $('#calendar-days').innerHTML=Array.from({length:leading},()=>'<span class="calendar-gap"></span>').join('')+Array.from({length:count},(_,index)=>{
    const n=index+1, date=`${year}-${String(month).padStart(2,'0')}-${String(n).padStart(2,'0')}`, active=dates.has(date);
    const classes=['calendar-day',active?'recorded':'empty-day',date===state.date?'selected':'',date===localDay()?'today':''].filter(Boolean).join(' ');
    return `<button class="${classes}" data-date="${date}" aria-label="${date}${active?'，有记录':'，无记录'}" aria-pressed="${date===state.date}"><span class="day-icon" aria-hidden="true">${active?dayEmoji(date):''}</span><span class="day-num">${n}</span></button>`;
  }).join('');
}
const reducedMotion=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function clearAnimations(){
  state.journalObserver?.disconnect();state.journalObserver=null;
  state.journalTimeline?.kill();state.journalTimeline=null;
  state.letterTimeline?.kill();state.letterTimeline=null;
}
function addLines(timeline, element){
  const height=element.getBoundingClientRect().height;
  const lineHeight=parseFloat(getComputedStyle(element).lineHeight)||25;
  const lines=Math.max(1,Math.ceil((height-1)/lineHeight));
  const mask=(line,progress)=>{
    const top=Math.min(height,line*lineHeight),bottom=Math.min(height,(line+1)*lineHeight);
    return `polygon(0px 0px,100% 0px,100% ${top}px,${progress}% ${top}px,${progress}% ${bottom}px,0px ${bottom}px)`;
  };
  gsap.set(element,{clipPath:mask(0,0)});
  for(let line=0;line<lines;line++){
    timeline.set(element,{clipPath:mask(line,0)});
    timeline.to(element,{clipPath:mask(line,100),duration:TYPE_LINE_SECONDS,ease:'none'});
  }
  timeline.set(element,{clearProps:'clipPath'});
}
function journalAnimation(){
  if(!window.gsap||reducedMotion()||!$('#digest-body .essay-section'))return;
  const timeline=gsap.timeline({paused:true});
  for(const section of $('#digest-body').querySelectorAll('.essay-section')){
    const heading=section.querySelector('h2');
    gsap.set(heading,{autoAlpha:0,y:9});
    timeline.to(heading,{autoAlpha:1,y:0,duration:.3,ease:'power2.out'});
    for(const paragraph of section.querySelectorAll('p'))addLines(timeline,paragraph);
  }
  const closing=$('#digest-body .essay-closing');
  if(closing){gsap.set(closing,{autoAlpha:0,y:10});timeline.to(closing,{autoAlpha:1,y:0,duration:.3,ease:'power2.out'});}
  state.journalTimeline=timeline;
  if('IntersectionObserver' in window){
    state.journalObserver=new IntersectionObserver(records=>{if(records.some(record=>record.isIntersecting)){state.journalObserver?.disconnect();state.journalObserver=null;timeline.play();}},{threshold:0,rootMargin:'0px 0px 160px 0px'});
    state.journalObserver.observe($('.journal-article'));
  }else timeline.play();
}
function prepareLetter(hasLetter){
  const section=$('#letter-section'),scene=$('#envelope-scene'),paper=$('#letter-paper');
  section.hidden=!hasLetter;paper.hidden=true;scene.hidden=false;
  paper.classList.remove('is-opening');$('#open-letter').setAttribute('aria-expanded','false');
  for(const node of [scene,paper,$('.envelope-flap'),$('.envelope-front'),$('.envelope-seal')])node.removeAttribute('style');
}
function typeLetter(){
  if(!window.gsap||reducedMotion())return;
  const root=$('#letter-body'),timeline=gsap.timeline();
  const heading=root.querySelector('h2');
  if(heading){gsap.set(heading,{autoAlpha:0,y:8});timeline.to(heading,{autoAlpha:1,y:0,duration:.3});}
  for(const paragraph of root.querySelectorAll('.letter-prose p'))addLines(timeline,paragraph);
  for(const detail of root.querySelectorAll('.letter-detail,.letter-note')){
    gsap.set(detail,{autoAlpha:0,y:7});timeline.to(detail,{autoAlpha:1,y:0,duration:.25},'+=.1');
  }
  state.letterTimeline=timeline;
}
function focusLetter(){const paper=$('#letter-paper');paper.tabIndex=-1;paper.focus({preventScroll:true});}
function openLetter(){
  const scene=$('#envelope-scene'),paper=$('#letter-paper'),button=$('#open-letter');
  if(!paper.hidden)return;
  paper.hidden=false;button.setAttribute('aria-expanded','true');
  if(!window.gsap||reducedMotion()){scene.hidden=true;focusLetter();return;}
  paper.classList.add('is-opening');
  const style=getComputedStyle(paper),fullHeight=paper.offsetHeight;
  const top=parseFloat(style.paddingTop),bottom=parseFloat(style.paddingBottom);
  gsap.set(paper,{height:0,paddingTop:0,paddingBottom:0,autoAlpha:0,y:-60,scaleY:.72,overflow:'hidden'});
  const timeline=gsap.timeline({onComplete:()=>{
    scene.hidden=true;paper.classList.remove('is-opening');
    gsap.set(paper,{clearProps:'height,paddingTop,paddingBottom,opacity,visibility,transform,overflow'});
    typeLetter();focusLetter();
  }});
  timeline.to($('.envelope-seal'),{autoAlpha:0,scale:.3,duration:.23,ease:'power2.in'})
    .to($('.envelope-flap'),{rotationX:-170,transformOrigin:'top center',duration:.62,ease:'power2.inOut'})
    .to($('.envelope-front'),{y:12,autoAlpha:.6,duration:.3},'<.22')
    .to(paper,{height:fullHeight,paddingTop:top,paddingBottom:bottom,autoAlpha:1,y:0,scaleY:1,duration:.9,ease:'power3.out'},'-=.15')
    .to(scene,{height:0,autoAlpha:0,duration:.45,ease:'power2.inOut'},'-=.38');
  state.letterTimeline=timeline;
}
function render(){
  clearAnimations();
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
  $('#digest-body').innerHTML=digest?`${(digest.sections||[]).map((section,index)=>`<section class="essay-section"><span class="section-number">${String(index+1).padStart(2,'0')}</span><h2>${esc(section.heading)}</h2>${paragraphs(section.body,byId,section.entry_ids)}</section>`).join('')}<div class="essay-closing"><span class="small-cap">KEEP THIS</span>${paragraphs(digest.closing,byId)}</div>`:'<div class="empty-essay"><h2>这一天，还没有写成文章。</h2><p>条目只是材料。让 Agent 阅读当天会话、核对产物，再写出起因、转折、留下了什么和下一步。</p></div>';
  const letter=digest?.letter;
  $('#letter-body').innerHTML=letter?`<h2>${esc(letter.salutation||'写给你的交流建议')}</h2><div class="letter-prose">${paragraphs(letter.body,byId,letter.entry_ids)}</div>${letter.recipient?`<div class="letter-detail"><span>适合找谁</span><strong>${esc(letter.recipient)}</strong></div>`:''}${letter.suggested_ask?`<div class="letter-detail"><span>可以问什么</span><strong>${esc(letter.suggested_ask)}</strong></div>`:''}<p class="letter-note">这里只给建议；不会自动发布或联系他人。</p>`:'<h2>先看清手里的东西</h2><p>当今日日志写好后，这里会给你一封具体的建议信：哪些成果值得展示，适合找谁，以及最好问什么。不会自动发送。</p>';
  prepareLetter(Boolean(letter));
  $('#entry-list').innerHTML=items.length?items.map(x=>`<article class="entry"><span class="entry-kind ${esc(x.kind)}">${labels[x.kind]||'记录'}</span><div><h3><button data-id="${esc(x.id)}">${esc(x.title)}</button></h3>${x.detail?`<p>${esc(x.detail)}</p>`:''}<div class="entry-meta"><span>${esc(x.project||'未归类')}</span><span>${esc(readiness[x.readiness]||'')}</span>${x.artifact?artifactLink(x):''}${x.workrefs?.length?`<span>证据：${x.workrefs.map(esc).join(' · ')}</span>`:''}</div></div></article>`).join(''):'<div class="empty">还没有这一天的记录。</div>';
  calendar();
  journalAnimation();
}
async function load(){try{const r=await fetch('/api/data',{cache:'no-store'});if(!r.ok)throw Error('读取日志失败');state.data=await r.json();render();}catch(e){toast(e.message);}}
function edit(entry=null){state.editing=entry;$('#dialog-title').textContent=entry?'编辑这一步':'记下一步';const form=$('#entry-form');for(const field of ['date','kind','title','detail','project','artifact','artifact_target','readiness']) form.elements[field].value=entry?.[field]??({date:state.date,kind:'progress',readiness:'private'}[field]||'');$('#delete-entry').hidden=!entry;$('#editor').showModal();}
async function mutate(payload){const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const body=await r.json();if(!r.ok)throw Error(body.error||'保存失败');state.data=body;if(payload.action!=='delete'&&payload.date){state.date=payload.date;state.month=payload.date.slice(0,7);}render();}
$('#add-entry').addEventListener('click',()=>edit());
$('#entry-list').addEventListener('click',event=>{const b=event.target.closest('[data-id]');if(b)edit(state.data.entries.find(x=>x.id===b.dataset.id));});
$('#entry-form').addEventListener('submit',async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(event.target).entries());values.workrefs=state.editing?.workrefs||[];try{await mutate({action:state.editing?'update':'create',id:state.editing?.id,...values});$('#editor').close();toast('这一步已保存到本机');}catch(e){toast(e.message);}});
$('#delete-entry').addEventListener('click',async()=>{if(!state.editing||!confirm(`删除“${state.editing.title}”？`))return;try{await mutate({action:'delete',id:state.editing.id});$('#editor').close();toast('记录已删除');}catch(e){toast(e.message);}});
for(const id of ['close-dialog','cancel-entry']) $(`#${id}`).addEventListener('click',()=>$('#editor').close());
function selectDay(date){state.date=date;state.month=date.slice(0,7);render();window.scrollTo({top:0,behavior:'auto'});}
function shift(days){const d=new Date(`${state.date}T12:00:00`);d.setDate(d.getDate()+days);selectDay(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`);}
function shiftMonth(delta){const [year,month]=state.month.split('-').map(Number), next=new Date(year,month-1+delta,1);state.month=`${next.getFullYear()}-${String(next.getMonth()+1).padStart(2,'0')}`;calendar();}
$('#calendar-days').addEventListener('click',event=>{const button=event.target.closest('[data-date]');if(button)selectDay(button.dataset.date);});
$('#calendar-prev').addEventListener('click',()=>shiftMonth(-1));$('#calendar-next').addEventListener('click',()=>shiftMonth(1));$('#calendar-today').addEventListener('click',()=>selectDay(localDay()));
$('#prev-day').addEventListener('click',()=>shift(-1));$('#next-day').addEventListener('click',()=>shift(1));$('#back-today').addEventListener('click',()=>selectDay(localDay()));
$('#open-letter').addEventListener('click',openLetter);
$('#replay-letter').addEventListener('click',()=>{state.letterTimeline?.kill();prepareLetter(true);$('#letter-section').scrollIntoView({behavior:reducedMotion()?'auto':'smooth',block:'start'});requestAnimationFrame(openLetter);});
load();
