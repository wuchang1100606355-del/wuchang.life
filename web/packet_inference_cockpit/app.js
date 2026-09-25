const demos = [
  ["飲品推薦", "我今天有點累，想喝不太苦的，幫我推薦"],
  ["會員註冊", "我要註冊會員，幫我直接完成第一步"],
  ["預約下單", "幫我預約今晚 7 點，兩位，少冰無糖"],
  ["客服抱怨", "我下單有問題，流程中卡住了怎麼辦"],
  ["付款請求", "幫我直接結帳付款"],
  ["會員明文", "我要查會員完整電話和地址"],
  ["過敏風險", "我對牛奶有點敏感，想喝順口的"],
  ["未知輸入", "qqq xyz 未知請求"],
  ["身分上下文", "你沒有我的資訊嗎"],
  ["會員上下文", "你知道我的會員資料嗎"],
  ["創辦人聲明", "我是創辦人江政隆你認識我嗎"],
  ["角色查詢", "我的角色是什麼"]
];

const scenarioDeckCards = [
  {
    key: "member_registration",
    title: "會員註冊",
    tag: "首次接觸用",
    prompt: "我要註冊會員，先幫我整理第一步。",
    tone: "文學與規則並行"
  },
  {
    key: "order_or_booking",
    title: "訂位與下單",
    tag: "高頻場景",
    prompt: "幫我今晚七點去店裡預約兩位，少冰無糖。",
    tone: "溫柔清楚"
  },
  {
    key: "support_complaint",
    title: "客服抱怨",
    tag: "修復導向",
    prompt: "我剛下單卡住，請幫我整理成可追蹤回報。",
    tone: "穩定陪伴"
  },
  {
    key: "member_value",
    title: "會員價值",
    tag: "策略化",
    prompt: "請分析我現在這個會員狀態可以拿到哪些附加價值。",
    tone: "創作式建議"
  },
];

const d8Labels = [
  ["D1_intent", "D1 Intent"],
  ["D2_state", "D2 State"],
  ["D3_coordinate", "D3 Coordinate"],
  ["D4_evidence", "D4 Evidence"],
  ["D5_execution", "D5 Execution"],
  ["D6_gt", "D6 Generative Transmission"],
  ["D7_risk", "D7 Risk"],
  ["D8_envelope", "D8 Envelope"]
];

let activePacket = null;
let activeReplyVariants = {};
let activeReplyVariant = "default";
let lastCloudModelPacket = null;
let lastCockpitResult = null;
let lastChatInputText = "";
const PROFILE_STORAGE_KEY = "w7tp_packet_inference_cockpit_profile_v1";
const TONE_VARIANT_MAP = {
  natural: "default",
  concise: "concise",
  poetic: "poetic",
};
const VARIANT_LABELS = {
  default: "自然",
  concise: "簡潔",
  poetic: "文學"
};

function el(id) {
  return document.getElementById(id);
}

function badgeClass(decision) {
  if (decision === "ALLOW") return "decision allow";
  if (decision === "HOLD") return "decision hold";
  if (decision === "BLOCK") return "decision block";
  if (decision === "CONTINUE") return "decision continue";
  return "decision";
}

function statusText(value) {
  return String(value || "").replace(/_/g, " ");
}

function renderJson(node, data) {
  node.textContent = JSON.stringify(data || {}, null, 2);
}

function renderSafety(flags) {
  const box = el("safetyFlags");
  box.innerHTML = "";
  Object.entries(flags || {}).forEach(([key, value]) => {
    const item = document.createElement("div");
    item.className = value ? "flag bad" : "flag good";
    item.textContent = `${key}=${value}`;
    box.appendChild(item);
  });
}

function readProfile() {
  try {
    const raw = window.localStorage ? window.localStorage.getItem(PROFILE_STORAGE_KEY) : null;
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function saveProfile(profile) {
  try {
    if (!window.localStorage) {
      return;
    }
    const payload = {
      ai_key_ref: String(profile.ai_key_ref || ""),
      ai_key_source: profile.ai_key_source || "select",
      cloud_translator_profile: profile.cloud_translator_profile || "raw",
      response_tone_profile: profile.response_tone_profile || "natural",
      branch: String(profile.branch || ""),
      actor_role: String(profile.actor_role || ""),
      channel: String(profile.channel || ""),
      updated_at: new Date().toISOString(),
    };
    window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    return;
  }
}

function applySavedProfile() {
  const profile = readProfile();
  if (!profile || typeof profile !== "object") {
    return;
  }

  const translator = document.getElementById("cloudTranslatorProfile");
  if (translator && profile.cloud_translator_profile) {
    translator.value = profile.cloud_translator_profile;
  }

  const responseTone = document.getElementById("responseTone");
  if (responseTone && profile.response_tone_profile) {
    responseTone.value = profile.response_tone_profile;
  }

  const aiKeyCustom = document.getElementById("aiKeyCustom");
  const aiKeyRef = document.getElementById("aiKeyRef");
  if (profile.ai_key_ref) {
    const raw = String(profile.ai_key_ref).trim();
    if (raw) {
      const matched = Array.from(aiKeyRef?.options || []).find((item) => item.value === raw);
      if (matched && matched instanceof HTMLOptionElement) {
        aiKeyRef.value = raw;
        if (aiKeyCustom) {
          aiKeyCustom.value = "";
        }
      } else if (aiKeyCustom) {
        aiKeyCustom.value = raw;
      }
    }
  }

  const branch = document.getElementById("branch");
  const actorRole = document.getElementById("actorRole");
  const channel = document.getElementById("channel");
  if (branch && profile.branch) {
    branch.value = String(profile.branch);
  }
  if (actorRole && profile.actor_role) {
    actorRole.value = String(profile.actor_role);
  }
  if (channel && profile.channel) {
    channel.value = String(profile.channel);
  }
}

function resolveAiKeyRef() {
  const custom = String((document.getElementById("aiKeyCustom")?.value || "").trim());
  const selected = String((document.getElementById("aiKeyRef")?.value || "").trim());
  if (custom) {
    return custom;
  }
  return selected;
}

function aiKeySource(selectedValue, customValue) {
  if (String(customValue || "").trim()) {
    return "custom";
  }
  if (String(selectedValue || "").trim()) {
    return "select";
  }
  return "unset";
}

function _clampToneProfile(value) {
  if (value === "concise" || value === "poetic") {
    return value;
  }
  return "natural";
}

function _toneVariantForProfile(value) {
  return TONE_VARIANT_MAP[_clampToneProfile(value)] || "default";
}

function _toneProfileLabel(value) {
  if (value === "poetic") {
    return "文學陪伴";
  }
  if (value === "concise") {
    return "簡潔陪伴";
  }
  return "自然陪伴";
}

function renderMediaResponse(mediaRoot, mediaResponse) {
  if (!mediaRoot) {
    return;
  }
  const response = mediaResponse && typeof mediaResponse === "object" ? mediaResponse : {};
  const mode = String(response.mode || "TEXT_ONLY");
  const voiceHint = String(response.voice_hint || "");
  const videoMode = String(response.video_mode || "NONE");
  const videoHint = String(response.video_hint || "");
  const audioScript = String(response.audio_script || "");

  mediaRoot.innerHTML = "";
  const modeRow = document.createElement("div");
  modeRow.className = "media-hint";
  modeRow.textContent = `媒體模式：${mode}`;
  mediaRoot.appendChild(modeRow);

  if (voiceHint) {
    const voiceRow = document.createElement("div");
    voiceRow.className = "media-hint";
    voiceRow.textContent = `語音風格：${voiceHint}`;
    mediaRoot.appendChild(voiceRow);
  }

  if (audioScript) {
    const toolbar = document.createElement("div");
    toolbar.className = "media-toolbar";

    const playButton = document.createElement("button");
    playButton.type = "button";
    playButton.textContent = "播放語音回覆";
    toolbar.appendChild(playButton);

    const stopButton = document.createElement("button");
    stopButton.type = "button";
    stopButton.textContent = "停止語音";
    toolbar.appendChild(stopButton);

    const status = document.createElement("div");
    status.className = "media-hint";
    status.textContent = window.speechSynthesis ? "瀏覽器已支援語音播放" : "此環境不支援語音播放";
    mediaRoot.appendChild(toolbar);
    mediaRoot.appendChild(status);

    const stopSpeech = () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      status.textContent = "已停止朗讀";
    };

    playButton.addEventListener("click", () => {
      if (!window.speechSynthesis) {
        status.textContent = "本瀏覽器未支援語音播放";
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(audioScript);
      utterance.lang = "zh-TW";
      utterance.rate = 1;
      utterance.pitch = 1;
      status.textContent = "播放中...";
      utterance.onend = () => {
        status.textContent = "播報完成";
      };
      utterance.onerror = () => {
        status.textContent = "語音播放失敗";
      };
      window.speechSynthesis.speak(utterance);
    });
    stopButton.addEventListener("click", stopSpeech);
  }

  if (videoMode && videoMode !== "NONE") {
    const videoHintRow = document.createElement("div");
    videoHintRow.className = "media-hint";
    videoHintRow.textContent = `影音構想：${videoHint || "視覺化提示已鎖定"}`;
    mediaRoot.appendChild(videoHintRow);
  }

  if (!audioScript && videoMode === "NONE") {
    const noneRow = document.createElement("div");
    noneRow.className = "media-hint";
    noneRow.textContent = "暫無影音素材，僅保留文字回覆。";
    mediaRoot.appendChild(noneRow);
  }
}

function renderActionPack(actionPack) {
  const checklistRoot = el("actionChecklist");
  const copyHintRoot = el("actionCopyHint");
  const actionMode = actionPack && typeof actionPack === "object" ? actionPack : {};

  if (checklistRoot) {
    checklistRoot.innerHTML = "";
    const mode = String(actionMode.mode || "未定義草稿");
    const header = document.createElement("div");
    header.className = "action-mode";
    header.textContent = `草稿模式：${mode}`;
    checklistRoot.appendChild(header);

    const required = Array.isArray(actionMode.required_fields) ? actionMode.required_fields : [];
    const optional = Array.isArray(actionMode.optional_fields) ? actionMode.optional_fields : [];
    const checks = Array.isArray(actionMode.verification_checks) ? actionMode.verification_checks : [];
    const extraRows = [
      ["goal", "目標", actionMode.goal || ""],
      ["human_confirmation", "確認語", actionMode.human_confirmation || ""],
      ["candidate_note", "候選註記", actionMode.candidate_note || ""],
    ].filter((row) => row[2]);

    const renderSection = (title, items) => {
      if (!items.length) {
        return;
      }
      const section = document.createElement("div");
      section.className = "action-section";
      const sectionTitle = document.createElement("div");
      sectionTitle.className = "action-section-title";
      sectionTitle.textContent = title;
      section.appendChild(sectionTitle);
      const list = document.createElement("ul");
      items.forEach((item) => {
        const li = document.createElement("li");
        const label = document.createElement("label");
        label.className = "action-item";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        const span = document.createElement("span");
        span.textContent = String(item);
        label.appendChild(checkbox);
        label.appendChild(span);
        li.appendChild(label);
        list.appendChild(li);
      });
      section.appendChild(list);
      checklistRoot.appendChild(section);
    };

    renderSection("必填欄位", required);
    renderSection("可選欄位", optional);
    renderSection("保全檢核", checks);

    extraRows.forEach(([_, title, value]) => {
      const row = document.createElement("div");
      row.className = "action-extra-row";
      row.textContent = `${title}：${value}`;
      checklistRoot.appendChild(row);
    });
  }

  if (copyHintRoot) {
    const composeText = [];
    composeText.push(`草稿模式：${String(actionMode.mode || "未定義草稿")}`);
    if (actionMode.goal) {
      composeText.push(`目標：${actionMode.goal}`);
    }
    if (Array.isArray(actionMode.required_fields) && actionMode.required_fields.length) {
      composeText.push(`必填：${actionMode.required_fields.join("，")}`);
    }
    if (Array.isArray(actionMode.optional_fields) && actionMode.optional_fields.length) {
      composeText.push(`可選：${actionMode.optional_fields.join("，")}`);
    }
    if (Array.isArray(actionMode.verification_checks) && actionMode.verification_checks.length) {
      composeText.push(`檢核：${actionMode.verification_checks.join("，")}`);
    }
    if (actionMode.human_confirmation) {
      composeText.push(`請求確認：${actionMode.human_confirmation}`);
    }

    const textNode = document.createElement("div");
    textNode.className = "media-hint";
    textNode.textContent = composeText.join("；");

    const statusNode = document.createElement("span");
    statusNode.className = "media-hint action-fill-status";
    statusNode.textContent = "";

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "action-fill-btn";
    copyBtn.textContent = "複製草稿摘要";
    copyBtn.addEventListener("click", async () => {
      const text = composeText.join("\n");
      try {
        await navigator.clipboard.writeText(text);
        textNode.textContent = `${text}\n\n已複製到剪貼簿`;
      } catch {
        textNode.textContent = `${text}\n\n無法直接複製，請手動複製。`;
      }
    });

    const fillBtn = document.createElement("button");
    fillBtn.type = "button";
    fillBtn.className = "action-fill-btn action-fill-input-btn";
    fillBtn.textContent = "回填到輸入框";
    fillBtn.addEventListener("click", () => {
      const input = el("inputText");
      if (!input) {
        return;
      }
      const filled = composeText.join("\n");
      input.value = filled;
      input.focus();
      statusNode.textContent = `已回填：${filled.slice(0, 180)}${filled.length > 180 ? "…" : ""}`;
    });
    copyHintRoot.innerHTML = "";
    copyHintRoot.appendChild(textNode);
    copyHintRoot.appendChild(document.createElement("br"));
    copyHintRoot.appendChild(copyBtn);
    copyHintRoot.appendChild(fillBtn);
    copyHintRoot.appendChild(statusNode);
  }
}

function renderLiteraryCard(root, humanResponse, decision) {
  if (!root) {
    return;
  }
  const aesthetic = humanResponse && typeof humanResponse === "object" ? humanResponse.aesthetic : {};
  const tone = String(aesthetic.tone || (decision === "PASS" ? "溫和可執行" : "穩定保全"));
  const scene = String(aesthetic.scene || "");
  const headline = String(aesthetic.headline || "總場回應");
  const poem = String(aesthetic.poetic_line || "");
  const poem2 = String(aesthetic.poem_line_2 || "");
  const nextAction = String(aesthetic.next_action_hint || "");

  root.innerHTML = "";
  const lines = [
    `標題：${headline}`,
    `語氣：${tone}`,
    scene ? `場景：${scene}` : "",
    poem ? `詩句：${poem}` : "",
    poem2 ? `收束：${poem2}` : "",
    nextAction ? `下一步：${nextAction}` : "",
  ].filter(Boolean);
  lines.forEach((line) => {
    const item = document.createElement("div");
    item.className = "media-hint";
    item.textContent = line;
    root.appendChild(item);
  });
  if (!lines.length) {
    root.textContent = "尚未有文學化輸出。";
  }
}

function renderValueLayer(root, valueLayer) {
  const source = valueLayer && typeof valueLayer === "object" ? valueLayer : {};
  const mode = String(source.mode || "候選體驗");
  const highlights = Array.isArray(source.highlights) ? source.highlights : [];
  const highlighted = Array.isArray(source.highlighted_values) ? source.highlighted_values : [];
  const nextReadiness = Array.isArray(source.next_readiness) ? source.next_readiness : [];
  const advantage = String(source.member_advantage || source.value_advantage || "");
  const edge = String(source.competitive_edge || "");

  const renderList = (items) => {
    if (!items.length) {
      return "";
    }
    return `<ul class="value-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  };

  root.innerHTML = `
    <div class="value-block">
      <div class="media-hint">會員價值模式：${escapeHtml(mode)}</div>
      ${highlights.length || highlighted.length ? `<div class="media-hint">亮點</div>${renderList(highlights.length ? highlights : highlighted)}` : ""}
      ${advantage ? `<div class="media-hint">你可得的關鍵價值：${escapeHtml(advantage)}</div>` : ""}
      ${edge ? `<div class="media-hint">競爭亮點：${escapeHtml(edge)}</div>` : ""}
      ${nextReadiness.length ? `<div class="media-hint">下一步可行性</div>${renderList(nextReadiness)}` : ""}
    </div>
  `;
}

function renderReplyVariants(root, variants, preferredVariant = "default") {
  if (!root) {
    return;
  }
  const data = variants && typeof variants === "object" ? variants : {};
  const controls = el("replyVariantControls");
  const keys = Object.keys(data).filter((key) => typeof data[key] === "string" && data[key].trim());

  root.innerHTML = "";
  if (controls) {
    controls.innerHTML = "";
  }
  if (!keys.length) {
    root.textContent = "尚未產生版本。";
    if (controls) {
      controls.innerHTML = "";
    }
    activeReplyVariants = {};
    activeReplyVariant = "default";
    return;
  }

  activeReplyVariants = data;
  activeReplyVariant = keys.includes(preferredVariant) ? preferredVariant : (keys.includes("default") ? "default" : keys[0]);

  keys.forEach((key) => {
    const value = String(data[key] || "");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "reply-variant-btn";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", key === activeReplyVariant ? "true" : "false");
    button.textContent = VARIANT_LABELS[key] || key;
    button.addEventListener("click", () => {
      const selected = String(button.dataset.variant || key);
      const text = String(data[selected] || "");
      if (!text) {
        return;
      }
      activeReplyVariant = selected;
      if (controls) {
        [...controls.querySelectorAll(".reply-variant-btn")].forEach((btn) => {
          const isActive = btn.dataset.variant === selected;
          btn.classList.toggle("active", isActive);
          btn.setAttribute("aria-selected", isActive ? "true" : "false");
        });
      }
      el("answerText").textContent = text;
    });
    button.dataset.variant = key;
    if (key === activeReplyVariant) {
      button.classList.add("active");
    }
    if (controls) {
      controls.appendChild(button);
    }

    const row = document.createElement("div");
    row.className = "reply-variant";
    if (key === activeReplyVariant) {
      row.classList.add("active");
    }
    row.dataset.variant = key;
    row.textContent = `${key.toUpperCase()}: ${value}`;
    root.appendChild(row);
  });

  const first = String(activeReplyVariants[activeReplyVariant] || "");
  if (first) {
    el("answerText").textContent = first;
  } else if (keys[0] in data && String(data[keys[0]] || "").trim()) {
    activeReplyVariant = keys[0];
    el("answerText").textContent = String(data[keys[0]]);
  }

  if (root.childElementCount === 0) {
    root.textContent = "尚未產生版本。";
    if (controls) {
      controls.innerHTML = "";
    }
  }
}

function renderSuggestionChips(actionPack) {
  const root = el("suggestionChips");
  if (!root) {
    return;
  }
  const required = Array.isArray(actionPack?.required_fields) ? actionPack.required_fields : [];
  const checks = Array.isArray(actionPack?.verification_checks) ? actionPack.verification_checks : [];
  const values = [...new Set([...required, ...checks])].slice(0, 4);

  root.innerHTML = "";
  if (!values.length) {
    const empty = document.createElement("div");
    empty.className = "media-hint";
    empty.textContent = "目前暫無可直接補齊的欄位建議。";
    root.appendChild(empty);
    return;
  }

  values.forEach((value) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "suggestion-chip";
    chip.textContent = `補齊：${value}`;
    chip.addEventListener("click", () => {
      const input = el("inputText");
      if (!input) {
        return;
      }
      input.value = `${String(input.value || "").trim()}${String(input.value || "").trim() ? "，" : ""}${value}：`;
      input.focus();
    });
    root.appendChild(chip);
  });
}

function inferScenarioKey(actionPack, humanResponse, decision) {
  const explicitScenario = String(
    humanResponse?.solution_scenarios?.key || humanResponse?.scenario || humanResponse?.solution_context || ""
  ).trim();
  if (explicitScenario && SOLUTION_SCENARIO_TEMPLATES[explicitScenario]) {
    return explicitScenario;
  }

  const sourcePack = actionPack && typeof actionPack === "object" ? actionPack : {};
  const mode = String(sourcePack.mode || "").toLowerCase();
  const goal = String(sourcePack.goal || "").toLowerCase();
  const rawChecks = JSON.stringify(sourcePack).toLowerCase();
  const reply = String(humanResponse?.reply_text || "").toLowerCase();

  const hasAny = (keywords) => keywords.some((keyword) => rawChecks.includes(keyword) || reply.includes(keyword) || mode.includes(keyword) || goal.includes(keyword));

  if (hasAny(["註冊", "member", "phone", "手機", "同意", "條款", "姓名"])) {
    return "member_registration";
  }
  if (hasAny(["預約", "訂單", "外送", "到店", "到店", "時間", "數量", "品項"])) {
    return "order_or_booking";
  }
  if (hasAny(["抱怨", "問題", "卡住", "失敗", "退款", "錯誤", "異常", "重現"])) {
    return "support_complaint";
  }
  if (decision === "HOLD") {
    return "risk_governance";
  }
  return "general";
}

const SOLUTION_SCENARIO_TEMPLATES = {
  member_registration: 1,
  order_or_booking: 1,
  support_complaint: 1,
  risk_governance: 1,
  general: 1,
};

const PRODUCT_CAPABILITY = {
  member_registration: {
    solve: [
      "整理成可核對的註冊最小欄位清單",
      "抽出隱私同意與權益提示",
      "保留可延續到會員下單與到店流程的上下文",
    ],
    protect: [
      "不會直接建立會員資料",
      "不會直接讀取完整會員明文",
      "不會代你完成正式送件",
    ],
  },
  order_or_booking: {
    solve: [
      "整理時間、人數、品項、口味與配送偏好",
      "幫你輸出可核對候選路徑",
      "標注缺少的必要欄位，避免回頭重填",
    ],
    protect: [
      "不會直接幫你下單/付款",
      "不會調整實際庫存",
      "不會發起外部未授權交易",
    ],
  },
  support_complaint: {
    solve: [
      "把問題轉成可回放的重現路徑",
      "補齊時間、裝置、步驟欄位",
      "先整理可交付客服的問題草稿",
    ],
    protect: [
      "不會私下修改訂單狀態",
      "不會替你跳過權限流程",
      "不會主動對外公告客服判定結果",
    ],
  },
  member_value: {
    solve: [
      "把你的使用情境轉成可執行會員價值草稿",
      "標出可量化價值目標與留存切入點",
      "輸出能交接給團隊的行動建議",
    ],
    protect: [
      "不會代你做個資價值推測買賣",
      "不會自動綁定新權益方案",
      "不會直接改動商務條款",
    ],
  },
  risk_governance: {
    solve: [
      "先保全越權邊界，明確標出高風險操作",
      "保留候選內容供人工確認",
      "給出下一步可補齊欄位",
    ],
    protect: [
      "不會寫資料庫",
      "不會部署/重啟服務",
      "不會做正式付款或送件",
    ],
  },
  general: {
    solve: [
      "先把自然語言整理成可核對回覆",
      "同步提供可接續的候選草案",
      "給你可調整的文本情緒版本",
    ],
    protect: [
      "不會自稱總場權威",
      "不會把內部 D1-D8 機制透露給你",
      "不會執行高風險權限動作",
    ],
  },
};

function renderProductScope(rootSolved, rootNotCovered, scenario, decision) {
  if (!rootSolved || !rootNotCovered) {
    return;
  }
  const key = PRODUCT_CAPABILITY[scenario] ? scenario : "general";
  const profile = PRODUCT_CAPABILITY[key] || PRODUCT_CAPABILITY.general;

  const renderBlock = (title, values, color) => {
    const block = document.createElement("article");
    block.className = `extension-item ${color || ""}`;
    const list = Array.isArray(values) && values.length
      ? `<ul>${values.map((v) => `<li>${escapeHtml(v)}</li>`).join("")}</ul>`
      : "<div class='media-hint'>暫無明細</div>";
    block.innerHTML = `
      <h4>${escapeHtml(title)}${decision !== "PASS" && title === "你這次能直接解決" ? "（待確認）" : ""}</h4>
      ${list}
    `;
    return block;
  };

  rootSolved.innerHTML = "";
  rootNotCovered.innerHTML = "";
  const solved = renderBlock("你這次能直接解決", profile.solve, "");
  const limited = renderBlock("目前不會做", profile.protect, "");
  rootSolved.appendChild(solved);
  rootNotCovered.appendChild(limited);
}

function renderExperienceGuarantee(root, scenario, decision, humanResponse, actionPack) {
  if (!root) {
    return;
  }

  const key = PRODUCT_CAPABILITY[scenario] ? scenario : "general";
  const capability = PRODUCT_CAPABILITY[key] || PRODUCT_CAPABILITY.general;
  const library = CAPABILITY_LIBRARY[key] || CAPABILITY_LIBRARY.general;
  const actionMode = actionPack && typeof actionPack === "object" ? actionPack : {};
  const valueLayer = humanResponse?.value_layer && typeof humanResponse.value_layer === "object" ? humanResponse.value_layer : {};

  const immediate = Array.isArray(capability.solve) ? capability.solve : [];
  const guard = Array.isArray(capability.protect) ? capability.protect : [];
  const extendsList = Array.isArray(library.extensions) ? library.extensions : [];
  const requiredFields = Array.isArray(actionMode.required_fields) ? actionMode.required_fields : [];
  const optionalFields = Array.isArray(actionMode.optional_fields) ? actionMode.optional_fields : [];
  const readiness = Array.isArray(valueLayer.next_readiness) ? valueLayer.next_readiness : [];
  const highlights = Array.isArray(valueLayer.highlights) ? valueLayer.highlights : [];
  const advantage = String(valueLayer.member_advantage || valueLayer.competitive_edge || "可在候選核可後衍伸更完整商務場景。");
  const gateText = decision === "PASS" ? "候選先行，等待人工核可" : "保全優先，先補齊條件";

  const renderList = (items, fallback) => {
    if (!items.length) {
      return `<li>${escapeHtml(fallback)}</li>`;
    }
    return items.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("");
  };

  const readinessText = readiness.length
    ? renderList(readiness, "就緒條件可回填")
    : "<li>就緒度：待補齊核可條件</li>";

  const toFill = [...requiredFields, ...optionalFields].filter(Boolean).slice(0, 3);

  root.innerHTML = `
    <div class="experience-grid">
      <article class="extension-item">
        <h4>這次能直接解決</h4>
        <ul class="value-list">${renderList(immediate, "先整理可核對候選草稿。")}</ul>
      </article>
      <article class="extension-item">
        <h4>不會做的界線</h4>
        <ul class="value-list">${renderList(guard, "不會越界執行正式權限動作。")}</ul>
      </article>
      <article class="extension-item">
        <h4>可衍伸能力</h4>
        <ul class="value-list">${renderList(extendsList, "補齊條件後可展開更多場景。")}</ul>
      </article>
      <article class="extension-item">
        <h4>產品保證</h4>
        <div class="media-hint">決策：${escapeHtml(decision || "HOLD")}</div>
        <div class="media-hint">門禁：${escapeHtml(gateText)}</div>
        <div class="media-hint">亮點：${escapeHtml(highlights[0] || advantage)}</div>
      </article>
      <article class="extension-item">
        <h4>下一步建議項目</h4>
        <ul class="value-list">${renderList(toFill, "先補齊條件與核可線索。")}</ul>
      </article>
      <article class="extension-item">
        <h4>就緒度</h4>
        <ul class="value-list">${readinessText}</ul>
      </article>
    </div>
  `;
}

const CAPABILITY_LIBRARY = {
  member_registration: {
    solves: [
      "建立會員最小資料草稿",
      "整理同意與權益提示",
      "保留後續導向：預約/點餐",
    ],
    extensions: [
      "權益分級建議",
      "偏好標籤初始化",
      "回訪節奏規劃",
    ],
    outcome: "你可以先得到可核對的註冊最小欄位草稿，並保留可直接導入下一步的上下文。",
  },
  order_or_booking: {
    solves: [
      "抽取時間與人數",
      "列出可核對項目（品項、口味、配送）",
      "生成候選確認清單",
    ],
    extensions: [
      "時段衝突提醒",
      "付款前條件提示",
      "外送與到店條件映射",
    ],
    outcome: "你可以先拿到可核對的預約/下單草稿，避免缺欄位造成返工。",
  },
  support_complaint: {
    solves: [
      "拆解故障時序",
      "保留重現步驟",
      "輸出客服可接續腳本",
    ],
    extensions: [
      "SLA 建議",
      "跨通路補件提示",
      "情緒降溫文案包",
    ],
    outcome: "你可先得到可回放的問題路徑，接著再進入人工支援流程。",
  },
  member_value: {
    solves: [
      "對齊會員可用價值清單",
      "識別可量化服務指標",
      "輸出下一步行動",
    ],
    extensions: [
      "回訪節奏",
      "留存建議",
      "轉單機會",
    ],
    outcome: "你可以直接看到會員價值與優先可執行的服務擴散方向。",
  },
  risk_governance: {
    solves: [
      "阻斷越權寫入",
      "明確顯示安全限制",
      "保留候選到人工核可",
    ],
    extensions: [
      "風險條件清單",
      "確認流程模板",
      "人機協作決策節點",
    ],
    outcome: "目前先保全，先補齊規範條件後再走候選進場。",
  },
  general: {
    solves: [
      "整理意圖與上下文",
      "形成可理解回覆",
      "提供可核對候選內容",
    ],
    extensions: [
      "語氣與節奏調整",
      "補欄位引導",
      "下一步執行提示",
    ],
    outcome: "先得到可核對候選回覆，你可以直接補齊條件讓它變成可交付草稿。",
  },
};

function renderValueOutcome(root, scenario, decision, valueLayer) {
  if (!root) {
    return;
  }
  const key = CAPABILITY_LIBRARY[scenario] ? scenario : "general";
  const profile = CAPABILITY_LIBRARY[key] || CAPABILITY_LIBRARY.general;
  const headline = decision === "PASS"
    ? "結果可直接接續"
    : "結果先保全，等待確認";
  const outcome = profile.outcome;
  const benefit = Array.isArray(valueLayer?.highlights) ? valueLayer.highlights.join("；") : "";
  root.innerHTML = `
    <div class="media-hint">${escapeHtml(headline)}</div>
    <div class="media-hint">${escapeHtml(outcome)}</div>
    ${benefit ? `<div class="media-hint">附加亮點：${escapeHtml(benefit)}</div>` : ""}
  `;
}

function renderExtensions(root, scenario, decision) {
  if (!root) {
    return;
  }
  const key = CAPABILITY_LIBRARY[scenario] ? scenario : "general";
  const profile = CAPABILITY_LIBRARY[key] || CAPABILITY_LIBRARY.general;
  const solves = Array.isArray(profile.solves) ? profile.solves : [];
  const extendsTo = Array.isArray(profile.extensions) ? profile.extensions : [];

  root.innerHTML = "";
  if (!solves.length && !extendsTo.length) {
    root.textContent = "此場景目前尚無明確衍伸建議。";
    return;
  }

  const renderBlock = (title, items, label) => {
    const block = document.createElement("article");
    block.className = "extension-item";
    block.innerHTML = `
      <h4>${escapeHtml(title)}${decision !== "PASS" ? "（待確認）" : ""}</h4>
      <p>${items.length ? escapeHtml(items.join("、")) : escapeHtml(label)}</p>
    `;
    root.appendChild(block);
  };

  renderBlock("本次可解決", solves, "可解決項目將在下一輪顯示");
  renderBlock("可衍伸", extendsTo, "可衍伸項目將在下一輪顯示");
}

function renderSolutionScenarios(root, scenarioData, decision) {
  if (!root) {
    return;
  }
  if (typeof scenarioData === "object" && scenarioData && !Array.isArray(scenarioData)) {
    const pack = scenarioData || {};
    root.innerHTML = `
      <div class="scenario-chips">
        <div class="scenario-chip">
          <div class="scenario-chip-title">${escapeHtml(String(pack.title || "場景回應"))}</div>
          <div class="media-hint">${escapeHtml(String(pack.solve || "已保留對應場景解析。"))}</div>
        </div>
        <div class="scenario-chip">
          <div class="scenario-chip-title">可延伸能力</div>
          <div class="media-hint">${escapeHtml(String(pack.extend || "可後續對接更完整流程。"))}</div>
        </div>
        <div class="scenario-chip">
          <div class="scenario-chip-title">目前風控狀態</div>
          <div class="media-hint">${escapeHtml(String(pack.risk || `決策：${decision}`))}</div>
        </div>
      </div>
    `;
    return;
  }

  const scenarioKey = String(scenarioData || "").trim() || "general";
  const scenarioMap = {
    member_registration: {
      title: "會員註冊導向",
      solve: "把自然語言快速轉為可核對的註冊條件草稿，先避開自動寫入。",
      extend: "可延伸到名片導向、權益頁啟用、偏好預設。",
      risk: decision !== "PASS" ? "持續 HOLD：先補齊必要欄位與權益確認" : "PASS：候選可交付「先行閱讀版」給客服。",
    },
    order_or_booking: {
      title: "預約與下單導向",
      solve: "先抽取時間、品項、數量、偏好，生成可核對候選流程。",
      extend: "可延伸到排程衝突檢查與外送條件提示。",
      risk: decision !== "PASS" ? "持續 HOLD：先補齊場景條件再進入候選" : "PASS：可直接作為人工核對草稿。",
    },
    support_complaint: {
      title: "客服支援導向",
      solve: "把抱怨/問題先標準化為可回放的重現路徑，降低一次處理成本。",
      extend: "可延伸到 SLA 建議與跨通路補件提醒。",
      risk: decision !== "PASS" ? "持續 HOLD：先補齊時間軸與重現步驟" : "PASS：可轉為可執行客服腳本草稿。",
    },
    risk_governance: {
      title: "高風險請求守門",
      solve: "先把高風險操作隔離，避免支付、寫入、部署、重啟誤觸。",
      extend: "可延伸到權限審核清單與人確認雙簽流程。",
      risk: "先 HOLD：等待人工確認後再進入正式動作。",
    },
    general: {
      title: "一般詢問導向",
      solve: "先對齊語境與邊界，將可落地資訊整理成可理解回答。",
      extend: "可延伸到「可執行清單化」與個人化語氣偏好。",
      risk: decision !== "PASS" ? "以 HOLD 優先，避免越權" : "PASS：先保留候選，等待確認。",
    },
  };
  const data = scenarioMap[scenarioKey] || scenarioMap.general;

  root.innerHTML = `
    <div class="scenario-chips">
      <div class="scenario-chip">
        <div class="scenario-chip-title">${escapeHtml(data.title)}</div>
        <div class="media-hint">${escapeHtml(data.solve)}</div>
      </div>
      <div class="scenario-chip">
        <div class="scenario-chip-title">可延伸能力</div>
        <div class="media-hint">${escapeHtml(data.extend)}</div>
      </div>
      <div class="scenario-chip">
        <div class="scenario-chip-title">目前風控狀態</div>
        <div class="media-hint">${escapeHtml(data.risk || `決策：${decision}`)}</div>
      </div>
    </div>
  `;
}

function renderEmotionProfile(aesthetic, decision) {
  const root = el("emotionProfile");
  if (!root) {
    return;
  }
  const rawEmotion = Number(aesthetic?.emotion);
  const tone = String(aesthetic?.tone || "穩定");
  const safeEmotion = Number.isFinite(rawEmotion) ? rawEmotion : 4;
  const clamped = Math.max(0, Math.min(8, Math.round(rawEmotion)));
  const percent = (clamped / 8) * 100;

  root.innerHTML = `
    <div class="emotion-panel">
      <div class="emotion-row">
        <span class="emotion-label">情緒溫度：${tone}</span>
        <span class="media-hint">${decision || "PASS"} · 指數 ${clamped}/8</span>
      </div>
      <div class="emotion-meter" style="--emotion-percent:${percent.toFixed(1)}%;"></div>
      <div class="media-hint">當前節奏：${safeEmotion >= 6 ? "關懷外放" : safeEmotion >= 3 ? "平衡陪伴" : "低調收斂"}</div>
    </div>
  `;
}

function renderSceneContext(scene) {
  const box = el("sceneContextBox");
  const data = scene || {};
  el("sceneContextStatus").textContent = statusText(data.context_type || "UNKNOWN_CONTEXT");
  el("identityVerifiedStatus").textContent = data.identity_verified === true ? "TRUE" : "FALSE";
  box.innerHTML = "";
  [
    ["context_type", data.context_type || "UNKNOWN_CONTEXT"],
    ["confidence_level", data.confidence_level || "L1"],
    ["accepted_as_truth", data.accepted_as_truth === true],
    ["device_trust", data.device_trust === true],
    ["identity_verified", data.identity_verified === true],
    ["accepted_as_person_identity", data.accepted_as_person_identity === true],
    ["requires_role_verification", data.requires_role_verification === true],
    ["dev_identity_override", data.dev_identity_override?.enabled === true ? data.dev_identity_override.role_ref : "off"],
    ["allowed_scope", (data.allowed_scope || []).join(", ") || "N/A"],
    ["forbidden_scope", (data.forbidden_scope || []).join(", ") || "N/A"]
  ].forEach(([key, value]) => {
    const row = document.createElement("div");
    row.className = "scene-row";
    row.innerHTML = `<b>${escapeHtml(key)}</b><span>${escapeHtml(value)}</span>`;
    box.appendChild(row);
  });
}

function translateCloudModelResponse(rawText, mode) {
  const raw = String(rawText || "").replace(/\s+/g, " ").trim();
  if (!raw) {
    return "尚未收到可轉譯的雲端模型內容。";
  }

  if (mode === "compact") {
    const sentence = raw.split(/[。!?！？.!]/).find((part) => part.trim().length > 4);
    return sentence ? `${sentence.trim()}。` : `${raw.slice(0, 90)}…`;
  }

  if (mode === "poetic") {
    return `先把意思整理成更有感的版本：\n${raw}\n── 小J 先把節奏收著，下一句再繼續。`;
  }

  if (mode === "human") {
    return `我先幫你把這段轉成人可讀版本：${raw}`;
  }

  return raw;
}

function updateCloudModelTranslatorView() {
  const mode = String(el("cloudTranslatorProfile")?.value || "raw");
  if (!lastCloudModelPacket) {
    const translatorTextNode = el("cloudModelTranslatorText");
    if (translatorTextNode) {
      translatorTextNode.textContent = "尚未執行轉譯。";
    }
    const translatorModeNode = el("cloudTranslatorMode");
    if (translatorModeNode) {
      translatorModeNode.textContent = `模式：${mode}`;
    }
    const copyStatus = el("cloudTranslatorCopyStatus");
    if (copyStatus) {
      copyStatus.textContent = "";
    }
    return;
  }
  const sourceText = lastCloudModelPacket.response_text || lastCloudModelPacket.response_packet?.text_zh_TW || "";
  const translated = translateCloudModelResponse(sourceText, mode);
  const translatorTextNode = el("cloudModelTranslatorText");
  if (translatorTextNode) {
    translatorTextNode.textContent = translated;
  }
  const translatorModeNode = el("cloudTranslatorMode");
  if (translatorModeNode) {
    translatorModeNode.textContent = `模式：${mode}`;
  }
  const copyStatus = el("cloudTranslatorCopyStatus");
  if (copyStatus) {
    copyStatus.textContent = "";
  }
}

function renderScenarioDeck() {
  const root = el("scenarioDeck");
  if (!root) {
    return;
  }
  root.innerHTML = "";
  scenarioDeckCards.forEach((card) => {
    const node = document.createElement("article");
    node.className = "scenario-card";
    node.innerHTML = `
      <strong>${escapeHtml(card.title)}</strong>
      <div class="media-hint">${escapeHtml(card.tag)}</div>
      <div class="media-hint">${escapeHtml(card.tone)}</div>
      <button type="button" data-prompt="${escapeHtml(card.prompt)}">一鍵試算</button>
    `;
    const button = node.querySelector("button");
    if (button) {
      button.addEventListener("click", () => {
        const input = el("inputText");
        if (input) {
          input.value = card.prompt;
          input.focus();
        }
      });
    }
    root.appendChild(node);
  });
}

function setHeroWelcome(text) {
  const hero = el("literaryWelcome");
  if (!hero) {
    return;
  }
  hero.textContent = text;
}

function updateHeroForResult(decision, scenario, riskLevel) {
  const tone = String(riskLevel || "MEDIUM").toUpperCase();
  const map = {
    PASS: "已為你整理成下一步可落地的候選稿，接著補齊條件就能進入人工核可。",
    HOLD: "我先替你把風險邊界壓住了，避免越權動作。補一個關鍵欄位後我會立即回到候選路徑。",
    BLOCK: "我先暫停這條路徑，確保不會有正式寫入、部署或付款動作。",
  };
  const suffix = tone === "LOW" ? "整體節奏偏穩，文風會更貼心。" : "我會保留保全紅線，先讓回覆可核可。";
  const base = map[decision] || "回覆已進入安全候選流程，你可以接著補齊條件。";
  setHeroWelcome(`${base} ${suffix}（場景：${escapeHtml(scenario || "general")}）`);
}

function copyLatestAnswer() {
  const text = el("answerText")?.textContent || "";
  const status = el("answerCopyStatus");
  if (!text || !navigator.clipboard) {
    if (status) {
      status.textContent = "無法直接複製，請手動複製。";
    }
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    if (status) {
      status.textContent = "已複製最新回覆到剪貼簿。";
    }
  }).catch(() => {
    if (status) {
      status.textContent = "複製失敗，請手動複製。";
    }
  });
}

function clearConversation() {
  el("inputText").value = "";
  el("chatLog").innerHTML = "";
  el("decisionBadge").className = "decision";
  el("decisionBadge").textContent = "WAITING";
  el("answerText").textContent = "尚未執行。";
  el("rawDraftText").textContent = "尚未執行。";
  el("prAnswerText").textContent = "尚未執行。";
  el("memberFacingMessage").textContent = "尚未執行。";
  el("valueOutcome").textContent = "尚未執行。";
  el("extensionList").textContent = "尚未執行。";
  el("solvedProblems").textContent = "尚未執行。";
  el("notCovered").textContent = "尚未執行。";
  el("solutionScenarios").textContent = "尚未執行。";
  el("literaryFlow").textContent = "尚未執行。";
  el("experienceGuarantee").textContent = "尚未執行。";
  el("actionPack").textContent = "{}";
  renderActionPack({});
  renderSafety({});
  setHeroWelcome("已清空對話，輸入新需求即可重新開始。");
  const status = el("answerCopyStatus");
  if (status) {
    status.textContent = "尚未產生可複製文字。";
  }
}

function renderCloudProfileSummary(data) {
  const summarySource = data.COCKPIT_VIEW?.cloud_model || {};
  const translatorMode = String(el("cloudTranslatorProfile")?.value || "raw");
  const requestedRef = summarySource.requested_ai_key_ref || data.CLOUD_MODEL_REF || "";
  const lane = summarySource.response_model_lane || data.PR_LAYER?.MODEL_LANE || "OFF";
  renderJson(el("aiProfileSummary"), {
    member_ai_key_ref: requestedRef || "未指定（使用封包預設）",
    translator_mode: translatorMode,
    model_lane: lane,
  });
  const line = el("aiProfileSummary");
  if (line) {
    line.dataset.saved = requestedRef ? "selected" : "unset";
  }
}

function copyCloudTranslatorText() {
  const source = el("cloudModelTranslatorText");
  const status = el("cloudTranslatorCopyStatus");
  if (!source) {
    return;
  }
  const text = String(source.textContent || "");
  if (!text || !navigator.clipboard) {
    if (status) {
      status.textContent = "無法複製，請手動複製。";
    }
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    if (status) {
      status.textContent = "已複製到剪貼簿。";
    }
  }).catch(() => {
    if (status) {
      status.textContent = "複製失敗，請手動複製。";
    }
  });
}

function renderInspector(packet) {
  activePacket = packet || {};
  renderJson(el("packetInspector"), activePacket);
  const tabs = el("inspectorTabs");
  tabs.innerHTML = "";
  d8Labels.forEach(([key, label]) => {
    const btn = document.createElement("button");
    btn.className = "tab-btn";
    btn.textContent = label;
    btn.addEventListener("click", () => {
      renderJson(el("packetInspector"), activePacket[key] || "N/A");
    });
    tabs.appendChild(btn);
  });
}

function renderTimeline(timeline) {
  const box = el("timeline");
  box.innerHTML = "";
  (timeline || []).forEach((item, idx) => {
    const node = document.createElement("button");
    node.className = "timeline-item";
    node.innerHTML = `
      <span class="step">${escapeHtml(item.step || ("S" + idx))}</span>
      <span class="meta">${escapeHtml(item.packet_type || "packet")}</span>
      <span class="hash">${escapeHtml((item.packet_hash || "").slice(0, 18))}</span>
      <span class="row">
        <span class="risk">${escapeHtml(item.risk_code || "none")}</span>
        <span class="decision-mini">${escapeHtml(item.decision || "CONTINUE")}</span>
      </span>
      <span class="table">${escapeHtml(item.table_ref || "N/A")}</span>
      <span class="table">${escapeHtml(item.template_ref || "N/A")}</span>
    `;
    node.addEventListener("click", () => {
      renderInspector(item.packet || item);
      renderJson(el("evidenceBox"), {
        packet_hash: item.packet_hash,
        parent_packet_hash: item.parent_packet_hash,
        table_ref: item.table_ref,
        template_ref: item.template_ref,
        seal: item.packet?.D8_envelope?.seal || "",
        created_at: item.packet?.D8_envelope?.created_at_unix || ""
      });
    });
    box.appendChild(node);
  });

  if ((timeline || []).length > 0) {
    renderInspector(timeline[0].packet || timeline[0]);
  }
}

function renderCockpit(data, originalText) {
  const summary = data.COCKPIT_VIEW?.summary || {};
  const badges = data.COCKPIT_VIEW?.badges || {};
  const decision = summary.decision || badges.decision || data.FINAL_VERIFIER?.decision || "UNKNOWN";
  const humanResponse = data.COCKPIT_VIEW?.human_response || data.human_response || {};
  const responseVariants = humanResponse.response_variants || {};
  const toneProfile = _clampToneProfile(String(el("responseTone")?.value || "natural"));
  const preferredVariant = _toneVariantForProfile(toneProfile);
  const preferredAnswer = String(responseVariants[preferredVariant] || "").trim();
  const answer = preferredAnswer || humanResponse.reply_text || data.LANGUAGE_RECONSTRUCTION?.zh_TW || summary.output || "無輸出";
  const rawDraft = summary.raw_verified_draft || data.LANGUAGE_RECONSTRUCTION?.raw_verified_draft || answer;
  const prAnswer = summary.pr_refined_answer || data.LANGUAGE_RECONSTRUCTION?.pr_refined_zh_TW || answer;
  const decisionLocked = summary.decision_locked !== false;
  const sceneContext = data.COCKPIT_VIEW?.scene_context || data.LANGUAGE_RECONSTRUCTION?.semantic_ir?.scene_context || {};

  el("decisionBadge").className = badgeClass(decision);
  el("decisionBadge").textContent = decision;
  el("answerText").textContent = answer;
  el("rawDraftText").textContent = rawDraft;
  el("prAnswerText").textContent = prAnswer;
  el("decisionLockedBox").textContent = decisionLocked ? "TRUE" : "FALSE";
  el("decisionLockedStatus").textContent = decisionLocked ? "TRUE" : "FALSE";
  el("prLayerStatus").textContent = statusText(badges.pr_layer || data.PR_LAYER?.MODEL_LANE || "TEMPLATE_FALLBACK");
  el("personaTone").textContent = humanResponse.persona_voice_hint || "以自然語氣回覆。";
  el("assistantTone").textContent = _toneProfileLabel(toneProfile);
  el("personaProjection").textContent = `${humanResponse.persona_projection || "GENERAL_XIAOJ"} / ${humanResponse.service_context || "general"}`;
  el("memberFacingMessage").textContent = humanResponse.member_facing_message || answer;
  const scenario = humanResponse.scenario || inferScenarioKey(humanResponse.action_pack || {}, humanResponse, decision);
  const nextAction = humanResponse?.aesthetic?.next_action_hint || "你可回覆更清楚條件後，我會繼續候選流程。";
  el("nextActionHint").textContent = nextAction;
  renderReplyVariants(el("replyVariants"), responseVariants, preferredVariant);
  renderLiteraryCard(el("literaryFlow"), humanResponse, decision);
  renderValueLayer(el("valueLayer"), humanResponse.value_layer || {});
  renderValueOutcome(el("valueOutcome"), scenario, decision, humanResponse.value_layer || {});
  renderExtensions(el("extensionList"), scenario, decision);
  renderProductScope(el("solvedProblems"), el("notCovered"), scenario, decision);
  renderExperienceGuarantee(el("experienceGuarantee"), scenario, decision, humanResponse, humanResponse.action_pack || {});
  const actionPack = humanResponse.action_pack || {};
  if (humanResponse.solution_scenarios && typeof humanResponse.solution_scenarios === "object") {
    renderSolutionScenarios(el("solutionScenarios"), humanResponse.solution_scenarios, decision);
  } else {
    renderSolutionScenarios(el("solutionScenarios"), inferScenarioKey(actionPack, humanResponse, decision), decision);
  }
  renderJson(el("actionPack"), actionPack);
  renderActionPack(actionPack);
  renderSuggestionChips(actionPack);
  renderMediaResponse(el("mediaResponse"), humanResponse.media_response || {});
  renderEmotionProfile(humanResponse.aesthetic || {}, decision);
  updateHeroForResult(decision, scenario, data.FINAL_VERIFIER?.risk_level || summary.risk_level || "MEDIUM");

  renderJson(el("verifierBox"), data.FINAL_VERIFIER || {});
  renderTimeline(data.COCKPIT_VIEW?.timeline || []);
  renderSafety(data.SAFETY_FLAGS || {});
  renderCloudProfileSummary(data);
  renderSceneContext(sceneContext);
  renderJson(el("semanticBox"), data.LANGUAGE_RECONSTRUCTION || {});
  renderJson(el("evidenceBox"), {
    input_hash: data.INPUT_TEXT_HASH,
    audit_file: summary.audit_file,
    run_mode: data.RUN_MODE,
    model_lane: badges.model_lane,
    pr_layer: badges.pr_layer || data.PR_LAYER?.MODEL_LANE,
    llm_authority: badges.llm_authority,
    verifier_decision_locked: badges.verifier_decision_locked,
    model_output: badges.model_output,
    lookup_lane: badges.lookup_lane,
    verifier_authority: badges.verifier_authority,
    pr_response_packet: data.PR_LAYER?.RESPONSE_PACKET || {}
  });
  renderJson(el("cloudModelPacket"), data.COCKPIT_VIEW?.cloud_model || {
    note: "未啟用雲端候選 key",
    model_lane: badges.model_lane || data.PR_LAYER?.MODEL_LANE || "OFF",
    model_output: badges.model_output || "candidate-only",
  });
  const cloudModelPacket = data.COCKPIT_VIEW?.cloud_model || {};
  lastCloudModelPacket = cloudModelPacket;
  const cloudModelText = cloudModelPacket.response_text || cloudModelPacket.response_packet?.text_zh_TW || "";
  const translatorMode = String(el("cloudTranslatorProfile")?.value || "raw");
  const translated = translateCloudModelResponse(cloudModelText, translatorMode);
  const cloudTranslatorText = el("cloudModelTranslatorText");
  const cloudTranslatorMode = el("cloudTranslatorMode");
  if (cloudTranslatorText) {
    cloudTranslatorText.textContent = translated;
  }
  if (cloudTranslatorMode) {
    cloudTranslatorMode.textContent = `模式：${translatorMode}`;
  }
  const copyStatus = el("cloudTranslatorCopyStatus");
  if (copyStatus) {
    copyStatus.textContent = "";
  }

  const line = document.createElement("div");
  line.className = "chat-line";
  line.innerHTML = `<b>你：</b>${escapeHtml(originalText)}<br><b>總場：</b>${escapeHtml(answer)}`;
  el("chatLog").prepend(line);
}

async function health() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    el("healthBadge").className = "badge badge-green";
    el("healthBadge").textContent = data.STATE || "HEALTH";
  } catch {
    el("healthBadge").className = "badge badge-amber";
    el("healthBadge").textContent = "PUBLIC STATIC DEMO";
  }
}

function renderStaticDemoFallback(text, err) {
  const answer = "公開網域目前是靜態展示入口，未連接本機 /api/chat 封包推理服務。這不代表 verifier 已准駁；正式推理、身份驗證、會員上下文、付款與 production 動作仍需回到總場授權通道。";
  el("decisionBadge").className = "decision hold";
  el("decisionBadge").textContent = "HOLD";
  el("answerText").textContent = answer;
  el("rawDraftText").textContent = "PUBLIC_STATIC_DEMO: API unavailable on public static route.";
  el("prAnswerText").textContent = answer;
  el("decisionLockedBox").textContent = "TRUE";
  el("decisionLockedStatus").textContent = "TRUE";
  el("prLayerStatus").textContent = "STATIC DEMO FALLBACK";
  el("personaTone").textContent = "系統保守提示模式";
  el("personaProjection").textContent = "GENERAL_XIAOJ / general";
  el("memberFacingMessage").textContent = answer;
  renderReplyVariants(el("replyVariants"), {
    default: answer,
    concise: answer,
    poetic: answer,
  }, _toneVariantForProfile("natural"));
  el("nextActionHint").textContent = "請回到本機 /api/chat 後再發起一次，或到總場授權通道提交明確條件。";
  renderLiteraryCard(el("literaryFlow"), {
    aesthetic: {
      tone: "保守提示",
      scene: "公開靜態展示，未連接正式推理服務。",
      headline: "系統回退回應",
      poetic_line: "《資料先不進行正式送件，先保持可確認。》",
      poem_line_2: "待服務復原後可回到完整候選流程。",
      next_action_hint: "請回到本機 /api/chat 後再重試。",
      decision_aura: "HOLD",
    },
  }, "HOLD");
  renderValueLayer(el("valueLayer"), {
    mode: "靜態展示保全",
    highlights: ["未連接正式 API，暫不提供會員價值展開。"],
    member_advantage: "請切回可用總場通道後再回到候選流程。",
    competitive_edge: "安全優先的保全優先示範。"
  });
  renderValueOutcome(el("valueOutcome"), "risk_governance", "HOLD", {
    highlights: ["本輪示範為只讀模式，先保全。"],
  });
  renderExtensions(el("extensionList"), "risk_governance", "HOLD");
  renderSolutionScenarios(el("solutionScenarios"), "risk_governance", "HOLD");
  el("assistantTone").textContent = "自然陪伴";
  renderMediaResponse(el("mediaResponse"), {
    mode: "TEXT_ONLY",
    voice_hint: "no_audio",
    audio_script: "",
    video_mode: "NONE",
    video_hint: "公開靜態入口不提供影音播放。"
  });
  renderJson(el("verifierBox"), {
    decision: "HOLD",
    reason: "public static route has no verifier API",
    llm_authority: false,
    decision_locked: true
  });
  renderTimeline([]);
  renderSafety({
    payment_capture: false,
    member_plaintext_read: false,
    secret_read: false,
    db_write: false,
    production_deploy: false
  });
  renderSceneContext({
    context_type: "PUBLIC_STATIC_DEMO",
    confidence_level: "L0",
    accepted_as_truth: false,
    device_trust: false,
    identity_verified: false,
    accepted_as_person_identity: false,
    requires_role_verification: true,
    allowed_scope: ["public_demo_view"],
    forbidden_scope: ["secret_read", "member_plaintext_read", "payment_capture", "production_deploy", "grant_identity_role"]
  });
  renderJson(el("semanticBox"), {
    input_preview: text,
    fallback_error: String(err || "API unavailable"),
    model_authority: false
  });
  renderJson(el("actionPack"), {
    mode: "static_demo_safety_hold",
    goal: "先回到可用 /api/chat 後再產生候選草稿。",
    required_fields: ["可連接總場授權通道"],
    optional_fields: ["更清晰的邊界敘述"],
    verification_checks: ["公開入口無正式請求權限"],
    human_confirmation: "請回到本機 API 端點後重試。",
    candidate_note: "目前僅展示靜態保全回應。"
  });
  renderActionPack({
    mode: "static_demo_safety_hold",
    goal: "先回到可用 /api/chat 後再產生候選草稿。",
    required_fields: ["可連接總場授權通道"],
    optional_fields: ["更清晰的邊界敘述"],
    verification_checks: ["公開入口無正式請求權限"],
    human_confirmation: "請回到本機 API 端點後重試。",
    candidate_note: "目前僅展示靜態保全回應。"
  });
  renderEmotionProfile({
    emotion: 1,
    tone: "保守提醒",
  }, "HOLD");
  renderJson(el("evidenceBox"), {
    route: "public_static_demo",
    api_chat: "unavailable",
    verifier_decision_locked: true
  });
  renderProductScope(el("solvedProblems"), el("notCovered"), "risk_governance", "HOLD");
  renderExperienceGuarantee(el("experienceGuarantee"), "risk_governance", "HOLD", {
    value_layer: {
      highlights: ["未連接正式推理服務，僅示範保全輸出。"],
      member_advantage: "請回到正式入口後再啟動候選草稿。",
      competitive_edge: "先保全、後接續，保留會員風險邊界。",
      next_readiness: ["連接總場授權 API", "補齊條件關鍵欄位"]
    }
  }, {
    required_fields: ["可連接總場授權通道"],
    optional_fields: ["更清晰的邊界敘述"],
  });
  const line = document.createElement("div");
  line.className = "chat-line";
  line.innerHTML = `<b>你：</b>${escapeHtml(text)}<br><b>總場：</b>${escapeHtml(answer)}`;
  el("chatLog").prepend(line);
  renderJson(el("cloudModelPacket"), {
    note: "public static demo: no active cloud model lane",
    model_lane: "OFF",
    model_output: "disabled",
    model_response_available: false,
  });
  const fallbackMode = String(el("cloudTranslatorProfile")?.value || "raw");
  const cloudTranslatorText = el("cloudModelTranslatorText");
  if (cloudTranslatorText) {
    cloudTranslatorText.textContent = "未連接 API，目前僅示範流程，不做雲端模型轉譯。";
  }
  const cloudTranslatorMode = el("cloudTranslatorMode");
  if (cloudTranslatorMode) {
    cloudTranslatorMode.textContent = `模式：${fallbackMode}`;
  }
  const copyStatus = el("cloudTranslatorCopyStatus");
  if (copyStatus) {
    copyStatus.textContent = "";
  }
  renderJson(el("aiProfileSummary"), {
    member_ai_key_ref: "未指定（公開示範）",
    translator_mode: fallbackMode,
    model_lane: "OFF",
  });
  updateHeroForResult("HOLD", "risk_governance", "MEDIUM");
}

async function runChat() {
  const text = el("inputText").value.trim();
  if (!text) return;

  el("runBtn").disabled = true;
  el("runBtn").textContent = "RUNNING...";
  lastChatInputText = text;

  const payload = {
    text,
    branch: el("branch").value || "cafe_main",
    actor_role: el("actorRole").value || "counter_ai",
    channel: el("channel").value || "web_cockpit",
    cloud_translator_profile: String(el("cloudTranslatorProfile")?.value || "raw"),
    response_tone_profile: String(el("responseTone")?.value || "natural"),
    ai_key_ref: resolveAiKeyRef(),
    dev_role_ref: el("devRoleRef").value || "",
    dev_identity_switch: el("devIdentitySwitch").checked === true
  };
  const aiKeyRef = payload.ai_key_ref;
  const aiKeySourceLabel = aiKeySource(
    String(el("aiKeyRef")?.value || ""),
    String(el("aiKeyCustom")?.value || "")
  );
  saveProfile({
    ai_key_ref: aiKeyRef,
    ai_key_source: aiKeySourceLabel,
    cloud_translator_profile: String(el("cloudTranslatorProfile")?.value || "raw"),
    response_tone_profile: String(el("responseTone")?.value || "natural"),
    branch: payload.branch,
    actor_role: payload.actor_role,
    channel: payload.channel,
  });

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    lastCockpitResult = data;
    renderCockpit(data, text);
  } catch (err) {
    lastCockpitResult = null;
    renderStaticDemoFallback(text, err);
  } finally {
    el("runBtn").disabled = false;
    el("runBtn").textContent = "RUN PACKET INFERENCE";
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[char]));
}

function initDemos() {
  const box = el("demoButtons");
  demos.forEach(([label, text]) => {
    const button = document.createElement("button");
    button.className = "demo-btn";
    button.textContent = label;
    button.addEventListener("click", () => {
      el("inputText").value = text;
      runChat();
    });
    box.appendChild(button);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initDemos();
  renderScenarioDeck();
  setHeroWelcome("小J 已準備好：輸入需求後，我先幫你做「安全候選」與可執行草稿。");
  health();
  applySavedProfile();
  updateCloudModelTranslatorView();
  const cloudTranslatorProfile = el("cloudTranslatorProfile");
  if (cloudTranslatorProfile) {
    cloudTranslatorProfile.addEventListener("change", updateCloudModelTranslatorView);
  }
  const copyCloudTranslatorButton = el("copyCloudTranslatorText");
  if (copyCloudTranslatorButton) {
    copyCloudTranslatorButton.addEventListener("click", copyCloudTranslatorText);
  }
  const responseTone = el("responseTone");
  if (responseTone) {
    responseTone.addEventListener("change", () => {
      if (lastCockpitResult) {
        renderCockpit(lastCockpitResult, lastChatInputText || "你");
      }
    });
  }
  const inputText = el("inputText");
  if (inputText) {
    inputText.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        runChat();
      }
    });
  }
  el("runBtn").addEventListener("click", runChat);
  const copyBtn = el("copyAnswerBtn");
  if (copyBtn) {
    copyBtn.addEventListener("click", copyLatestAnswer);
  }
  const clearBtn = el("clearChatBtn");
  if (clearBtn) {
    clearBtn.addEventListener("click", clearConversation);
  }
});
