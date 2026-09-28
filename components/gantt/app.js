const DAY = 42;
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const today = () => {const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;};
const dayNumber = (date) => Math.floor(Date.parse(`${date}T00:00:00Z`) / 86400000);
const dateFromNumber = (number) => new Date(number * 86400000).toISOString().slice(0, 10);
const state = {data:null, chartId:localStorage.getItem("eetm-chart"), offset:0, editor:null};
const storedTheme = localStorage.getItem("eetm-gantt-theme");
function setTheme(theme) {
  const selected = theme === "light" ? "light" : "dark";
  document.documentElement.dataset.theme = selected;
  const button = $("#theme-toggle");
  button.textContent = selected === "light" ? "☾ 夜间" : "☀ 日间";
  button.setAttribute("aria-label", selected === "light" ? "切换到夜间配色" : "切换到日间配色");
  localStorage.setItem("eetm-gantt-theme", selected);
}
setTheme(storedTheme);
$("#theme-toggle").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light"));

function toast(message) {
  const box = $("#toast"); box.textContent = message; box.style.display = "block";
  clearTimeout(toast.timer); toast.timer = setTimeout(() => box.style.display = "none", 4500);
}

async function load() {
  try {
    const response = await fetch("/api/data", {cache:"no-store"});
    if (!response.ok) throw Error("无法读取本机数据");
    state.data = await response.json();
    if (!state.data.charts.some((chart) => chart.id === state.chartId)) state.chartId = state.data.charts[0]?.id ?? null;
    render();
  } catch (error) { toast(error.message); }
}

async function action(payload) {
  const response = await fetch("/api/action", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || "保存失败");
  state.data = result;
  if (payload.action === "create_chart") {
    state.chartId = result.charts.at(-1)?.id ?? null;
    if (state.chartId) localStorage.setItem("eetm-chart", state.chartId);
  }
  if (!result.charts.some((chart) => chart.id === state.chartId)) state.chartId = result.charts.at(-1)?.id ?? null;
  render();
}

function currentChart() { return state.data?.charts.find((chart) => chart.id === state.chartId); }
function projectName(chart, projectId) { return chart.projects.find((project) => project.id === projectId)?.name || "未分配项目"; }
function deadlineLabel(project) { return project.deadline_date ? `${project.deadline_date}${project.deadline_zone ? ` · ${project.deadline_zone}` : ""}` : "无 DDL"; }

function render() {
  if (!state.data) return;
  const chart = currentChart();
  $("#chart-list").innerHTML = state.data.charts.map((item) => `<button type="button" class="${item.id === state.chartId ? "selected" : ""}" data-chart="${escapeHtml(item.id)}">${escapeHtml(item.name)}</button>`).join("") || `<span class="empty">还没有甘特图</span>`;
  $("#sync-state").textContent = state.data.last_sync_at ? `Agent 同步：${new Date(state.data.last_sync_at).toLocaleString("zh-CN")}` : "等待首次 Agent 同步";
  $("#chart-title").textContent = chart?.name || "开始建立研究计划";
  $("#chart-description").textContent = chart?.description || "创建图表，再加入项目和任务。";
  $("#auto-sync-pill").textContent = chart?.auto_sync ? "已开启" : "已关闭";
  $("#edit-chart").disabled = $("#new-project").disabled = $("#new-task").disabled = !chart;
  if (!chart) { $("#overview").innerHTML = ""; $("#timeline").innerHTML = `<div class="empty-timeline">点击左侧＋，创建第一张甘特图。</div>`; $("#backlog-list").innerHTML = ""; $("#backlog-count").textContent = ""; return; }
  renderOverview(chart); renderTimeline(chart); renderBacklog(chart);
}

function renderOverview(chart) {
  const due = chart.projects.filter((project) => project.deadline_date).sort((a,b) => a.deadline_date.localeCompare(b.deadline_date));
  const next = due.find((project) => project.deadline_date >= today()) || due.at(-1);
  const active = chart.tasks.filter((task) => task.status === "active" || task.status === "blocked").length;
  $("#overview").innerHTML = `<div class="metric"><small>当前研究项目</small><strong>${chart.projects.length}</strong></div><div class="metric"><small>进行中 / 受阻任务</small><strong class="accent">${active}</strong></div><div class="metric"><small>最近项目 DDL</small><strong class="${next ? "warn" : "subtle"}">${next ? escapeHtml(next.deadline_date.slice(5)) : "尚未设置"}</strong>${next ? `<small>${escapeHtml(next.name)} · ${escapeHtml(next.deadline_zone || "本地日期")}</small>` : ""}</div>`;
}

function renderTimeline(chart) {
  const base = dayNumber(today()) + state.offset * 14 - 2;
  const dates = Array.from({length:35}, (_, i) => dateFromNumber(base + i));
  const trackWidth = dates.length * DAY;
  const todayIndex = dayNumber(today()) - base;
  const todayLine = todayIndex >= 0 && todayIndex < dates.length ? `<span class="today-line" style="left:${todayIndex * DAY + DAY/2}px"></span>` : "";
  const weekends = dates.map((date, i) => [0,6].includes(new Date(`${date}T00:00:00Z`).getUTCDay()) ? `<span class="weekend" style="left:${i*DAY}px;width:${DAY}px"></span>` : "").join("");
  let html = `<div class="timeline-row head"><div class="timeline-label">项目 / 任务</div><div class="timeline-track" style="width:${trackWidth}px;height:55px">${weekends}${todayLine}${dates.map((date,i) => `<span class="day-head ${date === today() ? "today" : ""}" style="left:${i*DAY}px">${date.slice(5,7)}月<b>${date.slice(8)}</b></span>`).join("")}</div></div>`;
  for (const project of chart.projects) {
    const deadline = project.deadline_date ? dayNumber(project.deadline_date)-base : -1;
    const diamond = deadline >= 0 && deadline < dates.length ? `<button class="milestone" title="${escapeHtml(project.deadline_label || "项目 DDL")} · ${escapeHtml(deadlineLabel(project))}" data-project="${escapeHtml(project.id)}" style="left:${deadline*DAY+13}px"></button>` : "";
    html += `<div class="timeline-row project"><div class="timeline-label"><button data-project="${escapeHtml(project.id)}">${escapeHtml(project.name)}<span class="deadline-text">${escapeHtml(project.deadline_label || "项目期限")} · ${escapeHtml(deadlineLabel(project))}</span></button></div><div class="timeline-track" style="width:${trackWidth}px">${weekends}${todayLine}${diamond}</div></div>`;
    const tasks = chart.tasks.filter((task) => task.project_id === project.id && (task.start || task.due)).sort((a,b) => (a.due || a.start).localeCompare(b.due || b.start));
    for (const task of tasks) {
      const start = dayNumber(task.start || task.due), end = dayNumber(task.due || task.start);
      const visibleStart = Math.max(start, base), visibleEnd = Math.min(end, base+dates.length-1);
      let bar = "";
      if (visibleEnd >= visibleStart) {
        const left = (visibleStart-base)*DAY+5, width = (visibleEnd-visibleStart+1)*DAY-10;
        bar = `<button data-task="${escapeHtml(task.id)}" class="bar ${escapeHtml(task.status)}" style="left:${left}px;width:${width}px;--progress:${Number(task.progress)||0}%" title="${escapeHtml(task.title)} · ${escapeHtml(task.start || task.due)} → ${escapeHtml(task.due || task.start)}"><span>${width>95 ? escapeHtml(task.title) : ""}</span></button>`;
      }
      html += `<div class="timeline-row"><div class="timeline-label"><i class="dot ${escapeHtml(task.status)}"></i><button class="row-title" data-task="${escapeHtml(task.id)}">${escapeHtml(task.title)}</button><span class="meta">${Number(task.progress)||0}%</span></div><div class="timeline-track" style="width:${trackWidth}px">${weekends}${todayLine}${bar}</div></div>`;
    }
  }
  if (!chart.projects.length) html += `<div class="empty-timeline">还没有项目。点击“＋ 项目”建立研究线。</div>`;
  $("#timeline").innerHTML = html;
  $("#timeline").querySelectorAll("[data-project]").forEach((button) => button.addEventListener("click", () => editProject(button.dataset.project)));
  $("#timeline").querySelectorAll("[data-task]").forEach((button) => button.addEventListener("click", () => editTask(button.dataset.task)));
}

function renderBacklog(chart) {
  const tasks = chart.tasks.filter((task) => !task.start && !task.due);
  $("#backlog-count").textContent = `${tasks.length} 项`;
  $("#backlog-list").innerHTML = tasks.length ? tasks.map((task) => `<button class="backlog-item" data-task="${escapeHtml(task.id)}"><i class="dot ${escapeHtml(task.status)}"></i><span class="task-text">${escapeHtml(task.title)}</span><small>${escapeHtml(projectName(chart, task.project_id))}</small></button>`).join("") : `<div class="empty">没有待排期任务。</div>`;
  $("#backlog-list").querySelectorAll("[data-task]").forEach((button) => button.addEventListener("click", () => editTask(button.dataset.task)));
}

function field(label, name, value="", type="text", hint="") {
  return `<label class="field">${escapeHtml(label)}<input name="${name}" type="${type}" value="${escapeHtml(value ?? "")}">${hint ? `<span class="hint">${escapeHtml(hint)}</span>` : ""}</label>`;
}

function openEditor(kind, entity=null) {
  state.editor = {kind, entity};
  const isNew = !entity;
  $("#editor-eyebrow").textContent = isNew ? "CREATE" : "EDIT";
  $("#editor-title").textContent = {chart:"甘特图",project:"项目",task:"任务"}[kind];
  $("#delete-entity").hidden = isNew;
  const chart = currentChart();
  if (kind === "chart") {
    $("#editor-fields").innerHTML = field("图表名称","name",entity?.name) + field("说明 / 分类","description",entity?.description) + `<label class="field"><input name="auto_sync" type="checkbox" ${entity?.auto_sync !== false ? "checked" : ""}> Agent 在显式调用后自动同步该图表</label>`;
  } else if (kind === "project") {
    $("#editor-fields").innerHTML = field("项目名称","name",entity?.name) + field("工作区绝对路径","workspace",entity?.workspace,"text","Agent 只向路径完全匹配的项目同步进展。") + field("项目 DDL","deadline_date",entity?.deadline_date,"date") + field("DDL 名称","deadline_label",entity?.deadline_label) + field("DDL 时区","deadline_zone",entity?.deadline_zone,"text","如 AoE (UTC−12)。") + field("来源链接","deadline_url",entity?.deadline_url,"url");
  } else {
    const options = chart.projects.map((project) => `<option value="${escapeHtml(project.id)}" ${entity?.project_id === project.id ? "selected" : ""}>${escapeHtml(project.name)}</option>`).join("");
    $("#editor-fields").innerHTML = `<label class="field">所属项目<select name="project_id" ${entity ? "disabled" : ""}>${options}</select></label>` + field("任务名称","title",entity?.title) + field("开始日期","start",entity?.start,"date") + field("完成日期 / DDL","due",entity?.due,"date") + `<label class="field">状态<select name="status">${[["planned","计划"],["active","进行中"],["blocked","受阻"],["done","完成"]].map(([code,label]) => `<option value="${code}" ${entity?.status === code ? "selected" : ""}>${label}</option>`).join("")}</select></label>` + field("完成比例（0–100）","progress",entity?.progress ?? 0,"number") + `<label class="field">备注<textarea name="notes">${escapeHtml(entity?.notes || "")}</textarea></label>` + (entity?.workrefs?.length ? `<p class="field">证据：${entity.workrefs.map(escapeHtml).join(" · ")}</p>` : "") + (entity?.source === "agent" ? `<p class="field">修改后，Agent 不会覆盖你手动设定的字段。</p>` : "");
  }
  $("#editor").showModal();
}

function editProject(id) { const project = currentChart()?.projects.find((item) => item.id === id); if (project) openEditor("project",project); }
function editTask(id) { const task = currentChart()?.tasks.find((item) => item.id === id); if (task) openEditor("task",task); }

$("#editor-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const {kind, entity} = state.editor;
  const values = Object.fromEntries(new FormData(event.target).entries());
  if (kind === "chart") values.auto_sync = Boolean(values.auto_sync);
  if (kind === "task") { values.progress = Number(values.progress); if (entity) values.project_id = entity.project_id; }
  const payload = {action:`${entity ? "update" : "create"}_${kind}`, chart_id:state.chartId, ...values};
  if (entity) payload[`${kind}_id`] = entity.id;
  try { await action(payload); $("#editor").close(); toast("已保存到本机甘特图"); }
  catch (error) { toast(error.message); }
});
$("#delete-entity").addEventListener("click", async () => {
  const {kind,entity} = state.editor;
  if (!entity || !confirm(`删除“${entity.name || entity.title}”？此操作不能撤销。`)) return;
  try { await action({action:`delete_${kind}`,chart_id:state.chartId,[`${kind}_id`]:entity.id}); $("#editor").close(); toast("已删除"); }
  catch(error){toast(error.message)}
});
$("#cancel-editor").addEventListener("click", () => $("#editor").close());
$("#chart-list").addEventListener("click", (event) => {const button=event.target.closest("[data-chart]");if(!button)return;state.chartId=button.dataset.chart;localStorage.setItem("eetm-chart",state.chartId);render()});
$("#new-chart").addEventListener("click",()=>openEditor("chart"));
$("#edit-chart").addEventListener("click",()=>openEditor("chart",currentChart()));
$("#new-project").addEventListener("click",()=>openEditor("project"));
$("#new-task").addEventListener("click",()=>{if(!currentChart()?.projects.length){toast("先创建项目，再添加任务");return}openEditor("task")});
$("#prev-period").addEventListener("click",()=>{state.offset--;renderTimeline(currentChart())});
$("#next-period").addEventListener("click",()=>{state.offset++;renderTimeline(currentChart())});
$("#today-period").addEventListener("click",()=>{state.offset=0;renderTimeline(currentChart())});
load(); setInterval(()=>{if(!$("#editor").open)load()},20000);
