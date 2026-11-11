const $ = (selector) => document.querySelector(selector);
const state = { projects: [], current: null, manual: [], novels: [], health: null };

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
}
function setOutput(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  $("#output").textContent = text;
}
function toast(message, bad = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => { el.className = "toast"; }, 4200);
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let payload = null;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) throw new Error(payload?.detail || payload?.message || `请求失败：${response.status}`);
  return payload;
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("已复制到剪贴板"); }
  catch { toast("复制失败，请手动选择文本", true); }
}
function fmtDate(value) {
  if (!value) return "";
  try { return new Date(value).toLocaleString("zh-CN", { hour12: false }); } catch { return value; }
}
function statusLabel(status) {
  return ({ draft: "草稿", pending_approval: "待审核", approved: "已接受", rejected: "已拒绝", script_ready: "脚本完成", cost_ready: "成本已估算", generated: "已生成", rendered: "已渲染", packaged: "已打包" })[status] || status || "未知";
}
function badgeClass(kind) {
  return `tag ${esc(kind)}`;
}

async function refreshHealth() {
  try {
    const data = await api("/api/health?deep=true");
    state.health = data;
    const items = [
      ["火山方舟", data.ark_configured, data.ark_configured ? "已配置" : "未配置"],
      ["Seedream", data.jimeng?.seedream?.ok, data.jimeng?.seedream?.default_model || data.seedream_model],
      ["Seedance", data.jimeng?.seedance?.ok, data.jimeng?.seedance?.default_model || data.seedance_model],
      ["Pexels", data.pexels_configured, data.pexels_configured ? "已配置" : "待申请"],
      ["Pixabay", data.pixabay_configured, data.pixabay_configured ? "已配置" : "待申请"],
    ];
    $("#healthPills").innerHTML = items.map(([label, ok, text]) => `<span class="pill ${ok ? "ok" : "bad"}">${esc(label)} · ${esc(text)}</span>`).join("");
  } catch (error) {
    $("#healthPills").innerHTML = `<span class="pill bad">健康检查失败 · ${esc(error.message)}</span>`;
  }
}

async function refreshProjects() {
  state.projects = await api("/api/projects");
  if (!state.projects.length) {
    $("#projectList").className = "project-list empty";
    $("#projectList").textContent = "还没有项目";
    return;
  }
  $("#projectList").className = "project-list";
  $("#projectList").innerHTML = state.projects.map((project) => `
    <div class="project-item ${state.current?.id === project.id ? "active" : ""}" data-id="${esc(project.id)}">
      <strong>${esc(project.title)}</strong>
      <span>${esc(statusLabel(project.status))} · ${esc(project.genre || "未分类")}${project.decision === "pending" ? " · 待你审核" : ""} · ${esc(fmtDate(project.updated_at))}</span>
    </div>
  `).join("");
  document.querySelectorAll(".project-item").forEach((node) => {
    node.addEventListener("click", () => selectProject(node.dataset.id));
  });
}

async function refreshDashboard() {
  const data = await api("/api/dashboard");
  $("#dashboard").innerHTML = [
    ["项目", data.projects], ["可用小说", data.available_novels], ["发布", data.published], ["线索", data.leads], ["有效", data.qualified_leads], ["本月", `¥${Number(data.month_spend_cny || 0).toFixed(2)}`],
  ].map(([label, value]) => `<div class="stat"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`).join("");
}

async function refreshManual() {
  state.manual = await api("/api/manual-assets");
  if (!state.manual.length) {
    $("#manualAssets").innerHTML = `<p class="muted">assets/manual/ 中没有文件。请放入已授权素材。</p>`;
    return;
  }
  $("#manualAssets").innerHTML = state.manual.map((item) => `
    <div class="manual-row">
      <span>${esc(item.filename)} <small>${(item.size / 1024 / 1024).toFixed(1)} MB</small></span>
      <button class="small" data-manual="${esc(item.filename)}">关联素材</button>
    </div>
  `).join("");
  document.querySelectorAll("[data-manual]").forEach((button) => {
    button.addEventListener("click", () => attachManual(button.dataset.manual));
  });
}

async function refreshNovels() {
  state.novels = await api("/api/novels");
  if (!state.novels.length) {
    $("#novelList").className = "novel-list empty";
    $("#novelList").textContent = "还没有候选小说。请先添加候选，或调整自动选书条件。";
    return;
  }
  $("#novelList").className = "novel-list";
  $("#novelList").innerHTML = state.novels.map((item) => {
    const status = ({ available: "可用", in_review: "待审核", used: "已使用", rejected: "已拒绝" })[item.status] || item.status;
    const disabled = item.status !== "available";
    return `<div class="novel-row">
      <div><strong>${esc(item.title)}</strong><small>${esc(item.genre || "未分类")} · ${esc(status)} · ${esc(item.tags || "无标签")} · 优先级 ${esc(item.priority)}</small></div>
      <div class="novel-actions"><button class="small" data-novel="${esc(item.id)}" ${disabled ? "disabled" : ""}>用这条创建项目</button></div>
    </div>`;
  }).join("");
  document.querySelectorAll("[data-novel]").forEach((button) => {
    button.addEventListener("click", () => createProjectFromNovel(button.dataset.novel));
  });
}

async function createProjectFromNovel(candidateId) {
  try {
    const project = await api(`/api/novels/${candidateId}/project`, {
      method: "POST",
      body: JSON.stringify({ genre: "", keywords: "", target_duration: 30, budget_limit_cny: 20 }),
    });
    state.current = project;
    await Promise.all([refreshNovels(), refreshProjects()]);
    await selectProject(project.id);
    toast("已创建待审核项目");
  } catch (error) { toast(error.message, true); }
}

async function autoCreateProject() {
  try {
    const project = await api("/api/projects/auto", {
      method: "POST",
      body: JSON.stringify({
        genre: $("#autoGenre").value.trim(),
        keywords: $("#autoKeywords").value.trim(),
        target_duration: 30,
        budget_limit_cny: 20,
      }),
    });
    state.current = project;
    await Promise.all([refreshNovels(), refreshProjects()]);
    await selectProject(project.id);
    toast("已自动选一本并创建待审核项目");
  } catch (error) { toast(error.message, true); }
}

async function refreshLeads() {
  const leads = await api("/api/leads");
  if (!leads.length) { $("#leadList").innerHTML = `<p class="muted">还没有客户线索。</p>`; return; }
  $("#leadList").innerHTML = leads.map((lead) => `
    <div class="lead-row">
      <strong>${esc(lead.nickname || "未命名客户")}</strong>
      <small>${esc(lead.platform || "未知平台")} · ${esc(lead.need_type || "未填写需求")} · ${esc(lead.budget_range || "未填预算")} · ${esc(lead.stage)}</small>
      <div>${esc(lead.next_action || "")} ${lead.qualified ? '<span class="tag stock">有效</span>' : ""}</div>
    </div>
  `).join("");
}

async function loadAll() {
  await Promise.all([refreshHealth(), refreshProjects(), refreshDashboard(), refreshManual(), refreshLeads(), refreshNovels()]);
  if (state.current) await selectProject(state.current.id);
}

async function selectProject(id) {
  state.current = await api(`/api/projects/${id}`);
  $("#emptyDetail").classList.add("hidden");
  $("#detailCard").classList.remove("hidden");
  renderDetail();
  await refreshProjects();
}

function renderDetail() {
  const project = state.current;
  if (!project) return;
  $("#detailTitle").textContent = project.title;
  $("#detailMeta").textContent = `${project.genre || "未分类"} · 目标 ${project.target_duration} 秒 · 单条预算 ¥${Number(project.budget_limit_cny || 0).toFixed(2)} · ${project.id}`;
  $("#detailStatus").textContent = statusLabel(project.status);
  const script = project.script || {};
  const shots = project.shots || [];
  $("#scriptBox").innerHTML = `
    <div class="hooks">${(script.hooks || []).map((hook) => `<div class="hook">${esc(hook)}</div>`).join("") || '<span class="muted">还没有脚本，请点击“生成脚本和分镜”。</span>'}</div>
  `;
  $("#shotsBody").innerHTML = shots.map((shot) => {
    const assets = (project.assets || []).filter((asset) => asset.shot_id === shot.id);
    const selected = assets.find((asset) => asset.selected) || assets[0];
    return `<tr>
      <td>${esc(shot.id)}</td><td>${Number(shot.duration || 0).toFixed(1)}s</td>
      <td><span class="${badgeClass(shot.kind)}">${esc(shot.kind)}</span></td>
      <td>${esc(shot.narration || shot.visual || "")}</td>
      <td>${selected ? `${esc(selected.provider)} · ${esc(selected.license || "无许可证")}` : "未选择"}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="5" class="muted">还没有分镜。</td></tr>`;

  $("#costBox").classList.remove("hidden");
  const estimate = Number(project.estimated_cost_cny || 0);
  $("#costBox").className = "notice " + (estimate ? "ok" : "");
  $("#costBox").textContent = estimate ? `预计成本 ¥${estimate.toFixed(2)}，实际已记录 ¥${Number(project.actual_cost_cny || 0).toFixed(2)}。` : "还没有估算成本。点击“估算成本”后再决定是否付费生成。";

  const approval = $("#approvalBox");
  if (project.decision === "pending") {
    approval.classList.remove("hidden");
    approval.className = "notice";
    approval.innerHTML = `<strong>这个项目等待你的决定。</strong><p>程序已经自动选好小说并生成脚本/分镜，但还没有调用付费 API。接受后才会进入素材和生成流程。</p><div class="publish-actions"><button class="small" data-decision="approve">接受这个项目</button><button class="small" data-decision="reject">拒绝并换一条</button></div>`;
    document.querySelectorAll("[data-decision]").forEach((button) => {
      button.addEventListener("click", () => decideProject(button.dataset.decision));
    });
  } else {
    approval.classList.add("hidden");
  }

  renderAssets(project);
  renderPosts(project);
}

function renderAssets(project) {
  const assets = project.assets || [];
  $("#assetBox").classList.toggle("hidden", !assets.length);
  $("#assetList").innerHTML = assets.map((asset) => `
    <div class="asset-row">
      <div><strong>${esc(asset.shot_id)}</strong> · ${esc(asset.provider)} · <small>${esc(asset.license || "无许可证")}</small><br><small>${esc(asset.path)}</small></div>
      <button class="small" data-asset="${asset.id}" data-shot="${esc(asset.shot_id)}">${asset.selected ? "当前使用" : "设为使用"}</button>
    </div>
  `).join("");
  document.querySelectorAll("[data-asset]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        state.current = await api(`/api/projects/${project.id}/assets/${button.dataset.asset}/select?shot_id=${encodeURIComponent(button.dataset.shot)}`, { method: "POST" });
        renderDetail(); toast("已切换素材");
      } catch (error) { toast(error.message, true); }
    });
  });
}

function renderPosts(project) {
  const posts = project.posts || [];
  $("#publishBox").classList.toggle("hidden", !project.package_dir && !posts.length);
  $("#videoLink").href = `/api/projects/${project.id}/video`;
  $("#douyinCover").href = `/api/projects/${project.id}/cover/douyin`;
  $("#xhsCover").href = `/api/projects/${project.id}/cover/xiaohongshu`;
  $("#postList").innerHTML = posts.map((post) => `
    <div class="post-row">
      <strong>${post.platform === "douyin" ? "抖音" : "小红书"} · ${esc(post.status)}</strong>
      <small>${post.published_url ? esc(post.published_url) : "尚未回填发布链接"}</small>
      <div class="publish-actions">
        <button class="small" data-copy="${post.id}">复制文案</button>
        <a class="button-link small" href="${post.platform === "douyin" ? "https://creator.douyin.com/" : "https://creator.xiaohongshu.com/"}" target="_blank">打开创作中心</a>
        <button class="small" data-publish="${post.id}">回填发布</button>
      </div>
    </div>
  `).join("");
  posts.forEach((post) => {
    const copyButton = document.querySelector(`[data-copy="${post.id}"]`);
    if (copyButton) copyButton.addEventListener("click", () => copyText(post.caption || ""));
    const publishButton = document.querySelector(`[data-publish="${post.id}"]`);
    if (publishButton) publishButton.addEventListener("click", async () => {
      const url = prompt("粘贴发布后的作品链接：", post.published_url || "");
      if (url === null) return;
      const views = Number(prompt("播放量（可留空）：", "0") || 0);
      const dms = Number(prompt("私信/咨询数（可留空）：", "0") || 0);
      try {
        await api(`/api/posts/${post.id}/published`, { method: "POST", body: JSON.stringify({ published_url: url, metrics: { views, dms } }) });
        await selectProject(project.id); await refreshDashboard(); toast("已登记发布");
      } catch (error) { toast(error.message, true); }
    });
  });
}

async function attachManual(filename) {
  if (!state.current) return toast("请先选择项目", true);
  const shotId = prompt("要关联到哪个镜头 ID？例如 shot-01", state.current.shots?.[0]?.id || "shot-01");
  if (!shotId) return;
  const license = prompt("素材许可证（必填，例如 Pexels License / 自有素材）：", "自有素材");
  if (!license) return;
  const author = prompt("作者/来源：", "手动导入");
  try {
    state.current = await api(`/api/projects/${state.current.id}/assets/manual`, {
      method: "POST",
      body: JSON.stringify({ shot_id: shotId, filename, kind: filename.match(/\.(jpg|jpeg|png|webp)$/i) ? "image" : "video", license, author, source_url: "" }),
    });
    renderDetail(); toast("手动素材已关联");
  } catch (error) { toast(error.message, true); }
}

async function decideProject(decision) {
  if (!state.current) return;
  let reason = "";
  if (decision === "reject") {
    reason = prompt("拒绝原因（可留空）：", "") || "";
  }
  try {
    const result = await api(`/api/projects/${state.current.id}/decision`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        reason,
        next_candidate: decision === "reject",
        genre: $("#autoGenre").value.trim(),
        keywords: $("#autoKeywords").value.trim(),
        target_duration: 30,
        budget_limit_cny: 20,
      }),
    });
    await refreshNovels();
    if (result.next_project) {
      state.current = result.next_project;
      await Promise.all([refreshProjects(), refreshNovels()]);
      await selectProject(result.next_project.id);
      toast("已拒绝并切换到下一条候选");
    } else {
      await Promise.all([refreshProjects(), refreshNovels()]);
      await selectProject(state.current.id);
      toast(result.decision === "approved" ? "项目已接受，可以继续搜索素材和生成" : "项目已拒绝，没有更多可用候选");
    }
  } catch (error) { toast(error.message, true); }
}

async function runAction(action) {
  if (!state.current) return toast("请先选择项目", true);
  const id = state.current.id;
  try {
    let result;
    if (action === "auto-script") result = await api(`/api/projects/${id}/script/auto`, { method: "POST" });
    if (action === "asset-search") result = await api(`/api/projects/${id}/asset-search`, { method: "POST" });
    if (action === "dry-run") result = await api(`/api/projects/${id}/generate/dry-run`, { method: "POST" });
    if (action === "confirm-generate") {
      const estimate = await api(`/api/projects/${id}/generate/dry-run`, { method: "POST" });
      if (!confirm(`本次预计成本 ¥${Number(estimate.total_cny || 0).toFixed(2)}，确认调用火山方舟即梦 API？`)) return;
      result = await api(`/api/projects/${id}/generate/confirm`, { method: "POST", body: JSON.stringify({ confirmed: true }) });
    }
    if (action === "render") result = await api(`/api/projects/${id}/render`, { method: "POST" });
    if (action === "package") result = await api(`/api/projects/${id}/package`, { method: "POST" });
    setOutput(result);
    await selectProject(id);
    await Promise.all([refreshDashboard(), refreshProjects()]);
    toast("操作完成");
  } catch (error) {
    setOutput({ ok: false, error: error.message });
    toast(error.message, true);
  }
}

$("#novelForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await api("/api/novels", { method: "POST", body: JSON.stringify(Object.fromEntries(form.entries())) });
    event.target.reset();
    await refreshNovels();
    toast("候选小说已添加");
  } catch (error) { toast(error.message, true); }
});
$("#refreshNovels").addEventListener("click", refreshNovels);
$("#autoProjectBtn").addEventListener("click", autoCreateProject);

$("#createForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    const project = await api("/api/projects", { method: "POST", body: JSON.stringify(Object.fromEntries(form.entries())) });
    event.target.reset();
    state.current = project;
    await refreshProjects();
    await selectProject(project.id);
    toast("项目已创建");
  } catch (error) { toast(error.message, true); }
});
document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action));
});
$("#refreshBtn").addEventListener("click", loadAll);
$("#refreshManual").addEventListener("click", refreshManual);
$("#leadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = Object.fromEntries(form.entries());
  payload.qualified = form.has("qualified");
  payload.post_id = null;
  try {
    await api("/api/leads", { method: "POST", body: JSON.stringify(payload) });
    event.target.reset();
    await Promise.all([refreshLeads(), refreshDashboard()]);
    toast("线索已记录");
  } catch (error) { toast(error.message, true); }
});

loadAll().catch((error) => toast(error.message, true));
