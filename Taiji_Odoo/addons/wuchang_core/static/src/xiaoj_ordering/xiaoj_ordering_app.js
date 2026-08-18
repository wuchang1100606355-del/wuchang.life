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

  const MENU_ENDPOINT = "/wuchang/api/cafe/menu/v1";
  const HANDOFF_ENDPOINT = "/api/notification/broadcast";
  const SERVICE_STATE_KEY = "wuchang_xiaoj_service_session_state_v1";
  const TABLE_REF_PATTERN = /^T([1-9]\d?)$/;

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
    { id: "customer_service", label: "顧客服務" },
    { id: "av_ai_menu_display", label: "影音菜單" },
    { id: "business_management", label: "商業管理" },
    { id: "hardware_menu_business_settings", label: "硬體設定" },
  ];

  let state = {
    page: document.body.dataset.startMode || "staff_pos",
    selectedCategory: "全部",
    dryRunMessage: "尚未確認",
    storeRef: document.body.dataset.storeRef || "wuchang_cafe_main_store",
    tableRef: document.body.dataset.tableRef || "",
    serviceSessionRef: "",
    partySize: "",
    currentIntent: "ARRIVE",
    currentMenuContext: "NONE",
    currentSelections: [],
    lastCustomerRequest: "",
    lastServiceResponse: "",
    handoffRef: "",
    handoffState: "",
    liveMenuState: {
      state: "FAIL_CLOSED",
      schema: "LIVE_ODOO_MENU_DATA_READONLY_MAPPING_V1",
      store_ref: document.body.dataset.storeRef || "wuchang_cafe_main_store",
      menu: { categories: [], items: [] },
      mapping_sha256: "",
    },
    liveMenuStatus: "LOADING",
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

  function safeParseJSON(value) {
    try {
      return JSON.parse(value);
    } catch (error) {
      return null;
    }
  }

  function createServiceSessionRef() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return "svc-" + window.crypto.randomUUID();
    }
    return "svc-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
  }

  function loadServiceState() {
    const stored = safeParseJSON(window.sessionStorage.getItem(SERVICE_STATE_KEY) || "");
    if (!stored || typeof stored !== "object") {
      state.serviceSessionRef = createServiceSessionRef();
      persistServiceState();
      return;
    }
    state.serviceSessionRef = String(stored.serviceSessionRef || createServiceSessionRef());
    state.partySize = String(stored.partySize || "");
    state.currentIntent = String(stored.currentIntent || "ARRIVE");
    state.currentMenuContext = String(stored.currentMenuContext || "NONE");
    state.currentSelections = Array.isArray(stored.currentSelections) ? stored.currentSelections.slice() : [];
    state.lastCustomerRequest = String(stored.lastCustomerRequest || "");
    state.lastServiceResponse = String(stored.lastServiceResponse || "");
    state.handoffRef = String(stored.handoffRef || "");
    state.handoffState = String(stored.handoffState || "");
    state.storeRef = String(stored.storeRef || state.storeRef);
  }

  function persistServiceState() {
    window.sessionStorage.setItem(
      SERVICE_STATE_KEY,
      JSON.stringify({
        serviceSessionRef: state.serviceSessionRef,
        storeRef: state.storeRef,
        tableRef: state.tableRef,
        partySize: state.partySize,
        currentIntent: state.currentIntent,
        currentMenuContext: state.currentMenuContext,
        currentSelections: state.currentSelections,
        lastCustomerRequest: state.lastCustomerRequest,
        lastServiceResponse: state.lastServiceResponse,
        handoffRef: state.handoffRef,
        handoffState: state.handoffState,
      }),
    );
  }

  function tableNumberFromRef(tableRef) {
    const match = TABLE_REF_PATTERN.exec(String(tableRef || "").trim().toUpperCase());
    return match ? match[1].replace(/^0+/, "") || "0" : "";
  }

  function tableLabel(tableRef) {
    const number = tableNumberFromRef(tableRef);
    return number ? number + " 號桌" : "";
  }

  function menuItems() {
    const items = (state.liveMenuState.menu && Array.isArray(state.liveMenuState.menu.items)) ? state.liveMenuState.menu.items : [];
    return items
      .filter((item) => item && item.active !== false)
      .slice()
      .sort((left, right) => {
        const leftKey = [left.category || "", left.name || "", left.code || ""].join("|");
        const rightKey = [right.category || "", right.name || "", right.code || ""].join("|");
        return leftKey.localeCompare(rightKey, "zh-Hant");
      });
  }

  function menuCategories() {
    const categories = (state.liveMenuState.menu && Array.isArray(state.liveMenuState.menu.categories)) ? state.liveMenuState.menu.categories.slice() : [];
    if (categories.length > 0) {
      return categories.sort((left, right) => String(left).localeCompare(String(right), "zh-Hant"));
    }
    return Array.from(new Set(menuItems().map((item) => item.category || "其他"))).sort((left, right) => String(left).localeCompare(String(right), "zh-Hant"));
  }

  function menuItemByCode(code) {
    return menuItems().find((item) => item.code === code) || null;
  }

  function normalizePhrase(value) {
    return String(value || "")
      .trim()
      .replace(/\s+/g, " ");
  }

  function normalizeMatchKey(value) {
    return normalizePhrase(value).toLowerCase();
  }

  function summarizeSelectionItems(items) {
    return items.map((item) => `${item.name || item.code || "未命名商品"} 1 杯`).join("、");
  }

  function candidateItemsFromPhrase(phrase) {
    const target = normalizeMatchKey(phrase);
    if (!target) {
      return [];
    }
    return menuItems().filter((item) => {
      const keys = [item.code, item.name, item.description, item.category].map(normalizeMatchKey);
      return keys.some((key) => key && (key === target || key.includes(target) || target.includes(key)));
    });
  }

  function selectionItemsByRefs(refs) {
    return refs.map((code) => menuItemByCode(code)).filter(Boolean);
  }

  function getSelectionSummaryForCurrentState() {
    const items = selectionItemsByRefs(state.currentSelections);
    if (!state.currentSelections.length) {
      return "目前還沒有幫你記任何餐點，要不要一起看看菜單？";
    }
    if (items.length !== state.currentSelections.length) {
      return "我記得這裡有一個先前選擇，但現在菜單資料沒有完整對上，我先不亂報品項。";
    }
    const summary = summarizeSelectionItems(items);
    const label = tableLabel(state.tableRef);
    if (label) {
      return `目前我幫 ${label} 記著：${summary}。這還只是這次服務中的選擇，還沒有送進正式訂單喔。`;
    }
    return `目前我幫你記著：${summary}。這還只是這次服務中的選擇，還沒有送進正式訂單喔。`;
  }

  function summarizeSelectionCodes(codes) {
    const counts = new Map();
    codes.forEach((code) => {
      counts.set(code, (counts.get(code) || 0) + 1);
    });
    return Array.from(counts.entries())
      .map(([code, count]) => {
        const item = menuItemByCode(code);
        const name = item && item.name ? item.name : code;
        return count > 1 ? `${name} x ${count}` : name;
      })
      .join("、");
  }

  function setServiceResponse(message) {
    state.lastServiceResponse = String(message || "");
  }

  function createHandoffRef() {
    const sessionPart = String(state.serviceSessionRef || createServiceSessionRef()).toLowerCase().replace(/[^a-z0-9-]/g, "");
    return "handoff-" + sessionPart + "-" + Date.now().toString(36);
  }

  function requestHumanAssistance() {
    state.currentIntent = "HUMAN_REVIEW";
    state.lastCustomerRequest = "REQUEST_HUMAN_ASSISTANCE";
    state.handoffRef = createHandoffRef();
    state.handoffState = "HUMAN_REVIEW_REQUESTED";
    setServiceResponse("老闆～這個我不會啦，快來救我一下～");
    persistServiceState();
    render();
    if (typeof window.fetch !== "function") {
      state.handoffState = "HUMAN_REVIEW_DISPATCH_FAILED";
      setServiceResponse("糟糕，我剛剛沒叫到人，我再想別的辦法～");
      persistServiceState();
      render();
      return;
    }
    const evidenceRef = state.liveMenuState.mapping_sha256 ? "menu-" + state.liveMenuState.mapping_sha256 : "service-session";
    window.fetch(HANDOFF_ENDPOINT, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "handoff_request",
        handoff_ref: state.handoffRef,
        problem_class: "GENERAL_SERVICE_ASSISTANCE",
        table_ref: state.tableRef || null,
        risk_class: "LOW",
        non_pii_evidence_ref: evidenceRef,
      }),
    })
      .then((response) => response.json())
      .then((payload) => {
        if (!payload || payload.state !== "HUMAN_REVIEW_DISPATCHED" || !payload.receipt) {
          throw new Error("handoff_dispatch_not_accepted");
        }
        state.handoffState = "HUMAN_REVIEW_DISPATCHED";
        setServiceResponse(payload.customer_response || "我已經幫你喊人了，我再陪你等等喔～");
        persistServiceState();
        render();
      })
      .catch(() => {
        state.handoffState = "HUMAN_REVIEW_DISPATCH_FAILED";
        setServiceResponse("糟糕，我剛剛沒叫到人，我再想別的辦法～");
        persistServiceState();
        render();
      });
  }

  function resolvePartySizePhrase(text) {
    const input = String(text || "").trim();

    const numericMatch = input.match(/(\d{1,2})\s*(?:位|人)/);
    if (numericMatch) {
      const size = Number(numericMatch[1]);
      if (Number.isInteger(size) && size >= 1 && size <= 20) {
        return size;
      }
      return null;
    }

    const chineseNumbers = {
      "一": 1,
      "二": 2,
      "三": 3,
      "四": 4,
      "五": 5,
      "六": 6,
      "七": 7,
      "八": 8,
      "九": 9,
      "十": 10,
    };

    const chineseMatch = input.match(/([一二三四五六七八九十])\s*(?:位|人)/);
    if (chineseMatch) {
      return chineseNumbers[chineseMatch[1]] || null;
    }

    return null;
  }

  function resolvePartySizeInput(text) {
    const resolvedPhrase = resolvePartySizePhrase(text);
    if (resolvedPhrase !== null) {
      return resolvedPhrase;
    }

    const input = String(text || "").trim();
    if (/^\d{1,2}$/.test(input)) {
      const size = Number(input);
      if (Number.isInteger(size) && size >= 1 && size <= 20) {
        return size;
      }
    }
    return null;
  }

  function resolveQuantityPhrase(text) {
    const input = normalizePhrase(text);
    if (!input) {
      return null;
    }

    const numericMatch = input.match(/(\d+)\s*(?:杯|份|個|碗|瓶|顆|隻|張|條|盒|包|碟|盤|支|片)/);
    if (numericMatch) {
      const quantity = Number(numericMatch[1]);
      if (Number.isInteger(quantity) && quantity >= 1) {
        return quantity;
      }
      return null;
    }

    const chineseDigits = {
      "一": 1,
      "二": 2,
      "兩": 2,
      "三": 3,
      "四": 4,
      "五": 5,
      "六": 6,
      "七": 7,
      "八": 8,
      "九": 9,
      "十": 10,
    };
    const chineseMatch = input.match(/([一二兩三四五六七八九十])\s*(?:杯|份|個|碗|瓶|顆|隻|張|條|盒|包|碟|盤|支|片)/);
    if (chineseMatch) {
      return chineseDigits[chineseMatch[1]] || null;
    }

    return null;
  }

  function resolveSelectionChangeFromPhrase(phrase) {
    const text = normalizePhrase(phrase);
    const isRemove = /不要了|拿掉|移除|刪除/.test(text);
    const isReplace = /改要|改成|換成/.test(text);
    const isAdd = /加入|再加|再來|也要|我要/.test(text) && !isReplace;
    const mentionsCurrent = /剛才那杯|剛剛那杯|剛才選的|剛剛選的/.test(text);
    const candidates = candidateItemsFromPhrase(text);
    const requestedQuantity = resolveQuantityPhrase(text);

    if (!text) {
      return { ok: false, kind: "empty", message: "你想修改哪一項呢？" };
    }

    if (requestedQuantity !== null) {
      if (mentionsCurrent) {
        if (state.currentSelections.length === 1) {
          const current = selectionItemsByRefs(state.currentSelections)[0];
          if (!current) {
            return { ok: false, kind: "missing_menu", message: "我記得這裡有一個先前選擇，但現在菜單資料沒有完整對上，我先不亂報品項。" };
          }
          return { ok: true, action: "set_quantity", item: current, quantity: requestedQuantity };
        }
        if (state.currentSelections.length > 1) {
          return { ok: false, kind: "ambiguous_current", message: `你是要改哪一杯？目前我幫你記著：${getSelectionSummaryForCurrentState()}` };
        }
        return { ok: false, kind: "empty_selection", message: "目前還沒有幫你記任何餐點，要不要一起看看菜單？" };
      }
      if (candidates.length === 1) {
        const matches = state.currentSelections.filter((code) => code === candidates[0].code);
        if (matches.length === 1) {
          return { ok: true, action: "set_quantity", item: candidates[0], quantity: requestedQuantity };
        }
        if (matches.length > 1) {
          return { ok: false, kind: "ambiguous_item", message: "你是要改哪一杯？我目前找到不只一個相同品項的選擇，先不亂改。" };
        }
        return { ok: false, kind: "missing_item", message: "我記得這裡有一個先前選擇，但現在菜單資料沒有完整對上，我先不亂報品項。" };
      }
    }

    if (isRemove) {
      if (mentionsCurrent) {
        if (state.currentSelections.length === 1) {
          const current = selectionItemsByRefs(state.currentSelections)[0];
          if (!current) {
            return { ok: false, kind: "missing_menu", message: "我記得這裡有一個先前選擇，但現在菜單資料沒有完整對上，我先不亂報品項。" };
          }
          return { ok: true, action: "remove", item: current };
        }
        if (state.currentSelections.length > 1) {
          return { ok: false, kind: "ambiguous_current", message: `你是要拿掉哪一杯？目前我幫你記著：${getSelectionSummaryForCurrentState()}` };
        }
        return { ok: false, kind: "empty_selection", message: "目前還沒有幫你記任何餐點，要不要一起看看菜單？" };
      }
      if (candidates.length === 1) {
        return { ok: true, action: "remove", item: candidates[0] };
      }
      if (candidates.length > 1) {
        return { ok: false, kind: "ambiguous_item", message: "你是要拿掉哪一項？我目前找到不只一個可能品項，先不亂改。" };
      }
      return { ok: false, kind: "missing_item", message: "我記得這裡有一個先前選擇，但現在菜單資料沒有完整對上，我先不亂報品項。" };
    }

    if (isReplace || isAdd) {
      if (candidates.length === 1) {
        return { ok: true, action: isReplace ? "replace" : "add", item: candidates[0] };
      }
      if (candidates.length > 1) {
        return { ok: false, kind: "ambiguous_item", message: "你是要換成哪一項？我目前找到不只一個可能品項，先不亂改。" };
      }
      return { ok: false, kind: "missing_item", message: "我記得這裡有一個先前選擇，但現在菜單資料沒有完整對上，我先不亂報品項。" };
    }

    return { ok: false, kind: "unrecognized", message: "你是要修改哪一項呢？" };
  }

  function applyModifySelectionCommand(rawPhrase) {
    const phrase = normalizePhrase(rawPhrase);
    const resolved = resolveSelectionChangeFromPhrase(phrase);
    state.currentIntent = "MODIFY_SELECTION";
    state.lastCustomerRequest = phrase;

    if (!resolved.ok) {
      setServiceResponse(resolved.message);
      persistServiceState();
      render();
      return;
    }

    if (resolved.action === "set_quantity") {
      const nextSelections = [];
      let quantityApplied = false;
      state.currentSelections.forEach((code) => {
        if (code === resolved.item.code && !quantityApplied) {
          for (let index = 0; index < resolved.quantity; index += 1) {
            nextSelections.push(code);
          }
          quantityApplied = true;
          return;
        }
        if (code !== resolved.item.code) {
          nextSelections.push(code);
        }
      });
      state.currentSelections = nextSelections;
      syncMenuContext();
      setServiceResponse(`好，${resolved.item.name || resolved.item.code} 我幫你改成 ${resolved.quantity} 杯。目前我還幫你記著：${getSelectionSummaryForCurrentState()}`);
      persistServiceState();
      render();
      return;
    }

    if (resolved.action === "remove") {
      state.currentSelections = state.currentSelections.filter((code) => code !== resolved.item.code);
    } else if (resolved.action === "replace") {
      state.currentSelections = [resolved.item.code];
    } else if (resolved.action === "add") {
      state.currentSelections = state.currentSelections.concat([resolved.item.code]);
    }
    syncMenuContext();
    if (resolved.action === "remove") {
      setServiceResponse(`好，${resolved.item.name || resolved.item.code} 先幫你拿掉。目前我還幫你記著：${getSelectionSummaryForCurrentState()}`);
    } else if (resolved.action === "replace") {
      setServiceResponse(`好，改成 ${resolved.item.name || resolved.item.code}。目前我還幫你記著：${getSelectionSummaryForCurrentState()}`);
    } else {
      setServiceResponse(`好，${resolved.item.name || resolved.item.code} 幫你加上去。目前我還幫你記著：${getSelectionSummaryForCurrentState()}`);
    }
    persistServiceState();
    render();
  }

  function formatPrice(item) {
    const price = item && typeof item.normalized_price === "number" ? item.normalized_price : item && typeof item.price === "number" ? item.price : 0;
    return "NT$" + Number(price || 0).toLocaleString("zh-TW");
  }

  function customerGreeting() {
    const label = tableLabel(state.tableRef);
    if (label) {
      return "您好，我是今天為 " + label + " 服務的小J。";
    }
    return "您好，我是小J。請先掃桌牌，或告訴我您坐哪一桌。";
  }

  function customerFollowUp() {
    if (!tableLabel(state.tableRef)) {
      return "請掃桌牌，我才能持續服務這一桌。";
    }
    if (!state.partySize) {
      return "今天幾位呢？";
    }
    return "好，" + state.partySize + " 位。我會在這裡陪你們，有需要直接叫我就好。";
  }

  function syncMenuContext() {
    if (state.liveMenuStatus === "PASS") {
      state.currentMenuContext = "LIVE_ODOO_MENU_DATA";
    }
  }

  function setIntent(intent, message) {
    state.currentIntent = intent;
    state.lastCustomerRequest = message || intent;
    persistServiceState();
    render();
  }

  function setPartySize(value) {
    const resolved = resolvePartySizeInput(value);
    if (resolved === null) {
      state.lastCustomerRequest = "party_size_invalid";
      persistServiceState();
      render();
      return;
    }
    state.partySize = String(resolved);
    state.currentIntent = "SET_PARTY_SIZE";
    state.lastCustomerRequest = "party_size:" + resolved;
    setServiceResponse(`好，${resolved} 位。我會在這裡陪你們，有需要直接叫我就好。`);
    persistServiceState();
    render();
  }

  function addSelection(code) {
    const item = menuItemByCode(code);
    if (!item) {
      return;
    }
    state.currentSelections = state.currentSelections.concat([code]);
    state.currentIntent = "SELECT_ITEM";
    state.lastCustomerRequest = "select_item:" + code;
    syncMenuContext();
    persistServiceState();
    render();
  }

  function removeSelection(code) {
    state.currentSelections = state.currentSelections.filter((value) => value !== code);
    state.currentIntent = "MODIFY_SELECTION";
    state.lastCustomerRequest = "remove_item:" + code;
    persistServiceState();
    render();
  }

  function currentSelectionItems() {
    return state.currentSelections.map((code) => menuItemByCode(code)).filter(Boolean);
  }

  function recallCurrentSelectionsMessage() {
    return getSelectionSummaryForCurrentState();
  }

  function recommendedItems() {
    const resolution = resolveRecommendationFromPhrase(state.lastCustomerRequest || "");
    return resolution.items;
  }

  function itemEvidenceText(item) {
    const addonText = Array.isArray(item && item.addons)
      ? item.addons.map((addon) => [addon && addon.name, addon && addon.code, addon && addon.addon_type].filter(Boolean).join(" ")).join(" ")
      : "";
    const optionText = Array.isArray(item && item.options)
      ? item.options
          .map((option) => {
            const allowedValues = Array.isArray(option && option.allowed_values)
              ? option.allowed_values.map((value) => value && (value.name || value.display_name || "")).join(" ")
              : "";
            return [option && option.name, option && option.code, option && option.selection_type, allowedValues].filter(Boolean).join(" ");
          })
          .join(" ")
      : "";
    return normalizeMatchKey([item && item.name, item && item.category, item && item.description, addonText, optionText, item && item.normalized_price_note].filter(Boolean).join(" "));
  }

  function resolveRecommendationFromPhrase(rawPhrase) {
    const phrase = normalizePhrase(rawPhrase);
    const items = menuItems();
    if (!phrase) {
      return {
        items: [],
        message: "你現在比較想喝冰的、熱的、咖啡或順口一點的呢？我會照現在菜單幫你縮小。",
      };
    }

    const ruleSets = [];
    if (/冰/.test(phrase)) {
      ruleSets.push(["冰", ["冰", "冰飲", "冷", "冷飲"]]);
    }
    if (/熱/.test(phrase)) {
      ruleSets.push(["熱", ["熱", "熱飲"]]);
    }
    if (/咖啡/.test(phrase)) {
      ruleSets.push(["咖啡", ["咖啡"]]);
    }
    if (/不.*酸|少酸|低酸|酸/.test(phrase)) {
      ruleSets.push(["酸度", ["不酸", "低酸"]]);
    }
    if (/第一次|新手|入門|初次/.test(phrase)) {
      ruleSets.push(["新手", ["順口", "柔和", "奶", "拿鐵", "溫和"]]);
    }
    if (/順口/.test(phrase)) {
      ruleSets.push(["順口", ["順口", "柔和", "奶"]]);
    }

    const matchedRules = ruleSets.filter(([, keywords]) => keywords.length > 0);
    if (!matchedRules.length) {
      return {
        items: [],
        message: "我想再多知道一點你的方向。你比較在意冰熱、咖啡，還是想要順口一點？我會照現在菜單幫你縮小。",
      };
    }

    const filtered = items.filter((item) => {
      const evidence = itemEvidenceText(item);
      return matchedRules.every(([, keywords]) => keywords.some((keyword) => evidence.includes(normalizeMatchKey(keyword))));
    });

    if (!filtered.length) {
      return {
        items: [],
        message: "目前菜單資料沒有足夠證據支撐這個偏好，我不想亂推薦。你可以再告訴我你比較在意冰熱、咖啡、還是想要順口一點。",
      };
    }

    return {
      items: filtered.slice(0, 3),
      message: `目前有證據的候選是：${filtered.slice(0, 3).map((item) => item.name || item.code || "未命名商品").join("、")}。`,
    };
  }

  function applyRecommendationCommand(rawPhrase) {
    const phrase = normalizePhrase(rawPhrase || "有什麼推薦？");
    const resolved = resolveRecommendationFromPhrase(phrase);
    state.currentIntent = "ASK_RECOMMENDATION";
    state.lastCustomerRequest = phrase;
    syncMenuContext();
    setServiceResponse(resolved.message);
    persistServiceState();
    render();
  }

  function customerFacingHighlights() {
    const table = tableLabel(state.tableRef) || "請先掃桌牌";
    const partySize = state.partySize || "尚未告訴小J";
    const currentSelections = state.currentSelections.length
      ? summarizeSelectionCodes(state.currentSelections)
      : "目前還沒有幫你記任何餐點，要不要一起看看菜單？";
    const lastResponse = state.lastServiceResponse || customerFollowUp();
    return [
      ["今天服務的桌", table],
      ["今天幾位", partySize],
      ["目前幫你記著", currentSelections],
      ["小J回應", lastResponse],
    ];
  }

  function menuContextCards(items) {
    if (!items.length) {
      return '<div class="wide-row"><span>目前沒有可公開顯示的菜單項目</span><strong>請稍候</strong></div>';
    }
    return items.map((item) => `
      <article class="item-card">
        <div class="badge">${escapeHtml(item.category || "其他")}</div>
        <h3>${escapeHtml(item.name || item.code || "未命名商品")}</h3>
        <div class="price">${escapeHtml(formatPrice(item))}</div>
        ${item.description ? `<div class="meta">${escapeHtml(item.description)}</div>` : ""}
        <button data-add-item="${escapeHtml(item.code || "")}">我要這杯</button>
      </article>
    `).join("");
  }

  function customerServicePage() {
    const rows = customerFacingHighlights()
      .map(([label, value]) => `<div class="wide-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
      .join("");
    const selections = currentSelectionItems();
    const selectionRows = selections.length
      ? selections.map((item) => `<div class="wide-row"><span>${escapeHtml(item.name || item.code || "")}</span><button data-remove-item="${escapeHtml(item.code || "")}">不要了</button></div>`).join("")
      : '<div class="wide-row"><span>目前還沒有選項</span><strong>空</strong></div>';
    const categories = menuCategories();
    const categoryButtons = categories.length
      ? categories.map((category) => `<button data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`).join("")
      : '<span class="badge warn">菜單載入中</span>';
    const menuItemsHtml = menuContextCards(menuItems());
    const recommendations = recommendedItems();
    const recommendationHtml = recommendations.length
      ? recommendations.map((item) => `<div class="wide-row"><span>${escapeHtml(item.name || item.code || "")}</span><button data-add-item="${escapeHtml(item.code || "")}">加入建議</button></div>`).join("")
      : '<div class="wide-row"><span>推薦尚未準備好</span><strong>請稍候</strong></div>';
    const recallMessage = recallCurrentSelectionsMessage();
    return `
      <div class="hero-band">
        <div class="hero-card">
          <h2>${escapeHtml(customerGreeting())}</h2>
          <p>${escapeHtml(customerFollowUp())}</p>
          <div class="toolbar">
            <button data-intent="VIEW_MENU">看菜單</button>
            <button data-intent="ASK_RECOMMENDATION">有什麼推薦？</button>
            <button data-intent="RECALL_CURRENT_SELECTIONS">剛才我選什麼？</button>
            <button data-intent="CALL_XIAOJ">叫小J</button>
            <button data-intent="HUMAN_REVIEW">請店員幫忙</button>
          </div>
        </div>
        <div class="quick-stats">
          <div class="stat"><span>服務桌</span><strong>${escapeHtml(tableLabel(state.tableRef) || "待掃描")}</strong></div>
          <div class="stat"><span>今天人數</span><strong>${escapeHtml(state.partySize || "未設定")}</strong></div>
          <div class="stat"><span>目前選擇</span><strong>${String(state.currentSelections.length)}</strong></div>
          <div class="stat"><span>小J狀態</span><strong>陪你點餐中</strong></div>
        </div>
      </div>
      <div class="content split">
        <section class="panel pad">
          <h2 class="section-title">這桌的持續服務狀態</h2>
          <div class="wide-list">${rows}</div>
          <div class="toolbar" style="margin-top:12px">
            <input type="text" value="${escapeHtml(state.partySize)}" placeholder="例如：我們三位 / 3位 / 三人" data-party-size-input />
            <button data-party-size-save>設定人數</button>
          </div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">即時推薦</h2>
          <div class="toolbar" style="margin-bottom:12px">
            <input type="text" placeholder="例如：我不喜歡酸的 / 想喝比較順口的 / 有沒有適合第一次喝咖啡的人" data-recommendation-input />
            <button data-recommendation-submit>送出推薦需求</button>
          </div>
          <div class="wide-list">${recommendationHtml}</div>
        </section>
      </div>
      <div class="content split">
        <section class="panel pad">
          <h2 class="section-title">真實菜單</h2>
          <div class="toolbar">${categoryButtons}</div>
          <div class="cards">${menuItemsHtml}</div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">目前已選</h2>
          <div class="wide-list">${selectionRows}</div>
          <h2 class="section-title" style="margin-top:18px">小J 回顧</h2>
          <div class="proof-code">${escapeHtml(recallMessage)}</div>
          <h2 class="section-title" style="margin-top:18px">修改選擇</h2>
          <div class="toolbar" style="margin-top:12px">
            <input type="text" placeholder="例如：檸檬汁不要了 / 把剛才那杯拿掉 / 我改要招牌咖啡" data-modify-selection-input />
            <button data-modify-selection-submit>送出修改</button>
          </div>
          <div class="wide-row" style="margin-top:12px"><span>小J 說</span><strong>${escapeHtml(state.lastServiceResponse || "")}</strong></div>
        </section>
      </div>
    `;
  }

  function bootstrapCustomerService() {
    if (typeof window.sessionStorage === "undefined") {
      return;
    }
    loadServiceState();
    syncMenuContext();
    if (!state.serviceSessionRef) {
      state.serviceSessionRef = createServiceSessionRef();
      persistServiceState();
    }
    if (state.page === "customer_service") {
      state.currentIntent = state.currentIntent || "ARRIVE";
      persistServiceState();
    }
  }

  function loadLiveMenuData() {
    if (typeof window.fetch !== "function") {
      state.liveMenuStatus = "FAIL_CLOSED";
      render();
      return;
    }
    window.fetch(MENU_ENDPOINT, { method: "GET", credentials: "same-origin" })
      .then((response) => response.json())
      .then((payload) => {
        if (!payload || payload.state !== "PASS") {
          state.liveMenuStatus = "FAIL_CLOSED";
          state.liveMenuState = {
            state: "FAIL_CLOSED",
            schema: "LIVE_ODOO_MENU_DATA_READONLY_MAPPING_V1",
            store_ref: state.storeRef,
            menu: { categories: [], items: [] },
            mapping_sha256: "",
          };
          syncMenuContext();
          render();
          return;
        }
        state.liveMenuStatus = "PASS";
        state.liveMenuState = payload;
        state.storeRef = String(payload.store_ref || state.storeRef);
        syncMenuContext();
        persistServiceState();
        render();
      })
      .catch(() => {
        state.liveMenuStatus = "FAIL_CLOSED";
        state.liveMenuState = {
          state: "FAIL_CLOSED",
          schema: "LIVE_ODOO_MENU_DATA_READONLY_MAPPING_V1",
          store_ref: state.storeRef,
          menu: { categories: [], items: [] },
          mapping_sha256: "",
        };
        syncMenuContext();
        render();
      });
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
    return ["全部"].concat(menuCategories());
  }

  function filteredMenu() {
    const items = menuItems();
    if (state.selectedCategory === "全部") return items;
    return items.filter((item) => item.category === state.selectedCategory);
  }

  function layout(content) {
    const isCustomerPage = state.page === "customer_service";
    app.innerHTML = `
      <header class="topbar">
        <div class="brand">
          <h1>聊國咖啡館｜小J 主權式影音點餐 AI</h1>
          <p>${isCustomerPage ? "今天由小J陪你點餐" : "瀏覽器封裝程式｜雲端候選、本地驗證、人類確認、Odoo 落地"}</p>
        </div>
        ${isCustomerPage ? "" : `<nav class="mode-tabs">
          ${pages.map((page) => `<button class="${state.page === page.id ? "active" : ""}" data-page="${page.id}">${page.label}</button>`).join("")}
        </nav>`}
      </header>
      <section class="grid" style="${isCustomerPage ? "grid-template-columns: 1fr;" : ""}">
        ${isCustomerPage ? "" : leftRail()}
        <section class="panel workspace">${content}</section>
        ${isCustomerPage ? "" : rightRail()}
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
    app.querySelectorAll("[data-intent]").forEach((button) => {
      button.addEventListener("click", () => {
        const intent = button.dataset.intent;
        if (intent === "VIEW_MENU") {
          syncMenuContext();
          setIntent("VIEW_MENU", "看菜單");
          return;
        }
        if (intent === "ASK_RECOMMENDATION") {
          syncMenuContext();
          applyRecommendationCommand("有什麼推薦？");
          return;
        }
        if (intent === "RECALL_CURRENT_SELECTIONS") {
          syncMenuContext();
          setIntent("RECALL_CURRENT_SELECTIONS", "剛才我選什麼？");
          return;
        }
        if (intent === "CALL_XIAOJ") {
          setIntent("CALL_XIAOJ", "叫小J");
          return;
        }
        if (intent === "HUMAN_REVIEW") {
          requestHumanAssistance();
        }
      });
    });
    app.querySelectorAll("[data-add-item]").forEach((button) => {
      button.addEventListener("click", () => addSelection(button.dataset.addItem));
    });
    app.querySelectorAll("[data-remove-item]").forEach((button) => {
      button.addEventListener("click", () => removeSelection(button.dataset.removeItem));
    });
    app.querySelectorAll("[data-modify-selection-submit]").forEach((button) => {
      button.addEventListener("click", () => {
        const input = app.querySelector("[data-modify-selection-input]");
        applyModifySelectionCommand(input ? input.value : "");
      });
    });
    app.querySelectorAll("[data-recommendation-submit]").forEach((button) => {
      button.addEventListener("click", () => {
        const input = app.querySelector("[data-recommendation-input]");
        applyRecommendationCommand(input ? input.value : "");
      });
    });
    const modifyInput = app.querySelector("[data-modify-selection-input]");
    if (modifyInput) {
      modifyInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          applyModifySelectionCommand(modifyInput.value);
        }
      });
    }
    const recommendationInput = app.querySelector("[data-recommendation-input]");
    if (recommendationInput) {
      recommendationInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          applyRecommendationCommand(recommendationInput.value);
        }
      });
    }
    const partySizeInput = app.querySelector("[data-party-size-input]");
    const partySizeSave = app.querySelector("[data-party-size-save]");
    if (partySizeInput && partySizeSave) {
      partySizeSave.addEventListener("click", () => setPartySize(partySizeInput.value));
      partySizeInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          setPartySize(partySizeInput.value);
        }
      });
    }
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
    const summaryRows = [
      ["LIVE_MENU_STATUS", state.liveMenuStatus || "UNKNOWN"],
      ["CURRENT_SELECTIONS", state.currentSelections.length ? summarizeSelectionCodes(state.currentSelections) : "空"],
      ["CURRENT_MENU_CONTEXT", state.currentMenuContext || "NONE"],
      ["SERVICE_SESSION_REF", state.serviceSessionRef || "未設定"],
    ]
      .map(([label, value]) => `<div class="status-row"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>`)
      .join("");
    return `
      <aside class="right-rail">
        <section class="panel pad">
          <h2 class="section-title">即時營運投影</h2>
          ${state.liveMenuStatus === "PASS" ? `<div class="wide-list">${summaryRows}</div>` : '<div class="proof-code">目前沒有候選訂單</div>'}
        </section>
        <section class="panel pad">
          <h2 class="section-title">8D Proof</h2>
          <div class="proof-code">packet_ref=NONE<br/>d8_ref=NONE<br/>state=${escapeHtml(state.dryRunMessage)}</div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">Safety Flags</h2>
          ${Object.entries(safety).map(([key, value]) => `<div class="status-row"><span>${key}</span><b class="badge ok">${String(value).toUpperCase()}</b></div>`).join("")}
        </section>
      </aside>
    `;
  }

  function menuCards(limit) {
    const items = filteredMenu();
    return items.length ? items.slice(0, limit || 9).map((item) => `
      <article class="item-card">
        <div class="badge">${escapeHtml(item.category)}</div>
        <h3>${escapeHtml(item.name)}</h3>
        <div class="price">${money(item.price)}</div>
        <div class="meta">${escapeHtml(item.code)}｜Odoo menu ref</div>
        <button data-dry-run="加入 ${escapeHtml(item.name)} 候選">加入候選</button>
      </article>
    `).join("") : '<div class="wide-row"><span>即時菜單尚未取得</span><strong>EMPTY/UNAVAILABLE</strong></div>';
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
    const menuStateBlock = state.liveMenuStatus === "PASS"
      ? `<div class="cards">${menuCards(9)}</div>`
      : '<div class="wide-list"><div class="wide-row"><span>即時菜單尚未取得</span><strong>EMPTY/UNAVAILABLE</strong></div></div>';
    return `
      <div class="hero-band">
        <div class="hero-card">
          <h2>店員 POS：快速點餐、候選驗證、正式寫入前 HOLD</h2>
          <p>店員用這頁承接語音/觸控候選單，所有金額與折扣都由本地後腦重算，按下確認也只產生 dry-run gate。</p>
          <div class="toolbar">${categoryButtons}</div>
        </div>
        <div class="quick-stats">
          <div class="stat"><span>今日候選單</span><strong>尚未取得</strong></div>
          <div class="stat"><span>待確認</span><strong>尚未取得</strong></div>
          <div class="stat"><span>本地驗證</span><strong>尚未取得</strong></div>
          <div class="stat"><span>正式寫 POS</span><strong>0</strong></div>
        </div>
      </div>
      <div class="content">${menuStateBlock}</div>
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
    const topTicker = state.liveMenuStatus === "PASS"
      ? [
          "LIVE_ODOO_MENU_DATA 已取得",
          "正式營運不使用 demo menu",
          "所有商品事實只從 Odoo 投影",
        ]
      : ["即時菜單尚未取得", "正式營運不顯示 demo menu", "請稍候或檢查 live data"];
    const bottomTicker = state.liveMenuStatus === "PASS"
      ? [
          "顯示來源：LIVE_ODOO_MENU_DATA",
          "候選資訊僅供暫態服務使用",
          "正式交易與付款仍 HOLD",
        ]
      : ["LIVE ODOO unavailable", "EMPTY/UNAVAILABLE", "DEMO MENU disabled"];
    return `
      ${ticker(topTicker, "top")}
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
        ${state.liveMenuStatus === "PASS" ? `<div class="cards">${menuCards(6)}</div>` : '<div class="wide-list"><div class="wide-row"><span>即時菜單尚未取得</span><strong>EMPTY/UNAVAILABLE</strong></div></div>'}
        <section class="display-asset-panel">
          <div>
            <h2 class="section-title">大菜單 / 接客顯示機角色資產</h2>
            <p>VRM 檔放入靜態路徑後，顯示機以此作為小J角色來源；目前仍是顯示候選，不觸發正式 POS 或付款。</p>
          </div>
          <div class="proof-code">avatar_file=${escapeHtml(xiaojAvatar.fileName)}<br/>avatar_path=${escapeHtml(xiaojAvatar.assetPath)}<br/>display_mode=${escapeHtml(xiaojAvatar.mode)}</div>
        </section>
      </div>
      ${ticker(bottomTicker, "bottom")}
    `;
  }

  function businessManagementPage() {
    const liveMenuCount = state.liveMenuStatus === "PASS" ? menuItems().length : null;
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
          <div class="stat"><span>店內現金</span><strong>尚未取得</strong></div>
          <div class="stat"><span>社群互動</span><strong>尚未取得</strong></div>
          <div class="stat"><span>維護待辦</span><strong>尚未取得</strong></div>
          <div class="stat"><span>毛利雷達</span><strong>${liveMenuCount === null ? "UNKNOWN" : "可計算"}</strong></div>
        </div>
      </div>
      <div class="content split">
        <section class="panel pad">
          <h2 class="section-title">分級子功能</h2>
          <div class="wide-list">
            <div class="wide-row"><span>現金日結與交班</span><b class="badge warn">尚未取得</b></div>
            <div class="wide-row"><span>社群 AI 回訪與活動</span><b class="badge warn">尚未取得</b></div>
            <div class="wide-row"><span>維護排程與硬體健康</span><b class="badge warn">尚未取得</b></div>
            <div class="wide-row"><span>商品銷售與折扣分析</span><b class="badge warn">需 live data</b></div>
          </div>
        </section>
        <section class="panel pad">
          <h2 class="section-title">商業資訊分析</h2>
          <div class="wide-list">
            <div class="wide-row"><span>高毛利推薦</span><strong>尚未取得</strong></div>
            <div class="wide-row"><span>維護風險</span><strong>尚未取得</strong></div>
            <div class="wide-row"><span>社群任務</span><strong>尚未取得</strong></div>
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
      customer_service: customerServicePage,
      av_ai_menu_display: avDisplayPage,
      business_management: businessManagementPage,
      hardware_menu_business_settings: settingsPage,
    }[state.page] || staffPosPage;
    layout(page());
  }

  bootstrapCustomerService();
  loadLiveMenuData();
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
