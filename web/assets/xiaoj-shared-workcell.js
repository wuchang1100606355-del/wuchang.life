(() => {
  "use strict";
  const TASK_ID = "T-XIAOJ-LAUNCH";
  const API = "/api/taiji/nl-control";
  const CHANNEL = "xiaoj-shared-workcell";
  const ACTIVE = new Set(["STARTING", "RUNNING", "RESUMED"]);
  let root = null;
  let timer = null;
  let channel = null;

  function injectStyle() {
    if (document.getElementById("xiaojSharedWorkcellStyle")) return;
    const style = document.createElement("style");
    style.id = "xiaojSharedWorkcellStyle";
    style.textContent = `
      .xjShared{margin:16px 0;padding:18px;border:1px solid #ccd8e4;border-radius:14px;background:rgba(255,255,255,.96);box-shadow:0 14px 32px rgba(23,37,58,.08)}
      .xjShared h2{margin:0 0 8px}.xjSharedGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:12px 0}
      .xjSharedStat{padding:10px;border:1px solid #d9e1ea;border-radius:10px;background:#f8fbfd}.xjSharedStat span{display:block;font-size:12px;color:#607086}.xjSharedStat strong{display:block;word-break:break-word}
      .xjShared textarea{width:100%;box-sizing:border-box;min-height:96px;padding:10px;border:1px solid #c7d4e2;border-radius:10px;font:inherit}
      .xjSharedActions{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.xjShared button{width:auto;margin:0;padding:9px 12px;border-radius:9px;border:1px solid #1f6d60;background:#fff;font:inherit;font-weight:800;cursor:pointer}
      .xjShared button.primary{background:#1f6d60;color:#fff}.xjSharedMsg{margin-top:10px;font-size:13px;color:#607086}.xjSharedMsg[data-state="error"]{color:#b91c1c}.xjSharedMsg[data-state="ok"]{color:#047857}
    `;
    document.head.appendChild(style);
  }
  function createPanel() {
    const host = document.createElement("section");
    host.id = "xiaojSharedWorkcell";
    host.className = "xjShared";
    host.innerHTML = `
      <h2>小J 共用工作原胞</h2>
      <p>兩個頁面共用同一 task、同一狀態原胞與同一 Total Field；本頁不保存權威狀態。</p>
      <div class="xjSharedGrid">
        <div class="xjSharedStat"><span>Task</span><strong data-xj="task">${TASK_ID}</strong></div>
        <div class="xjSharedStat"><span>工作狀態</span><strong data-xj="task-state">讀取中</strong></div>
        <div class="xjSharedStat"><span>最新 Run</span><strong data-xj="run">—</strong></div>
        <div class="xjSharedStat"><span>模型</span><strong data-xj="model">讀取中</strong></div>
        <div class="xjSharedStat"><span>傳輸</span><strong data-xj="transport">讀取中</strong></div>
        <div class="xjSharedStat"><span>雲端推理</span><strong data-xj="cloud">讀取中</strong></div>
      </div>
      <label for="xiaojSharedIntent"><strong>自然語言工作</strong></label>
      <textarea id="xiaojSharedIntent" placeholder="輸入工作意圖；兩個頁面都會看到同一後端工作狀態。"></textarea>
      <div class="xjSharedActions">
        <button type="button" class="primary" data-xj-action="submit">送出工作</button>
        <button type="button" data-xj-action="refresh">重新整理</button>
      </div>
      <div class="xjSharedMsg" data-xj="message">尚未連線</div>
    `;
    const main = document.querySelector("main") || document.body;
    main.appendChild(host);
    return host;
  }

  function setText(key, value) {
    const node = root.querySelector(`[data-xj="${key}"]`);
    if (node) node.textContent = value ?? "—";
  }
  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      cache: "no-store",
      credentials: "same-origin",
      ...options,
      headers: {"Content-Type": "application/json", ...(options.headers || {})}
    });
    const text = await response.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) { data = {raw: text}; }
    if (!response.ok) throw new Error(`${response.status} ${data.detail || text || "API_ERROR"}`);
    return data;
  }

  function schedule(latestRun) {
    if (timer) clearTimeout(timer);
    if (latestRun && ACTIVE.has(String(latestRun.state || ""))) {
      timer = setTimeout(refresh, 2500);
    }
  }

  async function refresh() {
    const message = root.querySelector('[data-xj="message"]');
    try {
      const [status, task] = await Promise.all([
        requestJson(`${API}/status`),
        requestJson(`${API}/task/${encodeURIComponent(TASK_ID)}/state`)
      ]);
      const latest = task.latest_run || null;
      setText("task-state", task.work_task?.STATE || latest?.state || "NO_RUN");
      setText("run", latest ? `${latest.run_id || "—"} / ${latest.state || "—"}` : "尚無 Run");
      setText("model", status.local_model_primary || latest?.model || "—");
      setText("transport", status.context_transport_format || status.dynamic_context_delivery_mode || "—");
      setText("cloud", status.live_cloud_reasoning_enabled ? "ENABLED" : "DISABLED");
      message.dataset.state = "ok";
      message.textContent = `權威來源：${task.authoritative_source || "TAIJI01_NL_CONTROL"}`;
      schedule(latest);
    } catch (error) {
      setText("task-state", "API_UNAVAILABLE");
      message.dataset.state = "error";
      message.textContent = `共用後端未接通：${error.message}`;
      if (timer) clearTimeout(timer);
    }
  }
  async function submit() {
    const input = root.querySelector("#xiaojSharedIntent");
    const button = root.querySelector('[data-xj-action="submit"]');
    const message = root.querySelector('[data-xj="message"]');
    const intent = input.value.trim();
    if (!intent) {
      message.dataset.state = "error";
      message.textContent = "請輸入工作意圖。";
      return;
    }
    button.disabled = true;
    message.dataset.state = "";
    message.textContent = "送出中…";
    try {
      const result = await requestJson(`${API}/execute`, {
        method: "POST",
        body: JSON.stringify({
          intent,
          task_id: TASK_ID,
          goal_mode: true,
          auto_land: true,
          timeout_seconds: 900,
          dry_run: false,
          google_fallback: false
        })
      });
      message.dataset.state = "ok";
      message.textContent = `已送出：${result.run_id || result.state}`;
      if (channel) channel.postMessage({type: "refresh", task_id: TASK_ID});
      await refresh();
    } catch (error) {
      message.dataset.state = "error";
      message.textContent = `送出失敗：${error.message}`;
    } finally {
      button.disabled = false;
    }
  }
  function init() {
    if (document.getElementById("xiaojSharedWorkcell")) return;
    injectStyle();
    root = createPanel();
    root.querySelector('[data-xj-action="submit"]').addEventListener("click", submit);
    root.querySelector('[data-xj-action="refresh"]').addEventListener("click", refresh);
    try {
      channel = new BroadcastChannel(CHANNEL);
      channel.onmessage = (event) => {
        if (event.data?.type === "refresh" && event.data?.task_id === TASK_ID) refresh();
      };
    } catch (_) {
      channel = null;
    }
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, {once: true});
  } else {
    init();
  }
})();
