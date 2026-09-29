(() => {
  "use strict";

  const DIMENSIONS = [
    ["D1", "意圖", "Founder 要完成的結果"],
    ["D2", "狀態", "多模態、網路與設備現況"],
    ["D3", "座標", "場景、能力、節點與對象"],
    ["D4", "證據", "來源、雜湊與重新觀測"],
    ["D5", "執行／政策", "允許、候選或等待放行"],
    ["D6", "生成式傳輸", "最小必要差量與目標重建"],
    ["D7", "風險／隔離", "失敗封閉、隱私與回復"],
    ["D8", "權威", "總場與自然人決定真實效果"]
  ];

  const FLOW = [
    ["01", "捕捉意圖與多模態"],
    ["02", "綁定證據與座標"],
    ["03", "離散索引精準查表"],
    ["04", "高維浮點理解候選"],
    ["05", "無越權融合"],
    ["06", "形成 D1–D8 細胞"],
    ["07", "選擇可替換算力"],
    ["08", "產生最小傳輸差量"],
    ["09", "目標端重建"],
    ["10", "總場裁決效果"],
    ["11", "重新觀測與記錄"]
  ];

  const SCENES = {
    cafe: {
      label: "上品聊國咖啡館",
      role: "咖啡館服務員影音 AI 小 J",
      example: "我想喝一杯不太甜、適合下午的咖啡",
      capabilities: ["cafe.menu.explain", "cafe.order.proposal", "cafe.audiovisual.guide"],
      answer: "我已先定位菜單說明與點餐候選能力。接下來會顯示建議，不會直接下單或付款。"
    },
    property: {
      label: "社區管委會／物業",
      role: "大廳服務員影音 AI 小 J",
      example: "電梯有異音，請協助形成報修候選",
      capabilities: ["property.notice.read", "property.service.intake"],
      answer: "我已形成報修需求候選與必要座標；正式派工仍等待人員及總場放行。"
    },
    association: {
      label: "社區發展協會",
      role: "公益服務影音 AI 小 J",
      example: "有位長輩需要陪伴，請整理服務需求",
      capabilities: ["association.service.intake", "association.volunteer.match"],
      answer: "我只建立去識別化需求與志工媒合候選，不替代社工判斷，也不自動指派。"
    },
    personal: {
      label: "個人主權 AI 中繼",
      role: "個人影音 AI 小 J",
      example: "用最少雲端用量整理今天的工作上下文",
      capabilities: ["personal.dynamic.context.reconstruct", "personal.subscription.relay"],
      answer: "我會先用本機索引與轉譯，只把無法本機完成的最小差量交給已綁定的可替換雲端算力。"
    }
  };

  const PET = {
    element: null,
    state: "idle",
    frame: 0,
    timer: null,
    rows: {
      idle: { row: 0, frames: 6, delay: 180 },
      wave: { row: 3, frames: 4, delay: 170 },
      failed: { row: 5, frames: 8, delay: 150 },
      waiting: { row: 6, frames: 6, delay: 170 },
      working: { row: 7, frames: 6, delay: 140 },
      review: { row: 8, frames: 6, delay: 170 }
    }
  };

  const state = {
    scene: "cafe",
    imageRef: null,
    imageEvidenceRef: null,
    audioObserved: false,
    network: "尚未觀測",
    deviceObserved: false,
    earthquake: false,
    busy: false,
    voiceConsentPending: false
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];

  function animatePet(name, once = false) {
    const definition = PET.rows[name] || PET.rows.idle;
    PET.state = name;
    PET.frame = 0;
    clearInterval(PET.timer);
    const draw = () => {
      PET.element.style.backgroundPosition = `${-PET.frame * 192}px ${-definition.row * 208}px`;
      PET.frame += 1;
      if (PET.frame >= definition.frames) {
        if (once) {
          clearInterval(PET.timer);
          window.setTimeout(() => animatePet("idle"), 260);
          return;
        }
        PET.frame = 0;
      }
    };
    draw();
    PET.timer = window.setInterval(draw, definition.delay);
  }

  function renderDimensions(activeCount = 0, values = {}) {
    $("#dimensions").innerHTML = DIMENSIONS.map(([id, label, description], index) => `
      <article class="dimension ${index < activeCount ? "active" : ""}">
        <header><b>${id}</b><span>${label}</span></header>
        <p>${values[id] || description}</p>
      </article>
    `).join("");
  }

  function renderFlow(doneCount = 0, blockedAt = -1) {
    $("#executionFlow").innerHTML = FLOW.map(([id, label], index) => `
      <div class="flow-step ${index < doneCount ? "done" : ""} ${index === blockedAt ? "blocked" : ""}">
        <b>${id}</b><span>${label}</span>
      </div>
    `).join("");
  }

  async function digestText(text) {
    if (!window.crypto?.subtle) return "本機雜湊不可用";
    const data = new TextEncoder().encode(text);
    const digest = await crypto.subtle.digest("SHA-256", data);
    return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
  }

  function speak(text) {
    // The browser TTS API follows the operating system's default output and cannot
    // prove that audio will stay on a private device. Keep this candidate silent
    // until a governed TTS endpoint and an explicit output sink are both bound.
    return false;
  }

  function setSpeech(text, shouldSpeak = false) {
    $("#xiaojSpeech").textContent = text;
    if (shouldSpeak) speak(text);
  }

  function currentScene() {
    return SCENES[state.scene];
  }

  async function callOdoo(route, params) {
    if (!/^https?:$/.test(window.location.protocol)) throw new Error("HOLD_NOT_ODOO_ORIGIN");
    const response = await fetch(route, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "call",
        params,
        id: window.crypto?.randomUUID?.() || `${Date.now()}`
      })
    });
    const body = await response.json();
    if (!response.ok || body.error) throw new Error("ODOO_ROUTE_FAILED");
    return body.result || body;
  }

  async function requestStorefront(intent) {
    $("#odooRouteState").textContent = "讀取中";
    $("#gpuRouteState").textContent = "候選請求中";
    const [facts, flair] = await Promise.allSettled([
      callOdoo("/wuchang/xiaoj/api/store-chat", { text: intent }),
      callOdoo("/wuchang/xiaoj/api/store-flair", { text: intent })
    ]);
    if (facts.status !== "fulfilled") {
      $("#odooRouteState").textContent = facts.reason?.message === "HOLD_NOT_ODOO_ORIGIN" ? "請由 Odoo 頁面開啟" : "HOLD";
      $("#gpuRouteState").textContent = "未調用";
      throw facts.reason;
    }
    $("#odooRouteState").textContent = "PASS · 確定性結果";
    $("#gpuRouteState").textContent = flair.status === "fulfilled"
      ? (flair.value.flair ? "PASS · 可替換語氣" : "確定性備援")
      : "HOLD · 不影響結果";
    return { facts: facts.value, flair: flair.status === "fulfilled" ? flair.value : null };
  }

  function renderStorefrontProduct(product) {
    const payload = product.facts;
    const lines = payload.frozen_facts?.order_lines || [];
    if (lines.length) {
      $("#orderSuggestion").textContent = lines.map(line => `${line.name} × ${line.quantity}｜NT$${line.subtotal}`).join("　");
      $("#orderReason").textContent = `${payload.state_zh}；展示預覽合計 NT$${payload.frozen_facts.total}。正式價格、庫存與送單仍待店內 Odoo 對齊。`;
    } else {
      $("#orderSuggestion").textContent = "小 J 已理解，但還需要一個菜單品項";
      $("#orderReason").textContent = payload.xiaoj_line;
    }
    const flair = product.flair?.flair;
    setSpeech(flair ? `${flair} ${payload.xiaoj_line}` : payload.xiaoj_line, false);
    $("#orderResult").classList.add("ready");
    $("#fieldStatusPill").textContent = "Odoo 點餐工具已回應";
  }

  async function understand() {
    const intent = $("#intentInput").value.trim();
    if (!intent) {
      animatePet("waiting", true);
      setSpeech("請先給我一個明確意圖，我不會替您補造未知需求。", true);
      return;
    }
    if (state.busy) return;
    state.busy = true;
    $$('[data-action="understand"], [data-action="cafe-demo"]').forEach(button => { button.disabled = true; });
    animatePet("working");
    $("#flowState").textContent = "形成數位腦細胞中";
    $("#cellState").textContent = "組成中";
    renderFlow(0);
    const scene = currentScene();
    const storefrontRequest = state.scene === "cafe" ? requestStorefront(intent).catch(error => ({ error })) : null;
    const digest = await digestText(`${state.scene}:${intent}:${scene.capabilities.join("|")}`);
    $("#lookupResult").textContent = `${scene.capabilities.length} 項能力全部命中｜${digest.slice(0, 12)}`;
    $("#floatResult").textContent = `理解候選：${intent.slice(0, 28)}${intent.length > 28 ? "…" : ""}｜權威=false`;
    const dValues = {
      D1: intent,
      D2: `${state.imageRef ? "影像✓" : "影像—"}／${state.audioObserved ? "聲音✓" : "聲音—"}／網路=${state.network}`,
      D3: `${scene.label}｜${scene.capabilities.join("、")}`,
      D4: `本機意圖雜湊 ${digest.slice(0, 16)}…；證據不等於權威`,
      D5: "只形成說明與任務候選；外部效果=false",
      D6: `本機基座＋最小必要差量＋${state.network.includes("離線") ? "離線重建" : "傳輸政策 LAN 優先；目前路徑未驗證"}`,
      D7: "去識別、失敗封閉、座標衝突即停止",
      D8: "總場＋自然人；目前未請求真實效果"
    };
    try {
      for (let i = 1; i <= 8; i += 1) {
        await new Promise(resolve => window.setTimeout(resolve, 95));
        renderFlow(i);
        renderDimensions(i, dValues);
      }
      $("#cellState").textContent = "目前僅供展示";
      $("#flowState").textContent = "尚未送出或執行";
      $("#routeLabel").textContent = "NO_TRANSMISSION";
      $("#fieldStatusPill").textContent = "尚未接入總場執行";
      const suggestions = {
        cafe: ["午後柔和咖啡候選", `我依「${intent.slice(0, 22)}${intent.length > 22 ? "…" : ""}」形成口味建議；請再由現場菜單確認品項與價格。`],
        property: ["報修內容候選", "已整理問題、位置與待確認事項；尚未派工。"],
        association: ["服務需求候選", "已整理需求與下一個人工確認點；尚未指派。"],
        personal: ["節費工作路徑候選", "先重用本機上下文，再決定是否需要外部算力。"]
      };
      const [suggestion, reason] = suggestions[state.scene];
      $("#orderSuggestion").textContent = suggestion;
      $("#orderReason").textContent = reason;
      $("#orderResult").classList.add("ready");
      let productHandled = false;
      if (storefrontRequest) {
        const product = await storefrontRequest;
        if (!product.error) {
          renderStorefrontProduct(product);
          productHandled = true;
        }
        else if (product.error.message === "HOLD_NOT_ODOO_ORIGIN") {
          $("#orderSuggestion").textContent = "請從 Odoo 網址開啟，即可使用真實點餐工具";
          $("#orderReason").textContent = "目前是 file:// 檔案預覽；已拒絕假裝連線，也沒有改送其他通路。";
        }
      }
      animatePet("review", true);
      if (!productHandled) setSpeech("我已把你的需求整理成畫面建議；目前沒有下單、付款或播音。", false);
    } finally {
      state.busy = false;
      $$('[data-action="understand"], [data-action="cafe-demo"]').forEach(button => { button.disabled = false; });
    }
  }

  function setScene(sceneId) {
    state.scene = sceneId;
    $$(".scene-tab").forEach(tab => tab.classList.toggle("active", tab.dataset.scene === sceneId));
    $("#intentInput").value = currentScene().example;
    setSpeech(`已切換為${currentScene().role}。核心仍是同一個 8D ADI 完整系統。`);
    $("#lookupResult").textContent = "等待意圖";
    $("#floatResult").textContent = "等待感知";
    $("#cellState").textContent = "等待形成";
    renderDimensions();
    renderFlow();
    animatePet("wave", true);
  }

  function setView(viewId) {
    $$('[data-page]').forEach(section => { section.hidden = section.dataset.page !== viewId; });
    $$('.page-tab').forEach(tab => tab.classList.toggle('active', tab.dataset.view === viewId));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function checkVoiceCapability() {
    $("#voiceRouteState").textContent = "已封閉：找不到同時綁定 Google 商用語音與指定輸出頻道的正式入口；維持靜音";
    setSpeech("語音維持靜音，避免誤送到藍牙或店內廣播。", false);
    animatePet("review", true);
  }

  function observeNetwork() {
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    const link = navigator.onLine ? "瀏覽器回報線上（路徑未驗證）" : "離線最低服務";
    const quality = connection?.effectiveType ? `，${connection.effectiveType}` : "";
    state.network = `${link}${quality}`;
    $("#networkState").textContent = state.network;
    setSpeech(`已觀測網路狀態：${state.network}。這只決定傳輸候選路徑，不代表連線權威。`);
  }

  function observeDevice() {
    state.deviceObserved = true;
    const microphone = "mediaDevices" in navigator ? "麥克風可請求" : "麥克風未知";
    $("#deviceState").textContent = `畫面✓／喇叭${"speechSynthesis" in window ? "✓" : "—"}／${microphone}`;
    setSpeech("設備能力已形成候選索引；沒有權限的能力不會被假定可用。", true);
  }

  function voiceInput() {
    if (!state.voiceConsentPending) {
      state.voiceConsentPending = true;
      $("#audioState").textContent = "辨識可能由瀏覽器供應商處理；再按一次才同意啟動";
      setSpeech("語音辨識路徑尚未驗證。若你同意瀏覽器可能使用供應商服務，請再按一次語音。", false);
      return;
    }
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      state.audioObserved = true;
      $("#audioState").textContent = "瀏覽器不支援即時辨識，使用演練文字";
      setSpeech("此瀏覽器沒有語音辨識介面，已明確標成未知並保持未知，不改送雲端。", true);
      return;
    }
    const recognition = new Recognition();
    recognition.lang = "zh-TW";
    recognition.interimResults = false;
    $("#audioState").textContent = "瀏覽器正在辨識；處理路徑未驗證";
    animatePet("waiting");
    recognition.onresult = event => {
      const text = event.results[0][0].transcript;
      state.audioObserved = true;
      $("#intentInput").value = text;
      $("#audioState").textContent = "語音意圖已轉成文字候選";
      animatePet("review", true);
      state.voiceConsentPending = false;
      setSpeech("聲音已在瀏覽器形成文字候選，尚未執行任何外部作用。", true);
    };
    recognition.onerror = () => {
      $("#audioState").textContent = "語音不可用，保持未知";
      state.voiceConsentPending = false;
      animatePet("failed", true);
    };
    recognition.start();
  }

  async function observeImage(file) {
    if (!file) return;
    const buffer = await file.arrayBuffer();
    const digest = window.crypto?.subtle ? await crypto.subtle.digest("SHA-256", buffer) : null;
    const fullRef = digest ? [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("") : null;
    const ref = fullRef ? fullRef.slice(0, 12) : "無雜湊";
    state.imageRef = `image:${ref}`;
    state.imageEvidenceRef = fullRef ? `sha256:${fullRef}` : null;
    $("#imageState").textContent = `${file.name}｜${ref}`;
    setSpeech("影像只在本機形成雜湊與觀測參照，不上傳，也不做人臉年齡或性別推論。", true);
    animatePet("review", true);
  }

  function startEarthquakeExercise() {
    state.earthquake = true;
    state.scene = "cafe";
    $$(".scene-tab").forEach(tab => tab.classList.toggle("active", tab.dataset.scene === "cafe"));
    $("#earthquakePanel").hidden = false;
    $("#earthquakePanel").scrollIntoView({ behavior: "smooth", block: "center" });
    state.network = "離線最低服務演練";
    $("#networkState").textContent = state.network;
    $("#intentInput").value = "地震特殊狀態：店內安全引導與設備保護提案";
    animatePet("failed", true);
    setSpeech("地震演練：請立即趴下、掩護、穩住。這是隔離模擬，不是國家警報；設備控制只形成提案。", true);
    window.setTimeout(understand, 550);
  }

  function closeEarthquakeExercise() {
    state.earthquake = false;
    $("#earthquakePanel").hidden = true;
    state.network = "尚未觀測";
    $("#networkState").textContent = state.network;
    setScene("cafe");
  }

  function bindEvents() {
    $$("[data-view]").forEach(button => button.addEventListener("click", () => setView(button.dataset.view)));
    $$("[data-view-jump]").forEach(button => button.addEventListener("click", () => setView(button.dataset.viewJump)));
    $$("[data-prompt]").forEach(button => button.addEventListener("click", () => {
      $("#intentInput").value = button.dataset.prompt;
      $("#orderExperience").scrollIntoView({ behavior: "smooth", block: "center" });
    }));
    $$("[data-tool-prompt]").forEach(button => button.addEventListener("click", () => {
      const [scene, prompt] = button.dataset.toolPrompt.split("|", 2);
      setScene(scene);
      setView("customer");
      $("#intentInput").value = prompt;
      window.setTimeout(() => $("#orderExperience").scrollIntoView({ behavior: "smooth", block: "center" }), 80);
    }));
    $$("[data-scene]").forEach(button => button.addEventListener("click", () => setScene(button.dataset.scene)));
    $$("[data-action]").forEach(button => button.addEventListener("click", () => {
      const actions = {
        "cafe-demo": () => { setScene("cafe"); window.setTimeout(understand, 250); },
        "start-order": () => $("#orderExperience").scrollIntoView({ behavior: "smooth", block: "center" }),
        "voice-preview": checkVoiceCapability,
        "earthquake-demo": startEarthquakeExercise,
        understand,
        voice: voiceInput,
        network: observeNetwork,
        device: observeDevice,
        "close-earthquake": closeEarthquakeExercise
      };
      actions[button.dataset.action]?.();
    }));
    $("#imageInput").addEventListener("change", event => observeImage(event.target.files?.[0]));
    $("#intentInput").addEventListener("keydown", event => {
      if (event.key === "Enter") understand();
    });
  }

  function init() {
    PET.element = $("#xiaojPet");
    renderDimensions();
    renderFlow();
    animatePet("idle");
    bindEvents();
    observeNetwork();
    setView("customer");
    $("#clock").textContent = new Intl.DateTimeFormat("zh-TW", { dateStyle: "medium", timeStyle: "short" }).format(new Date());
    window.XiaoJCompetitionDemo = Object.freeze({ understand, setScene, startEarthquakeExercise });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
