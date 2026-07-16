(function () {
  "use strict";

  var MENU_DATA = window.WUCHANG_QUICKCLICK_MENU;
  if (!MENU_DATA || MENU_DATA.schema !== "w7tp.quickclick_menu_web.v1") {
    throw new Error("QUICKCLICK_MENU_DATA_UNAVAILABLE");
  }

  var RECTIFIER = window.WUCHANG_CAFE_POS_TOTAL_FIELD_RECTIFIER;
  var AI_INTENT = window.WUCHANG_CAFE_POS_AI_INTENT;
  if (!RECTIFIER || !AI_INTENT) {
    throw new Error("CAFE_POS_FLOW_MODULE_UNAVAILABLE");
  }

  var MENU_SOURCE = Object.freeze({
    id: MENU_DATA.source.id,
    scope: MENU_DATA.source.name,
    sha256: MENU_DATA.source.sha256,
    source_row_count: MENU_DATA.source.sourceProductCount,
    active_row_count: MENU_DATA.source.activeProductCount,
    excluded_row_count: MENU_DATA.source.excludedProductCount,
    excluded_source_categories: MENU_DATA.source.excludedSourceCategories,
    option_group_count: MENU_DATA.source.optionGroupCount,
    normalized_option_count: MENU_DATA.source.normalizedOptionCount,
    raw_option_row_count: MENU_DATA.source.rawOptionRowCount,
    source_warning_count: MENU_DATA.source.sourceWarningCount,
    authority_state: MENU_DATA.source.authorityState,
    observation: "QUICKCLICK_RAW_XLSX_READ_ONLY"
  });
  var MENU = MENU_DATA.products;
  var OPTION_GROUPS = MENU_DATA.optionGroups;
  var CATEGORY_LABELS = MENU_DATA.categories.reduce(function (result, category) {
    result[category.id] = category.label;
    return result;
  }, {});

  var WORKFLOWS = {
    counter: {
      overline: "HUMAN COUNTER REVIEW",
      title: "店員先覆核，候選才可進展示佇列",
      description: "核對品項、來源選項與服務方式；即使覆核完成，仍不等於正式 POS 訂單或付款授權。",
      steps: ["選擇 QuickClick 權威商品", "依序完成尺寸、溫度、甜度與口味", "建立 8D 候選並由店員覆核"]
    },
    cup: {
      overline: "SYNTHETIC CUP REDEMPTION",
      title: "匿名案例先提出核銷，再由店員確認",
      description: "案例只使用 SYN-CUP-014，不收姓名、電話或會員末碼；確認後僅改變瀏覽器記憶體中的展示杯數。",
      steps: ["讀取合成記杯參照", "提出核銷 1 杯候選", "由店員確認展示核銷"]
    },
    offline: {
      overline: "EDGE CONTINUITY",
      title: "斷線可整理候選，回線必須重新驗證",
      description: "離線佇列只保存 L3 候選與內容雜湊；沒有 taiji01 總場與人工 D8，就不形成正式交易事實。",
      steps: ["切換至離線展示狀態", "建立 hash-chain 合成候選", "回線後由 taiji01 重驗與去重"]
    }
  };

  function initialState() {
    return {
      category: "all",
      workflow: "counter",
      cart: [],
      configuringProductId: null,
      selections: {},
      candidate: null,
      candidateCanonical: "",
      candidateHash: "",
      staffReviewed: false,
      queue: [],
      offline: false,
      cupRemaining: 12,
      redeemPending: false,
      eventSeq: 0,
      events: [{ seq: 0, label: "DEMO_READY" }],
      redteamCycle: 0
    };
  }

  var state = initialState();

  function byId(id) {
    return document.getElementById(id);
  }

  function announce(message) {
    byId("announcement").textContent = message;
  }

  function money(value) {
    var sign = value < 0 ? "−" : "";
    return sign + "NT$ " + String(Math.abs(value));
  }

  function priceDelta(value) {
    if (value === 0) {
      return "不加價";
    }
    return (value > 0 ? "+" : "−") + "NT$ " + String(Math.abs(value));
  }

  function logEvent(label) {
    state.eventSeq += 1;
    state.events.push({ seq: state.eventSeq, label: label });
    renderEventLog();
  }

  function eventCode(sequence) {
    return "SEQ-" + String(sequence).padStart(3, "0");
  }

  function renderEventLog() {
    var log = byId("event-log");
    log.replaceChildren();
    state.events.slice(-8).forEach(function (event) {
      var item = document.createElement("li");
      item.textContent = eventCode(event.seq) + " · " + event.label;
      log.appendChild(item);
    });
  }

  function evaluateRedteam(trigger, alertCode) {
    state.redteamCycle += 1;
    var monitor = byId("cafe-redteam-monitor");
    var clear = !alertCode;
    var status = clear ? "MONITORING CLEAR" : "DRIFT ALERT";
    monitor.dataset.state = clear ? "MONITORING_CLEAR" : "DRIFT_ALERT";
    byId("redteam-state").textContent = status;
    byId("strip-redteam-state").textContent = status;
    byId("redteam-cycle").textContent = "cycle " + String(state.redteamCycle) + " · " + trigger;
    byId("redteam-message").textContent = clear
      ? "本次轉換已檢查：商品與選項皆有 QuickClick 來源，未產生正式訂單、付款、會員明文或資料庫寫入。"
      : alertCode + " · 已阻擋越過候選邊界的操作，狀態與付款計數均未改變。";
  }

  function categoryName(category) {
    return CATEGORY_LABELS[category] || "商品";
  }

  function productFor(id) {
    return RECTIFIER.productFor(MENU_DATA, id);
  }

  function questionsForProduct(product) {
    return RECTIFIER.questionsForProduct(MENU_DATA, product);
  }

  function optionFor(question, optionId) {
    return RECTIFIER.optionFor(question, optionId);
  }

  function renderMenu() {
    var grid = byId("menu-grid");
    grid.replaceChildren();
    var visibleProducts = MENU.filter(function (product) {
      return state.category === "all" || product.category === state.category;
    });
    visibleProducts.forEach(function (product) {
      var button = document.createElement("button");
      var category = document.createElement("small");
      var name = document.createElement("strong");
      var detail = document.createElement("span");
      var price = document.createElement("b");

      button.type = "button";
      button.className = "menu-item";
      button.dataset.addProduct = product.id;
      button.setAttribute("aria-label", "選擇 " + product.name + "，QuickClick 來源價 " + money(product.price));
      category.textContent = categoryName(product.category) + "／" + product.sourceCategory + " · " + product.id;
      name.textContent = product.name;
      detail.textContent = product.sourceRef + " · " + (product.optionGroupIds.length
        ? "需完成來源選項"
        : "無綁定選項 · 可直接加入");
      price.textContent = money(product.price) + " · QuickClick 來源價";
      button.append(category, name, detail, price);
      grid.appendChild(button);
    });
    if (!visibleProducts.length) {
      var paused = document.createElement("p");
      paused.className = "catalog-paused";
      paused.textContent = state.category === "drip"
        ? "濾掛咖啡保留於來源分類，但依商品策略暫停販售；6 項商品不提供人類或 AI 加入候選。"
        : "此分類目前沒有啟用商品。";
      grid.appendChild(paused);
    }

    document.querySelectorAll("[data-category]").forEach(function (button) {
      button.setAttribute("aria-selected", String(button.dataset.category === state.category));
    });
  }

  function selectedConfiguration(product) {
    return questionsForProduct(product).map(function (question) {
      var option = optionFor(question, state.selections[question.id]);
      return option ? {
        questionId: question.id,
        questionName: question.displayName,
        optionId: option.id,
        optionName: option.displayName,
        priceDelta: option.priceDelta
      } : null;
    }).filter(Boolean);
  }

  function configurationComplete(product) {
    return questionsForProduct(product).every(function (question) {
      return !question.required || Boolean(state.selections[question.id]);
    });
  }

  function configurationPrice(product) {
    return product.price + selectedConfiguration(product).reduce(function (sum, selection) {
      return sum + selection.priceDelta;
    }, 0);
  }

  function selectionSummary(selections) {
    return selections.length
      ? selections.map(function (selection) {
        return selection.questionName + "：" + selection.optionName;
      }).join("／")
      : "無選項";
  }

  function renderConfigurator() {
    var panel = byId("item-configurator");
    var product = state.configuringProductId ? productFor(state.configuringProductId) : null;
    if (!product) {
      panel.hidden = true;
      byId("option-questions").replaceChildren();
      return;
    }

    panel.hidden = false;
    byId("config-product-name").textContent = product.name;
    byId("config-product-source").textContent =
      product.sourceRef + " · " + product.sourceCategory + " · QuickClick 來源價 " + money(product.price);

    var container = byId("option-questions");
    container.replaceChildren();
    var questions = questionsForProduct(product);
    if (!questions.length) {
      var noOptions = document.createElement("p");
      noOptions.className = "config-empty";
      noOptions.textContent = "此商品在權威匯出中沒有綁定選項，仍須由人員確認後加入。";
      container.appendChild(noOptions);
    }

    questions.forEach(function (question) {
      var section = document.createElement("section");
      var heading = document.createElement("div");
      var title = document.createElement("h4");
      var requirement = document.createElement("span");
      var options = document.createElement("div");

      section.className = "option-question";
      section.dataset.question = question.id;
      heading.className = "option-question-heading";
      title.textContent = question.displayName;
      requirement.textContent = question.required ? "必選 1 項" : "選填";
      heading.append(title, requirement);

      options.className = "option-buttons";
      question.options.forEach(function (option) {
        var button = document.createElement("button");
        var label = document.createElement("strong");
        var delta = document.createElement("small");
        var selected = state.selections[question.id] === option.id;
        button.type = "button";
        button.dataset.questionId = question.id;
        button.dataset.optionId = option.id;
        button.setAttribute("aria-pressed", String(selected));
        button.setAttribute("aria-label", question.displayName + "選擇" + option.displayName + "，" + priceDelta(option.priceDelta));
        label.textContent = option.displayName;
        delta.textContent = priceDelta(option.priceDelta);
        button.append(label, delta);
        options.appendChild(button);
      });
      section.append(heading, options);
      container.appendChild(section);
    });

    var selections = selectedConfiguration(product);
    var incomplete = questions.filter(function (question) {
      return question.required && !state.selections[question.id];
    });
    byId("config-summary").textContent = incomplete.length
      ? "尚待選擇：" + incomplete.map(function (question) { return question.displayName; }).join("、")
      : "已選：" + selectionSummary(selections);
    byId("config-price").textContent = money(configurationPrice(product));
    byId("confirm-config").disabled = !configurationComplete(product);
  }

  function openConfigurator(productId, source) {
    state.configuringProductId = productId;
    state.selections = {};
    renderConfigurator();
    byId("intent-status").textContent = source === "intent"
      ? "已找到來源商品；請檢查辨識結果並完成缺少的必選項。"
      : "請依序選擇來源綁定選項，再確認加入候選單。";
    byId("item-configurator").scrollIntoView({ block: "nearest" });
  }

  function closeConfigurator() {
    state.configuringProductId = null;
    state.selections = {};
    renderConfigurator();
  }

  function totalQuantity() {
    return state.cart.reduce(function (sum, line) { return sum + line.quantity; }, 0);
  }

  function totalValue() {
    return state.cart.reduce(function (sum, line) {
      return sum + line.unitPrice * line.quantity;
    }, 0);
  }

  function renderCart() {
    var lines = byId("cart-lines");
    lines.replaceChildren();

    if (!state.cart.length) {
      var empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "點選左側權威商品，完成必選題組後建立本機合成候選。";
      lines.appendChild(empty);
    } else {
      state.cart.forEach(function (line) {
        var product = productFor(line.productId);
        var row = document.createElement("div");
        var copy = document.createElement("div");
        var title = document.createElement("strong");
        var modifiers = document.createElement("span");
        var detail = document.createElement("small");
        var controls = document.createElement("div");
        var minus = document.createElement("button");
        var quantity = document.createElement("span");
        var plus = document.createElement("button");

        row.className = "cart-line";
        title.textContent = product.name;
        modifiers.className = "line-modifiers";
        modifiers.textContent = selectionSummary(line.selections);
        detail.textContent = product.sourceRef + " · " + money(line.unitPrice) + " × " + String(line.quantity);
        copy.append(title, modifiers, detail);

        controls.className = "line-controls";
        minus.type = "button";
        minus.dataset.lineAction = "decrease";
        minus.dataset.lineKey = line.key;
        minus.setAttribute("aria-label", "減少 " + product.name + "，" + selectionSummary(line.selections));
        minus.textContent = "−";
        quantity.textContent = String(line.quantity);
        quantity.setAttribute("aria-label", product.name + " 數量");
        plus.type = "button";
        plus.dataset.lineAction = "increase";
        plus.dataset.lineKey = line.key;
        plus.setAttribute("aria-label", "增加 " + product.name + "，" + selectionSummary(line.selections));
        plus.textContent = "+";
        controls.append(minus, quantity, plus);
        row.append(copy, controls);
        lines.appendChild(row);
      });
    }

    byId("cart-count").textContent = String(totalQuantity()) + " 項";
    byId("cart-total").textContent = money(totalValue());
    byId("clear-cart").disabled = state.cart.length === 0;
    byId("build-candidate").disabled = state.cart.length === 0;
  }

  function invalidateCandidate(reason) {
    if (state.candidate || state.staffReviewed) {
      byId("action-result").textContent = "候選內容已變更，請重新建立並覆核。";
    }
    state.candidate = null;
    state.candidateCanonical = "";
    state.candidateHash = "";
    state.staffReviewed = false;
    renderPacket();
    updateActionAvailability();
    if (reason) {
      announce("已變更候選內容：" + reason);
    }
  }

  function addConfiguredLine(product, selections) {
    var rawSelections = selections.reduce(function (result, selection) {
      result[selection.questionId] = selection.optionId;
      return result;
    }, {});
    var normalized = RECTIFIER.normalizeConfiguration(MENU_DATA, product.id, rawSelections);
    if (!normalized.ok) {
      byId("intent-status").textContent = "來源選項尚未通過共用驗證，不能加入候選單。";
      evaluateRedteam("CONFIG_NORMALIZE", "HOLD_" + normalized.code);
      return;
    }

    var existing = state.cart.find(function (line) {
      return line.key === normalized.lineKey;
    });
    if (existing) {
      existing.quantity += 1;
    } else {
      state.cart.push({
        key: normalized.lineKey,
        productId: normalized.product.id,
        quantity: 1,
        selections: normalized.selections,
        unitPrice: normalized.unitPrice
      });
    }
    invalidateCandidate("商品或選項已加入");
    renderCart();
    closeConfigurator();
    logEvent("PRODUCT_CONFIGURED:" + normalized.product.id);
    evaluateRedteam("PRODUCT_ADD");
    announce(normalized.product.name + " 已通過共用來源驗證並加入本機候選單。");
  }

  function selectProduct(id) {
    var product = productFor(id);
    if (!product) {
      return;
    }
    if (questionsForProduct(product).length) {
      openConfigurator(id, "human");
      logEvent("PRODUCT_CONFIG_OPEN:" + id);
      evaluateRedteam("PRODUCT_CONFIG_OPEN");
      return;
    }
    addConfiguredLine(product, []);
  }

  function chooseOption(questionId, optionId) {
    var product = productFor(state.configuringProductId);
    if (!product) {
      return;
    }
    var question = questionsForProduct(product).find(function (item) {
      return item.id === questionId;
    });
    if (!question || !optionFor(question, optionId)) {
      evaluateRedteam("OPTION_SELECTION", "HOLD_UNKNOWN_SOURCE_OPTION");
      return;
    }
    state.selections[questionId] = optionId;
    renderConfigurator();
    logEvent("SOURCE_OPTION_SELECTED:" + questionId);
    evaluateRedteam("OPTION_SELECTION");
  }

  function confirmConfiguration() {
    var product = productFor(state.configuringProductId);
    if (!product || !configurationComplete(product)) {
      byId("intent-status").textContent = "仍有必選項未完成，不能加入候選單。";
      evaluateRedteam("CONFIG_CONFIRM", "HOLD_REQUIRED_OPTION_MISSING");
      return;
    }
    addConfiguredLine(product, selectedConfiguration(product));
    byId("intent-status").textContent = "已由人員確認加入；AI 與自動規則均未送出正式訂單。";
  }

  function changeLine(key, direction) {
    var line = state.cart.find(function (item) { return item.key === key; });
    if (!line) {
      return;
    }
    line.quantity += direction === "increase" ? 1 : -1;
    if (line.quantity <= 0) {
      state.cart = state.cart.filter(function (item) { return item.key !== key; });
    }
    invalidateCandidate("品項數量已變更");
    renderCart();
    logEvent("CART_LINE_" + direction.toUpperCase());
    evaluateRedteam("CART_LINE_CHANGE");
  }

  function clearCart() {
    state.cart = [];
    invalidateCandidate("候選單已清除");
    renderCart();
    byId("action-result").textContent = "合成候選單已清除；沒有任何伺服器狀態被改變。";
    logEvent("CART_CLEARED");
    evaluateRedteam("CART_CLEAR");
  }

  function packetDefaults() {
    return {
      D1: "等待櫃檯候選",
      D2: state.offline ? "EDGE_OFFLINE_QUEUE" : "LINKED_DEMO",
      D3: "SYN-SHIFT-07 / counter",
      D4: "QUICKCLICK-M387676 · SHA256 18798f9fe998",
      D5: "不執行正式交易",
      D6: "L3 candidate reconstruction",
      D7: "來源代碼／付款／價格／權限漂移",
      D8: "HOLD · FORMAL POS RELEASE"
    };
  }

  function renderPacket() {
    var fields = state.candidate ? state.candidate.intent_fields : packetDefaults();
    Object.keys(fields).forEach(function (key) {
      byId("packet-" + key.toLowerCase()).textContent = fields[key];
    });

    if (!state.candidate) {
      byId("packet-state").textContent = "EMPTY";
      byId("candidate-hash").textContent = "尚未建立候選";
    } else if (state.staffReviewed) {
      byId("packet-state").textContent = "HUMAN_REVIEWED_DEMO · D8 HOLD";
      byId("candidate-hash").textContent = state.candidateHash || "裝置端雜湊計算中";
    } else {
      byId("packet-state").textContent = "L3 CANDIDATE · D8 HOLD";
      byId("candidate-hash").textContent = state.candidateHash || "裝置端雜湊計算中";
    }
  }

  function canonicalize(value) {
    if (Array.isArray(value)) {
      return value.map(canonicalize);
    }
    if (value && typeof value === "object") {
      return Object.keys(value).sort().reduce(function (result, key) {
        result[key] = canonicalize(value[key]);
        return result;
      }, {});
    }
    return value;
  }

  function canonicalJson(value) {
    return JSON.stringify(canonicalize(value));
  }

  function sha256(value) {
    if (!window.crypto || !window.crypto.subtle || !window.TextEncoder) {
      return Promise.reject(new Error("WEB_CRYPTO_UNAVAILABLE"));
    }
    return window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)).then(function (buffer) {
      return Array.from(new Uint8Array(buffer)).map(function (byte) {
        return byte.toString(16).padStart(2, "0");
      }).join("");
    });
  }

  function selectedValue(id) {
    return byId(id).value;
  }

  function createCandidate() {
    return {
      schema: "w7tp-pos-candidate-v2",
      profile: "CAFE_POS",
      synthetic_case: true,
      menu_source: MENU_SOURCE,
      input_surfaces: MENU_DATA.surfaces,
      total_field_rectifier: {
        surface: RECTIFIER.surface,
        state: RECTIFIER.state
      },
      intent_fields: {
        D1: "建立櫃檯訂單候選，交由店員人工覆核",
        D2: state.offline ? "EDGE_OFFLINE_QUEUE" : "LINKED_DEMO",
        D3: "SYN-SHIFT-07 / counter",
        D4: "QUICKCLICK-M387676 · 64 PRODUCTS · SHA256 18798f9fe998",
        D5: "只建立候選；不執行正式交易",
        D6: "L3 candidate reconstruction",
        D7: "來源代碼／付款／價格／權限／重複候選漂移",
        D8: "HOLD · FORMAL POS RELEASE"
      },
      context: {
        service_mode: selectedValue("service-mode")
      },
      cart: state.cart.map(function (line) {
        var product = productFor(line.productId);
        return {
          sku: line.productId,
          source_product_id: product.sourceProductId,
          source_ref: product.sourceRef,
          adi_ref: null,
          adi_state: MENU_DATA.adi.state,
          source_category: product.sourceCategory,
          quantity: line.quantity,
          modifiers: line.selections.map(function (selection) {
            return {
              question: selection.questionName,
              question_coordinate: selection.questionCoordinate,
              option: selection.optionName,
              option_coordinate: selection.optionCoordinate,
              price_delta: selection.priceDelta
            };
          }),
          unit_price_candidate: line.unitPrice
        };
      }),
      candidate_total: totalValue(),
      guardrails: {
        formal_pos_order: false,
        payment_capture: false,
        member_plaintext: false,
        db_write: false,
        server_llm: false,
        ai_auto_submit: false
      }
    };
  }

  function buildCandidate() {
    if (!state.cart.length) {
      byId("action-result").textContent = "請先加入至少一項有來源商品。";
      announce("尚未建立候選，候選單為空。");
      return;
    }

    state.candidate = createCandidate();
    state.candidateCanonical = canonicalJson(state.candidate);
    state.candidateHash = "";
    state.staffReviewed = false;
    renderPacket();
    updateActionAvailability();
    byId("action-result").textContent = "8D L3 候選已在裝置端建立；等待店員逐行覆核。";
    logEvent("CANDIDATE_BUILT_LOCAL");
    evaluateRedteam("CANDIDATE_BUILD");
    announce("8D 訂單候選已建立，正式訂單仍為零。");

    var source = state.candidateCanonical;
    sha256(source).then(function (hash) {
      if (state.candidateCanonical !== source) {
        return;
      }
      state.candidateHash = hash;
      renderPacket();
      updateActionAvailability();
      announce("候選內容 SHA-256 已在裝置端完成。");
    }).catch(function () {
      if (state.candidateCanonical !== source) {
        return;
      }
      state.candidateHash = "";
      byId("candidate-hash").textContent = "WEB_CRYPTO_UNAVAILABLE · 未偽造雜湊";
      byId("action-result").textContent = "瀏覽器無法提供 Web Crypto；候選保持 HOLD。";
      updateActionAvailability();
    });
  }

  function updateActionAvailability() {
    byId("staff-review").disabled = !state.candidate || !state.candidateHash;
    byId("queue-candidate").disabled = !state.candidate || !state.candidateHash || !state.staffReviewed;
    byId("confirm-redeem").disabled = !state.redeemPending;
  }

  function reviewCandidate() {
    if (!state.candidate || !state.candidateHash) {
      byId("action-result").textContent = "請先建立具內容雜湊的候選。";
      return;
    }
    state.staffReviewed = true;
    renderPacket();
    updateActionAvailability();
    byId("action-result").textContent = "HUMAN_REVIEWED_DEMO；D8 仍為 HOLD，不是正式訂單。";
    logEvent("STAFF_REVIEWED_DEMO");
    evaluateRedteam("STAFF_REVIEW");
    announce("店員已完成展示覆核，正式訂單仍為零。");
  }

  function queueCandidate() {
    if (!state.candidate || !state.candidateHash || !state.staffReviewed) {
      byId("action-result").textContent = "候選須先建立雜湊並完成人工覆核。";
      return;
    }
    var duplicate = state.queue.some(function (entry) { return entry.hash === state.candidateHash; });
    if (!duplicate) {
      state.queue.push({ hash: state.candidateHash, envelope: state.candidate });
    }
    byId("queue-count").textContent = String(state.queue.length) + " PACKETS";
    byId("packet-state").textContent = "QUEUED_DEMO · D8 HOLD";
    byId("action-result").textContent = duplicate
      ? "相同內容雜湊已存在；裝置端去重，未重複加入。"
      : "已加入合成班次佇列；不建立 Odoo／POS 訂單。";
    logEvent(duplicate ? "QUEUE_DUPLICATE_BLOCKED" : "CANDIDATE_QUEUED_LOCAL");
    evaluateRedteam("QUEUE_CANDIDATE");
    announce(byId("action-result").textContent);
  }

  function testPaymentBoundary() {
    byId("action-result").textContent = "HOLD_PAYMENT_CAPTURE_FORBIDDEN · 付款請求已被常駐紅隊阻擋。";
    logEvent("PAYMENT_CAPTURE_BLOCKED");
    evaluateRedteam("PAYMENT_BOUNDARY_TEST", "HOLD_PAYMENT_CAPTURE_FORBIDDEN");
    announce("付款邊界測試完成：未扣款、未建立正式訂單。");
  }

  function requestRedeem() {
    if (state.cupRemaining <= 0 || state.redeemPending) {
      return;
    }
    state.redeemPending = true;
    byId("cup-state").textContent = "PENDING HUMAN REVIEW";
    updateActionAvailability();
    logEvent("CUP_REDEEM_REQUESTED:SYN-CUP-014");
    evaluateRedteam("CUP_REDEEM_REQUEST");
    announce("已提出合成核銷候選，等待店員確認。");
  }

  function confirmRedeem() {
    if (!state.redeemPending) {
      return;
    }
    state.cupRemaining -= 1;
    state.redeemPending = false;
    byId("cup-remaining").textContent = String(state.cupRemaining);
    byId("cup-state").textContent = "HUMAN_CONFIRMED_DEMO";
    updateActionAvailability();
    logEvent("CUP_REDEEM_CONFIRMED_LOCAL");
    evaluateRedteam("CUP_REDEEM_CONFIRM");
    announce("展示杯數已在瀏覽器記憶體更新為 " + String(state.cupRemaining) + " 杯。");
  }

  function toggleOffline() {
    state.offline = !state.offline;
    invalidateCandidate("連線狀態已變更");
    byId("connection-state").textContent = state.offline ? "EDGE OFFLINE / LOCAL ONLY" : "TAIJI01 LINKED / DEMO";
    byId("total-field-state").textContent = state.offline ? "HOLD · EDGE CANDIDATE ONLY" : "HOLD · CANDIDATE ONLY";
    byId("toggle-offline").textContent = state.offline ? "恢復總場連線" : "模擬離線";
    byId("edge-step").className = state.offline ? "is-active" : "";
    byId("revalidate-step").className = state.offline ? "" : "is-complete";
    renderPacket();
    logEvent(state.offline ? "EDGE_OFFLINE_ENTERED" : "TAIJI01_REVALIDATE_REQUIRED");
    evaluateRedteam(state.offline ? "OFFLINE_ENTER" : "LINK_RESTORED");
    announce(state.offline ? "已進入離線展示，只能建立本機候選。" : "已恢復連線展示，候選必須重新建立與覆核。");
  }

  function parseIntent() {
    var textValue = byId("intent-input").value.trim();
    var result = AI_INTENT.resolve(textValue, MENU_DATA, RECTIFIER);
    if (result.status === "EMPTY_INTENT") {
      byId("intent-status").textContent = "請輸入商品、尺寸、溫度、甜度或口味；不會傳到伺服器。";
      return;
    }
    if (result.status === "AMBIGUOUS_PRODUCT") {
      byId("intent-status").textContent = "同名商品無法安全判斷：" + result.ambiguous.map(function (product) {
        return product.name + "（" + product.sourceCategory + "／" + product.id + "）";
      }).join("、") + "。請補上分類或商品代碼。";
      evaluateRedteam("INTENT_PARSE", "HOLD_AMBIGUOUS_PRODUCT");
      return;
    }
    if (result.status === "UNKNOWN_PRODUCT") {
      byId("intent-status").textContent = "找不到完全對應的來源商品；未建立任何候選。";
      evaluateRedteam("INTENT_PARSE", "HOLD_UNKNOWN_PRODUCT");
      return;
    }

    openConfigurator(result.productId, "intent");
    state.selections = result.selections;
    renderConfigurator();
    byId("intent-status").textContent = result.unresolved.length
      ? "已辨識 " + result.productName + "；請人工補選：" + result.unresolved.join("、") + "。"
      : "已辨識商品與所有必選項；請人工檢查後按「確認加入候選」。";
    logEvent("DEVICE_INTENT_PARSED:" + result.productId);
    evaluateRedteam("INTENT_PARSE");
    announce("AI 意圖檔已填入員工選項卡，尚未加入候選單。");
  }

  function selectWorkflow(name) {
    state.workflow = name;
    var workflow = WORKFLOWS[name];
    document.querySelectorAll("[data-workflow]").forEach(function (button) {
      button.setAttribute("aria-selected", String(button.dataset.workflow === name));
    });
    byId("workflow-overline").textContent = workflow.overline;
    byId("workflow-title").textContent = workflow.title;
    byId("workflow-description").textContent = workflow.description;
    var steps = byId("workflow-steps");
    steps.replaceChildren();
    workflow.steps.forEach(function (label) {
      var item = document.createElement("li");
      item.textContent = label;
      steps.appendChild(item);
    });
    logEvent("WORKFLOW_VIEW:" + name.toUpperCase());
    evaluateRedteam("WORKFLOW_VIEW");
  }

  function resetDemo() {
    state = initialState();
    byId("service-mode").value = "dine_in";
    byId("intent-input").value = "";
    byId("intent-status").textContent = "輸入範例：招牌咖啡 大杯 少冰 半糖。語句只留在本裝置。";
    byId("connection-state").textContent = "TAIJI01 LINKED / DEMO";
    byId("total-field-state").textContent = "HOLD · CANDIDATE ONLY";
    byId("toggle-offline").textContent = "模擬離線";
    byId("edge-step").className = "";
    byId("revalidate-step").className = "is-complete";
    byId("cup-remaining").textContent = "12";
    byId("cup-state").textContent = "ACTIVE DEMO";
    byId("queue-count").textContent = "0 PACKETS";
    byId("action-result").textContent = "等待操作";
    renderMenu();
    renderConfigurator();
    renderCart();
    renderPacket();
    renderEventLog();
    selectWorkflow("counter");
    announce("合成班次已重置；所有狀態只存在本頁記憶體。");
  }

  document.addEventListener("click", function (event) {
    var addButton = event.target.closest("[data-add-product]");
    var lineButton = event.target.closest("[data-line-action]");
    var categoryButton = event.target.closest("[data-category]");
    var workflowButton = event.target.closest("[data-workflow]");
    var optionButton = event.target.closest("[data-option-id]");

    if (addButton) {
      selectProduct(addButton.dataset.addProduct);
      return;
    }
    if (lineButton) {
      changeLine(lineButton.dataset.lineKey, lineButton.dataset.lineAction);
      return;
    }
    if (categoryButton) {
      state.category = categoryButton.dataset.category;
      renderMenu();
      logEvent("CATEGORY_VIEW:" + state.category.toUpperCase());
      evaluateRedteam("CATEGORY_VIEW");
      return;
    }
    if (workflowButton) {
      selectWorkflow(workflowButton.dataset.workflow);
      return;
    }
    if (optionButton) {
      chooseOption(optionButton.dataset.questionId, optionButton.dataset.optionId);
    }
  });

  byId("service-mode").addEventListener("change", function () {
    invalidateCandidate("服務方式已變更");
    logEvent("MODIFIER_CHANGED:SERVICE_MODE");
    evaluateRedteam("MODIFIER_CHANGE");
  });
  byId("parse-intent").addEventListener("click", parseIntent);
  byId("confirm-config").addEventListener("click", confirmConfiguration);
  byId("cancel-config").addEventListener("click", function () {
    closeConfigurator();
    byId("intent-status").textContent = "已取消商品設定，候選單沒有改變。";
    evaluateRedteam("CONFIG_CANCEL");
  });
  byId("clear-cart").addEventListener("click", clearCart);
  byId("build-candidate").addEventListener("click", buildCandidate);
  byId("staff-review").addEventListener("click", reviewCandidate);
  byId("queue-candidate").addEventListener("click", queueCandidate);
  byId("test-payment-boundary").addEventListener("click", testPaymentBoundary);
  byId("request-redeem").addEventListener("click", requestRedeem);
  byId("confirm-redeem").addEventListener("click", confirmRedeem);
  byId("toggle-offline").addEventListener("click", toggleOffline);
  byId("reset-demo").addEventListener("click", resetDemo);

  renderMenu();
  renderConfigurator();
  renderCart();
  renderPacket();
  renderEventLog();
  updateActionAvailability();
  byId("revalidate-step").className = "is-complete";
}());
