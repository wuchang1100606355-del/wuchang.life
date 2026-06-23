(function () {
  "use strict";

  const safety = {
    FORMAL_DB_WRITE: false,
    FORMAL_POS_WRITE: false,
    PAYMENT_CAPTURE: false,
    SERVICE_RESTART: false,
    DEPLOY: false,
    PRODUCTION_RELEASE: false,
    SECRET_READ: false,
    MEMBER_PLAINTEXT_READ: false,
  };

  const menu = [
    { code: "DR_RED_TEA", name: "紅茶", category: "飲料類", price: 30 },
    { code: "DR_GREEN_TEA", name: "綠茶", category: "飲料類", price: 30 },
    { code: "FO_C_DUMPLING", name: "煎餃", category: "中式餐點類", price: 30 },
    { code: "FO_C_RADISH", name: "蘿蔔糕", category: "中式餐點類", price: 30 },
    { code: "FO_W_BURGER", name: "漢堡", category: "西式餐點類", price: 30 },
    { code: "FO_W_BURGER_EGG", name: "漢堡加蛋", category: "西式餐點類", price: 40 },
    { code: "FO_W_CLUB", name: "總匯三明治", category: "西式餐點類", price: 45 },
    { code: "SET_CHI_60", name: "中式套餐", category: "套餐類", price: 60 },
    { code: "SET_WES_60", name: "西式套餐", category: "套餐類", price: 60 },
    { code: "ODOO_PROD_SOY_MILK", name: "豆漿", category: "早餐", price: 25 },
    { code: "ODOO_PROD_EGG_PANCAKE", name: "蛋餅", category: "早餐", price: 40 },
    { code: "ODOO_PROD_COFFEE_LATTE", name: "拿鐵", category: "咖啡", price: 80 },
    { code: "ODOO_PROD_COFFEE_AMERICANO", name: "美式咖啡", category: "咖啡", price: 60 },
  ];

  const order = {
    productName: "父親節早午餐咖啡套組",
    items: [
      { name: "熱拿鐵", qty: 1, price: 120 },
      { name: "燕麥奶", qty: 1, price: 20 },
      { name: "火腿起司吐司", qty: 1, price: 75 },
      { name: "公益杯押金", qty: 1, price: 50 },
    ],
    subtotal: 265,
    discount: 30,
    payable: 235,
    d8: "76b0fd75...598e3f6c",
    voice: "候選試算 235 元；公益杯押金不列入折扣。請店員確認後才可進正式 POS。",
  };

  const displayTicker = {
    top: [
      "今日推薦：拿鐵 + 蛋餅組合",
      "團體會員掃八維碼可建立候選註冊",
      "雲端 AI 僅產生候選，本地驗證後才顯示",
      "公益杯押金不列入折扣",
    ],
    bottom: [
      "候選訂單：父親節早午餐咖啡套組，試算 235 元",
      "叫號提示：請留意櫃台與小J語音",
      "維護公告：客顯為顯示模式，不處理付款",
      "正式 POS 寫入需店員確認 gate",
    ],
  };

  const xiaojAvatar = {
    name: "小J 接客顯示機 VRM",
    assetPath: "/wuchang_core/static/src/xiaoj_ordering/avatar/lung.vrm",
    fileName: "lung.vrm",
    mode: "customer_menu_display",
    state: "VRM_ASSET_SLOT_READY",
  };

  const pages = [
    { id: "staff_pos", label: "店員 POS" },
    { id: "counter_service_touch", label: "櫃台觸控" },
    { id: "av_ai_menu_display", label: "影音菜單" },
    { id: "business_management", label: "商業管理" },
    { id: "hardware_menu_business_settings", label: "硬體設定" },
  ];

  let state = {
    page: document.body.dataset.startMode || "staff_pos",
    selectedCategory: "全部",
    dryRunMessage: "尚未確認",
  };

  const app = document.getElementById("xiaoj-ordering-app");

  function money(value) {
    return "$" + Number(value || 0).toLocaleString("zh-TW");
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setPage(page) {
    state.page = page;
    render();
  }

  function dryRun(action) {
    state.dryRunMessage = action + "：CONFIRM_DRY_RUN / FORMAL_POS_WRITE=FALSE";
    render();
  }

  function categories() {
    return ["全部"].concat(Array.from(new Set(menu.map((item) => item.category))));
  }

  function filteredMenu() {
    if (state.selectedCategory === "全部") return menu;
    return menu.filter((item) => item.category === state.selectedCategory);
  }

  function layout(content) {
    app.innerHTML = `
      <header class="topbar">
        <div class="brand">
          <h1>聊國咖啡館｜小J 主權式影音點餐 AI</h1>
          <p>瀏覽器封裝程式｜雲端候選、本地驗證、人類確認、Odoo 落地</p>
        </div>
        <nav class="mode-tabs">
          ${pages.map((page) => `<button class="${state.page === page.id ? "active" : ""}" data-page="${page.id}">${page.label}</button>`).join("")}
        </nav>
      </header>
      <section class="grid">
        ${leftRail()}
        <section class="panel workspace">${content}</section>
        ${rightRail()}
      </section>
    `;
    app.querySelectorAll("[data-page]").forEach((button) => {
      button.addEventListener("click", () => setPage(button.dataset.page));
    });
    app.querySelectorAll("[data-dry-run]").forEach((button) => {
      button.addEventListener("click", () => dryRun(button.dataset.dryRun));
    });
    app.querySelectorAll("[data-category]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedCategory = button.dataset.category;
        render();
      });
    });
  }

  function leftRail() {
    return `
      <aside class="panel pad">
        <h2 class="section-title">總場狀態</h2>
        <div class="status-list">
          <div class="status-row"><span>雲端 AI</span><b class="badge warn">候選苦力</b></div>
          <div class="status-row"><span>No-LLM 後腦</span><b class="badge ok">本地權威</b></div>
          <div class="status-row"><span>Human Gate</span><b class="badge ok">必須確認</b></div>
          <div class="status-row"><span>正式 POS</span><b class="badge hold">HOLD</b></div>
          <div class="status-row"><span>付款擷取</span><b class="badge hold">FALSE</b></div>
        </div>
        <h2 class="section-title" style="margin-top:18px">頁面封裝</h2>
        <div class="proof-code">start_url=/wuchang/xiaoj/ordering<br/>display=standalone<br/>route_auth=user</div>
      </aside>
    `;
  }

  function rightRail() {
    return `
      <aside class="right-rail">
        <section class="panel pad">
          <h2 class="section-title">候選訂單</h2>
          <div>${order.items.map((item) => `<div class="cart-line"><span>${escapeHtml(item.name)}</span><span>x${item.qty}</span><strong>${money(item.price)}</strong></div>`).join("")}</div>
          <div class="total"><span>試算應付</span><strong>${money(order.payable)}</strong></div>
          <div class="toolbar">
            <button class="primary" data-dry-run="店員確認候選訂單">確認試算</button>
            <button class="danger" data-dry-run="取消候選訂單">取消</button>
          </div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">8D Proof</h2>
          <div class="proof-code">packet_ref=POS-CANDIDATE-DRY-RUN<br/>d8_ref=${order.d8}<br/>state=${escapeHtml(state.dryRunMessage)}</div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">Safety Flags</h2>
          ${Object.entries(safety).map(([key, value]) => `<div class="status-row"><span>${key}</span><b class="badge ok">${String(value).toUpperCase()}</b></div>`).join("")}
        </section>
      </aside>
    `;
  }

  function menuCards(limit) {
    return filteredMenu().slice(0, limit || 9).map((item) => `
      <article class="item-card">
        <div class="badge">${escapeHtml(item.category)}</div>
        <h3>${escapeHtml(item.name)}</h3>
        <div class="price">${money(item.price)}</div>
        <div class="meta">${escapeHtml(item.code)}｜Odoo menu ref</div>
        <button data-dry-run="加入 ${escapeHtml(item.name)} 候選">加入候選</button>
      </article>
    `).join("");
  }

  function ticker(items, position) {
    const text = items.map(escapeHtml).join("　｜　");
    return `
      <div class="display-ticker ${position}" aria-label="${position === "top" ? "上方跑馬燈" : "下方跑馬燈"}">
        <div class="ticker-track">
          <span>${text}</span>
          <span aria-hidden="true">${text}</span>
        </div>
      </div>
    `;
  }

  function staffPosPage() {
    const categoryButtons = categories().map((cat) => `<button class="${state.selectedCategory === cat ? "active" : ""}" data-category="${cat}">${cat}</button>`).join("");
    return `
      <div class="hero-band">
        <div class="hero-card">
          <h2>店員 POS：快速點餐、候選驗證、正式寫入前 HOLD</h2>
          <p>店員用這頁承接語音/觸控候選單，所有金額與折扣都由本地後腦重算，按下確認也只產生 dry-run gate。</p>
          <div class="toolbar">${categoryButtons}</div>
        </div>
        <div class="quick-stats">
          <div class="stat"><span>今日候選單</span><strong>38</strong></div>
          <div class="stat"><span>待確認</span><strong>6</strong></div>
          <div class="stat"><span>本地驗證</span><strong>100%</strong></div>
          <div class="stat"><span>正式寫 POS</span><strong>0</strong></div>
        </div>
      </div>
      <div class="content"><div class="cards">${menuCards(9)}</div></div>
    `;
  }

  function counterTouchPage() {
    return `
      <div class="hero-band">
        <div class="hero-card">
          <h2>櫃台客戶服務觸控：掃 8D、查會員、問菜單、排隊提示</h2>
          <p>此頁給櫃台或客戶觸控螢幕使用，顯示安全化資料與可執行候選，不讀會員明文。</p>
          <div class="toolbar">
            <button data-dry-run="掃描團體會員八維碼">掃 8D</button>
            <button data-dry-run="建立服務請求候選">服務請求</button>
            <button data-dry-run="排隊叫號候選">叫號</button>
          </div>
        </div>
        <div class="quick-stats">
          <div class="stat"><span>會員顯示</span><strong>遮罩</strong></div>
          <div class="stat"><span>團體註冊</span><strong>Ready</strong></div>
          <div class="stat"><span>LINE/Google</span><strong>Ref</strong></div>
          <div class="stat"><span>付款</span><strong>Hold</strong></div>
        </div>
      </div>
      <div class="content split">
        <section class="panel pad">
          <h2 class="section-title">常用服務</h2>
          <div class="wide-list">
            <div class="wide-row"><span>團體會員八維碼註冊</span><button data-dry-run="開啟團體註冊入口">開啟</button></div>
            <div class="wide-row"><span>訂單候選狀態查詢</span><button data-dry-run="查詢候選狀態">查詢</button></div>
            <div class="wide-row"><span>公益/社區方案說明</span><button data-dry-run="顯示社區方案">顯示</button></div>
          </div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">客服回覆</h2>
          <div class="proof-code">${escapeHtml(order.voice)}</div>
        </section>
      </div>
    `;
  }

  function avDisplayPage() {
    return `
      ${ticker(displayTicker.top, "top")}
      <div class="hero-band">
        <div class="hero-card">
          <h2>影音 AI 影像菜單顯示場：小J、菜單、候選單同框</h2>
          <p>顧客看到的是產品級影音菜單；雲端主播只拿遮罩後的候選狀態，本地驗證結果在前景。</p>
          <div class="toolbar">
            <button data-dry-run="播放小J候選介紹">播放</button>
            <button data-dry-run="切換菜單輪播">輪播</button>
            <button data-dry-run="朗讀候選訂單">朗讀</button>
          </div>
        </div>
        <div class="screen-preview">
          <div class="avatar-stage" aria-label="XiaoJ VRM customer display slot">
            <div class="avatar-halo"></div>
            <div class="avatar-body">
              <div class="avatar-face"></div>
              <div class="avatar-dress"></div>
            </div>
            <div class="avatar-status">
              <b>${escapeHtml(xiaojAvatar.name)}</b>
              <span>${escapeHtml(xiaojAvatar.state)}</span>
              <code>${escapeHtml(xiaojAvatar.assetPath)}</code>
            </div>
          </div>
        </div>
      </div>
      <div class="content">
        <div class="cards">${menuCards(6)}</div>
        <section class="display-asset-panel">
          <div>
            <h2 class="section-title">大菜單 / 接客顯示機角色資產</h2>
            <p>VRM 檔放入靜態路徑後，顯示機以此作為小J角色來源；目前仍是顯示候選，不觸發正式 POS 或付款。</p>
          </div>
          <div class="proof-code">avatar_file=${escapeHtml(xiaojAvatar.fileName)}<br/>avatar_path=${escapeHtml(xiaojAvatar.assetPath)}<br/>display_mode=${escapeHtml(xiaojAvatar.mode)}</div>
        </section>
      </div>
      ${ticker(displayTicker.bottom, "bottom")}
    `;
  }

  function businessManagementPage() {
    return `
      <div class="hero-band">
        <div class="hero-card">
          <h2>商業管理：現金、社群 AI、維護排程、營業分析</h2>
          <p>老闆頁面以分級子功能組織營運情報，讓店內現金、社群互動、設備維護與市場分析排成每日工作流。</p>
          <div class="toolbar">
            <button data-dry-run="匯出今日營業分析候選">分析</button>
            <button data-dry-run="排入維護任務候選">維護</button>
            <button data-dry-run="社群AI貼文候選">社群</button>
          </div>
        </div>
        <div class="quick-stats">
          <div class="stat"><span>店內現金</span><strong>$18,420</strong></div>
          <div class="stat"><span>社群互動</span><strong>126</strong></div>
          <div class="stat"><span>維護待辦</span><strong>4</strong></div>
          <div class="stat"><span>毛利雷達</span><strong>↑</strong></div>
        </div>
      </div>
      <div class="content split">
        <section class="panel pad">
          <h2 class="section-title">分級子功能</h2>
          <div class="wide-list">
            <div class="wide-row"><span>現金日結與交班</span><b class="badge warn">候選</b></div>
            <div class="wide-row"><span>社群 AI 回訪與活動</span><b class="badge warn">候選</b></div>
            <div class="wide-row"><span>維護排程與硬體健康</span><b class="badge ok">本地</b></div>
            <div class="wide-row"><span>商品銷售與折扣分析</span><b class="badge ok">Odoo</b></div>
          </div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">商業資訊分析</h2>
          <div class="wide-list">
            <div class="wide-row"><span>高毛利推薦：咖啡 + 早餐組合</span><strong>+18%</strong></div>
            <div class="wide-row"><span>維護風險：客顯 Chrome 心跳延遲</span><strong>中</strong></div>
            <div class="wide-row"><span>社群任務：團體會員 QR 推廣</span><strong>高</strong></div>
          </div>
        </section>
      </div>
    `;
  }

  function settingsPage() {
    return `
      <div class="hero-band">
        <div class="hero-card">
          <h2>硬體、菜單、營業資訊設定：封裝成瀏覽器程式</h2>
          <p>設定頁只調整候選設定與本地顯示狀態；正式硬體控制、服務重啟、部署都維持 HOLD。</p>
          <div class="toolbar">
            <button data-dry-run="儲存硬體設定候選">硬體候選</button>
            <button data-dry-run="同步菜單設定候選">菜單候選</button>
            <button data-dry-run="更新營業資訊候選">營業候選</button>
          </div>
        </div>
        <div class="quick-stats">
          <div class="stat"><span>客顯</span><strong>Chrome</strong></div>
          <div class="stat"><span>聲音</span><strong>SUNMI</strong></div>
          <div class="stat"><span>菜單品項</span><strong>25</strong></div>
          <div class="stat"><span>正式控制</span><strong>Hold</strong></div>
        </div>
      </div>
      <div class="content split">
        <section class="panel pad">
          <h2 class="section-title">硬體設定</h2>
          <div class="wide-list">
            <div class="wide-row"><span>NODE_POS_MAINT</span><b class="badge ok">維護節點</b></div>
            <div class="wide-row"><span>NODE_XIAOJ_DISPLAY_COMPUTE</span><b class="badge ok">客顯/算力</b></div>
            <div class="wide-row"><span>SUNMI Voice Adapter</span><b class="badge warn">待 API 確認</b></div>
          </div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">菜單與營業資訊</h2>
          <div class="wide-list">
            <div class="wide-row"><span>菜單來源</span><b class="badge ok">Odoo XML/ORM</b></div>
            <div class="wide-row"><span>商品照片</span><b class="badge warn">待產品級照片</b></div>
            <div class="wide-row"><span>營業資訊</span><b class="badge warn">候選設定</b></div>
          </div>
        </section>
      </div>
    `;
  }

  function render() {
    const page = {
      staff_pos: staffPosPage,
      counter_service_touch: counterTouchPage,
      av_ai_menu_display: avDisplayPage,
      business_management: businessManagementPage,
      hardware_menu_business_settings: settingsPage,
    }[state.page] || staffPosPage;
    layout(page());
  }

  render();
})();

/* XiaoJ VRM browser runtime bootstrap */
(function () {
  if (document.getElementById("xiaoj-vrm-runtime-loader")) return;
  const s = document.createElement("script");
  s.id = "xiaoj-vrm-runtime-loader";
  s.type = "module";
  s.src = "/wuchang_core/static/src/xiaoj_ordering/xiaoj_vrm_bootstrap.js?v=" + Date.now();
  document.body.appendChild(s);
})();
