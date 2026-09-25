(function () {
  "use strict";

  const roleData = {
    doctor: {
      tabId: "role-doctor",
      overline: "PHYSICIAN REVIEW",
      title: "醫師覆核佇列",
      evidenceCount: "4 個",
      reviewCount: "2 項",
      exposure: "最小化",
      focus: "專業術語、醫囑版本、來源證據與尚未釐清的不確定性並列呈現。",
      next: "覆核候選、修正摘要或明確否決；系統不能代簽診斷、處方或醫囑。",
      boundary: "AI 不得把摘要升級成正式病歷，也不能讓角色名稱或管理權限取代醫療身分驗證。",
      professional: "「依已簽署照護計畫 v3 執行，任何變更需由有權醫療人員確認。」",
      plain: "「你看到的提醒都來自醫療團隊已確認的版本；系統不會自己改變醫囑。」"
    },
    nurse: {
      tabId: "role-nurse",
      overline: "NURSING HANDOFF",
      title: "護理交班與待辦",
      evidenceCount: "3 個",
      reviewCount: "3 項",
      exposure: "工作所需",
      focus: "只顯示本班需要完成的聯絡、理解確認與待醫師覆核項目，保留來源與時序。",
      next: "依機構流程完成人工分級與聯絡紀錄；遇到不確定或超出權限時升級，不讓 AI 自行決定。",
      boundary: "交班摘要不能取代原始護理紀錄，也不能把病人自述自動升級成診斷或處置命令。",
      professional: "「症狀自述與居家量測為病人提供資料，需依院方流程分級並保留聯絡結果。」",
      plain: "「護理人員會依照醫療團隊的流程確認你的回報；請不要因本頁內容自行改變照護。」"
    },
    patient: {
      tabId: "role-patient",
      overline: "PATIENT CARE JOURNEY",
      title: "我的照護旅程",
      evidenceCount: "2 個",
      reviewCount: "1 項",
      exposure: "本人已授權",
      focus: "以白話呈現已簽署醫囑的來源、下一個提醒與尚待醫療人員回答的問題，不隱藏不確定性。",
      next: "確認自己是否理解、記錄實際狀態並準備問題；不依 AI 候選自行改藥或取代就醫。",
      boundary: "病人登入不等於取得所有病歷；代理人也不能只靠姓名或關係字串取得存取權。",
      professional: "「所有病人端解釋均須綁定原始醫囑版本、provenance 與醫療人員確認狀態。」",
      plain: "「你可以看到這段說明來自哪一份醫囑，也可以標記不懂；正式內容仍由醫療團隊確認。」"
    }
  };

  const eventData = {
    plan: {
      title: "出院照護計畫 v3 已簽署",
      summary: "這是後續提醒與交班唯一可引用的醫囑版本；AI 只能解釋與對齊來源，不能新增、刪除或改寫內容。",
      d1: "依正式照護計畫提供一致提醒",
      d3: "SYN-CARE-014 / plan",
      d4: "signed-care-plan:v3",
      d5: "呈現來源，不改內容",
      d7: "過期版本／角色越權",
      redteam: "若引用的醫囑不是最新簽署版本，阻擋提醒並要求人工核對。"
    },
    teachback: {
      title: "病人回述有一項待澄清",
      summary: "系統只標記病人理解與已簽署內容可能不一致，保留原話與來源；不自動改寫醫囑，也不假裝病人已完全理解。",
      d1: "找出需要醫療人員澄清的理解差異",
      d3: "SYN-CARE-014 / teachback",
      d4: "patient-teachback:synthetic-02",
      d5: "建立澄清候選，不改醫囑",
      d7: "白話層改變醫療原意",
      redteam: "若白話解釋刪除限制條件或誇大確定性，立即標記語義漂移並停止發布。"
    },
    signal: {
      title: "病人回報一項新的居家狀態",
      summary: "合成病人描述起身時短暫不適並記錄居家量測。系統對齊時間與照護計畫，只提出待人工分級候選，不判定病因。",
      d1: "把新狀態交給正確角色人工分級",
      d3: "SYN-CARE-014 / home-signal",
      d4: "patient-report:synthetic-03",
      d5: "對齊時序並請護理人工分級",
      d7: "漏警／誤警／把自述當診斷",
      redteam: "若模型把病人自述寫成診斷、處方或緊急分流結論，候選立即隔離。"
    },
    handoff: {
      title: "護理交班候選等待醫師覆核",
      summary: "交班候選只列來源、尚未完成事項、人工分級結果與待覆核問題；在醫師確認前，病人端不會看到新的正式醫囑。",
      d1: "跨班別維持未完成事項與責任連續",
      d3: "SYN-CARE-014 / handoff",
      d4: "nursing-handoff:synthetic-04",
      d5: "移交候選與責任，不形成醫療決策",
      d7: "交班遺漏／責任不明／提早發布",
      redteam: "若交班缺少來源、負責角色或待辦狀態，總場保持 HOLD 並阻擋成為正式封套。"
    }
  };

  const byId = (id) => document.getElementById(id);
  const tabs = Array.from(document.querySelectorAll("[role='tab'][data-role]"));
  const eventButtons = Array.from(document.querySelectorAll(".event-button[data-event]"));
  const perspectiveLinks = Array.from(document.querySelectorAll("[data-perspective-role]"));
  const offlineButton = byId("simulate-offline");
  const restoreButton = byId("restore-link");
  const connectionState = byId("connection-state");
  const packetState = byId("packet-state");
  const announcement = byId("demo-announcement");
  let currentRole = "patient";
  let currentEvent = "plan";
  let offline = false;
  const redteamMonitor = byId("care-redteam-monitor");
  let redteamCycle = 0;

  function setText(id, value) {
    const node = byId(id);
    if (node) node.textContent = value;
  }

  function evaluateRedteam(trigger) {
    const event = eventData[currentEvent];
    if (!event || !redteamMonitor) return;
    redteamCycle += 1;
    redteamMonitor.dataset.state = "MONITORING_CLEAR";
    setText("care-redteam-state", "MONITORING CLEAR");
    setText("redteam-message", event.redteam);
    setText("care-redteam-cycle", `cycle ${redteamCycle} · ${trigger}`);
  }

  function renderRole(roleName) {
    const role = roleData[roleName];
    if (!role) return;
    currentRole = roleName;
    tabs.forEach((tab) => {
      const selected = tab.dataset.role === roleName;
      tab.setAttribute("aria-selected", String(selected));
      tab.setAttribute("tabindex", selected ? "0" : "-1");
    });
    const panel = byId("role-panel");
    panel.setAttribute("aria-labelledby", role.tabId);
    setText("role-overline", role.overline);
    setText("role-title", role.title);
    setText("role-evidence-count", role.evidenceCount);
    setText("role-review-count", role.reviewCount);
    setText("role-exposure", role.exposure);
    setText("role-focus", role.focus);
    setText("role-next", role.next);
    setText("role-boundary", role.boundary);
    setText("professional-source", role.professional);
    setText("plain-language", role.plain);
    announcement.textContent = `已切換為${role.title}；事件內容身分保持不變。`;
    evaluateRedteam("ROLE_TRANSITION");
  }

  async function renderHash(eventName) {
    const canonicalDemoString = `w7tp-demo/v1|SYN-CARE-014|${eventName}|L3|synthetic-only`;
    if (!window.crypto || !window.crypto.subtle) {
      setText("content-hash", "安全瀏覽環境未提供 Web Crypto；未偽造雜湊");
      return;
    }
    const bytes = new TextEncoder().encode(canonicalDemoString);
    const digest = await window.crypto.subtle.digest("SHA-256", bytes);
    const rendered = Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, "0")).join("");
    if (currentEvent === eventName) setText("content-hash", rendered);
  }

  function renderEvent(eventName) {
    const event = eventData[eventName];
    if (!event) return;
    currentEvent = eventName;
    eventButtons.forEach((button) => {
      const selected = button.dataset.event === eventName;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    setText("event-title", event.title);
    setText("event-summary", event.summary);
    setText("packet-d1", event.d1);
    setText("packet-d2", offline ? "EDGE_OFFLINE_QUEUE" : "LINKED_DEMO");
    setText("packet-d3", event.d3);
    setText("packet-d4", event.d4);
    setText("packet-d5", event.d5);
    setText("packet-d6", "L3 candidate reconstruction");
    setText("packet-d7", event.d7);
    setText("packet-d8", "HOLD · 未形成正式裁決");
    evaluateRedteam("EVENT_TRANSITION");
    setText("content-hash", "計算中…");
    void renderHash(eventName);
    announcement.textContent = `已選取合成事件：${event.title}。`;
  }

  function setOfflineState(value) {
    offline = value;
    connectionState.classList.toggle("is-offline", value);
    setText("connection-state", value ? "EDGE OFFLINE / L3 QUEUED" : "TAIJI01 LINKED / REVALIDATED");
    setText("packet-d2", value ? "EDGE_OFFLINE_QUEUE" : "LINKED_DEMO");
    setText("packet-state", value ? "QUEUED · NO D8" : "HOLD · HUMAN REVIEW");
    offlineButton.disabled = value;
    restoreButton.disabled = !value;
    byId("queue-step").classList.toggle("is-active", value);
    byId("queue-step").classList.toggle("is-complete", !value && byId("revalidate-step").classList.contains("is-complete"));
    if (value) {
      byId("revalidate-step").classList.remove("is-complete");
      setText("queue-label", "L3 候選已排入（互動模擬）");
      setText("revalidate-label", "等待主節點回線");
      announcement.textContent = "已模擬離線：候選只排隊，不形成正式 D8。";
    } else {
      byId("revalidate-step").classList.add("is-complete");
      setText("queue-label", "hash 鏈完整");
      setText("revalidate-label", "已示意重驗與去重");
      announcement.textContent = "已恢復連線：候選完成重驗與去重示意，仍等待人類覆核。";
    }
    evaluateRedteam(value ? "OFFLINE_QUEUE" : "RELINK_REVALIDATION");
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => renderRole(tab.dataset.role));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      tabs[nextIndex].focus();
      renderRole(tabs[nextIndex].dataset.role);
    });
  });

  eventButtons.forEach((button) => button.addEventListener("click", () => renderEvent(button.dataset.event)));
  perspectiveLinks.forEach((link) => link.addEventListener("click", () => renderRole(link.dataset.perspectiveRole)));
  offlineButton.addEventListener("click", () => setOfflineState(true));
  restoreButton.addEventListener("click", () => setOfflineState(false));

  renderRole(currentRole);
  renderEvent(currentEvent);
}());
