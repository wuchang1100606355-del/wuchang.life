/** @odoo-module **/

(() => {
  "use strict";
  const root = document.getElementById("wuchang-management-app");
  if (!root) return;
  const panel = document.getElementById("wc-panel");
  const sync = document.getElementById("wc-sync");
  let state = null;
  let active = "overview";

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const money = (value) => value == null ? "未判定" : `NT$ ${Number(value).toLocaleString("zh-TW")}`;
  const statusClass = (value) => String(value || "").startsWith("PASS") ? "wc-pass" : "wc-hold";
  const stateLine = (value) => `<span class="wc-pill ${statusClass(value)}">${esc(value || "UNKNOWN")}</span>`;
  const card = (title, value, note) => `<article class="wc-card"><small>${esc(title)}</small><h2>${esc(value)}</h2><p>${esc(note)}</p></article>`;

  async function rpc(path, params = {}) {
    const response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({jsonrpc: "2.0", method: "call", params, id: Date.now()}),
    });
    const body = await response.json();
    if (!response.ok || body.error) throw new Error(body.error?.data?.message || `HTTP ${response.status}`);
    return body.result;
  }

  function overview() {
    const menu = state.menu || {};
    const orders = state.orders || {};
    return `<div class="wc-grid">
      ${card("Odoo 商品映射", `${menu.product_count ?? menu.observed_count ?? 0}/64`, menu.state)}
      ${card("近 7 日訂單", orders.order_count ?? "未判定", `已付款 ${orders.paid_order_count ?? "未判定"} 筆`)}
      ${card("已付款金額", money(orders.paid_amount_total), "未付款訂單不列入收入")}
      ${card("毛利", "未判定", orders.gross_margin_state)}
    </div>
    <div class="wc-section-title"><h2>資料與權威狀態</h2><small>${esc(state.observed_at)} · ${esc(state.timezone)}</small></div>
    <div class="wc-grid two">
      <article class="wc-card"><h3>Odoo 正式資料</h3>${stateLine(menu.state)}<p>範圍 ${esc(state.store_ref)}。畫面只讀，無訂單、付款或票券效果。</p></article>
      <article class="wc-card"><h3>小J AI 總成</h3>${stateLine(state.ai?.state)}<p>本地模型只產候選；總場規則准駁，效果收據才可完成。</p></article>
    </div>`;
  }

  function orders() {
    const data = state.orders || {};
    return `<div class="wc-grid">
      ${card("全部訂單", data.order_count ?? "未判定", "資料期間內 Odoo 訂單")}
      ${card("已付款", data.paid_order_count ?? "未判定", "只計 paid / done / invoiced")}
      ${card("收入", money(data.paid_amount_total), "無跨系統歸因")}
      ${card("未付款", data.unpaid_not_counted_as_revenue ?? "未判定", "不計收入")}
    </div><div class="wc-section-title"><h2>堂食／外帶／外送</h2></div>
    <article class="wc-card">${stateLine(data.sale_mode_state)}<p>用餐方式是訂單層級；沒有已驗證欄位時不由商品或模型推測。</p></article>`;
  }

  function menu() {
    const data = state.menu || {};
    const rows = (data.products || []).slice(0, 64).map((item) => `<tr><td>${esc(item.id)}</td><td>${esc(item.name)}</td><td>${esc(item.category)}</td><td>${money(item.price)}</td><td>${esc((item.groups || []).join(", ") || "無")}</td></tr>`).join("");
    if (!rows) return `<div class="wc-empty">${esc(data.state)}；未精確映射 64/64 前不顯示猜配商品。</div>`;
    return `<div class="wc-section-title"><h2>QuickClick 64 精確來源映射</h2>${stateLine(data.state)}</div><div class="wc-card"><table class="wc-table"><thead><tr><th>來源 ID</th><th>商品</th><th>分類</th><th>Odoo 售價</th><th>非變體屬性群組</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function inventory() {
    const data = state.inventory || {};
    const rows = (data.items || []).map((item) => `<tr><td>${esc(item.source_product_id)}</td><td>${esc(item.name)}</td><td>${esc(item.qty_available)}</td><td>${esc(item.forecasted_qty)}</td></tr>`).join("");
    return `<div class="wc-section-title"><h2>統一庫存唯讀檢視</h2>${stateLine(data.state)}</div><article class="wc-card"><p>${esc(data.low_stock_state)}</p>${rows ? `<table class="wc-table"><thead><tr><th>來源 ID</th><th>商品</th><th>現有量</th><th>預測量</th></tr></thead><tbody>${rows}</tbody></table>` : "沒有可驗證資料"}</article>`;
  }

  function eightd() {
    const data = state.eightd || {};
    const rows = (data.coordinates || []).map((item) => `<tr><td>${esc(item.object)}</td><td>${esc(item.version)}</td><td>${esc(item.time)}</td><td>${esc(item.state)}</td><td>${item.fresh ? "是" : "否"}</td><td>${item.authority_allowed ? "範圍內" : "未授權"}</td><td>${esc(item.source_ref)}</td></tr>`).join("");
    return `<div class="wc-section-title"><h2>8D 單一耦合場資源定位</h2>${stateLine(data.state)}</div>
      <article class="wc-card"><p>觀測端：03 店家管理節點；目標端：${esc(data.target_ref)}。區分存在、載入、可呼叫、效果驗收；過時或缺證據不得當作現況。</p>
      <table class="wc-table"><thead><tr><th>資源</th><th>版本</th><th>觀測時間</th><th>狀態</th><th>時效</th><th>授權</th><th>證據座標</th></tr></thead><tbody>${rows}</tbody></table></article>
      <div class="wc-section-title"><h2>候選動作</h2></div><article class="wc-card"><p>目前沒有動作被執行。任何搜尋、設備控制、外部發佈或 Odoo 寫入，須取得對應授權並由原底層執行器回傳效果收據。</p><button class="wc-disabled" disabled>等待總場授權與執行器綁定</button></article>`;
  }

  function connector(title, data, details) {
    return `<article class="wc-card"><h3>${esc(title)}</h3>${stateLine(data?.state)}<p>${esc(details)}</p><p>資源：${esc(data?.account_resource_ref || "未取得")}<br/>最後同步：${esc(data?.last_sync || "未取得")}<br/>權限已核：${data?.permissions_verified ? "是" : "否"}</p><button class="wc-disabled" disabled>外部寫入需另行核准</button></article>`;
  }

  function community() {
    return `<div class="wc-grid two">
      ${connector("Google 商家檔案", state.google_business, "商家資訊、評論、貼文與績效只在精確商家資源及唯讀權限已驗證後顯示。")}
      ${connector("平台中立社群協作", state.social_collaboration, "貼文草稿、協作任務與審核；不冒充平台原生排程，不自行新增平台。")}
    </div><div class="wc-section-title"><h2>協作邊界</h2></div><article class="wc-card"><p>咖啡店自然人商家帳號與協會 Workspace 分離。Google 指標與 Odoo 銷售只並列，沒有歸因證據不得宣稱貼文帶來營收。</p></article>`;
  }

  function devices() {
    return `<div class="wc-grid two">
      ${connector("店內音樂資源", state.music, "只顯示既有設備／服務與可驗證控制接口；播放、音量變更尚未授權。")}
      ${connector("NVR／指定攝影機", state.nvr, "僅店長管理面可見。憑證綁定與新鮮畫格收據未閉合時，不展示、下載或外傳影像。")}
    </div><div class="wc-section-title"><h2>總場執行閉環</h2></div><article class="wc-card"><p>小J先定位資源與授權範圍，總場准駁後交原執行器；命令回應不等於現場效果，必須回收設備或 NVR 效果收據。</p></article>`;
  }

  const renderers = {overview, orders, menu, inventory, eightd, community, devices};
  function render() { panel.innerHTML = (renderers[active] || overview)(); }
  root.querySelectorAll("[data-panel]").forEach((button) => button.addEventListener("click", () => {
    root.querySelectorAll("[data-panel]").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active"); active = button.dataset.panel; render();
  }));

  rpc("/wuchang/ordering/management/state").then((result) => {
    state = result;
    sync.textContent = `${result.state} · ${result.observed_at}`;
    sync.className = `wc-state ${String(result.state).startsWith("PASS") ? "is-pass" : "is-warn"}`;
    render();
  }).catch((error) => {
    sync.textContent = "讀取失敗"; sync.className = "wc-state is-warn";
    panel.innerHTML = `<div class="wc-empty">${esc(error.message)}；不得把失敗標為完成。</div>`;
  });
})();
