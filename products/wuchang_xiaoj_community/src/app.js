import {
  approveActionReview,
  createActionReviewPacket,
  rejectActionReview,
} from "./action-review.js";
import { buildOdooProjectionCandidate } from "./odoo-authority.js";
import { PRODUCT_CONTRACT, SYNTHETIC_SESSION } from "./product-contract.js";
import { getLocalXiaojCandidate } from "./xiaoj-candidate.js";

const actionStore = new Map();
let currentView = "home";
let personalImageCandidate = null;
let personalImagePreviewUrl = null;

const CURRENT_XIAOJ_IMAGE = Object.freeze({
  assetRef: "asset://wuchang-xiaoj/prior-codex-white-haired-service-worker",
  sha256: "691b23d874688f351f6729388e6250ee6de974ce75d3ed34e2136d2bfda61140",
});

const ACTION_TEMPLATES = Object.freeze({
  "resident-service-request": {
    sceneRef: "RESIDENT",
    purpose: "建立一張居民服務需求候選，等待本人確認",
    feature: "居民服務需求候選",
    actionType: "ODOO_WORKFLOW_WRITE_CANDIDATE",
    targetRefs: ["logical://taiji01/odoo", "candidate://resident-service-request"],
    parameters: {
      request_kind: "resident_service",
      member_input: "NOT_COLLECTED_IN_CANDIDATE",
      submit: false,
    },
    parameterSummary: "服務類型：居民服務；目前不收集個人明文；正式送出：否",
    expectedResult: "產生一張可供本人檢查的服務需求候選",
    changes: "若日後正式執行，可能在Odoo建立一筆服務流程紀錄",
    unchanged: "本候選不寫入Odoo、不通知外部、不改變會員權限",
    maximumEffect: "最多建立一筆與本會員及本次session綁定的服務需求",
    risk: "內容若不完整，可能需要補充；正式執行前可拒絕",
    rollback: "候選模式零副作用；正式流程須使用Odoo既有撤銷或補償契約",
    flags: { money: false, memberData: true, externalSend: false, deletion: false },
  },
  "business-subscription-review": {
    sceneRef: "BUSINESS_CLOUD",
    purpose: "確認商業雲適用區域與訂閱規則",
    feature: "商業雲方案候選",
    actionType: "SUBSCRIPTION_ELIGIBILITY_CANDIDATE",
    targetRefs: ["logical://taiji01/odoo", "candidate://business-cloud-eligibility"],
    parameters: {
      district_scope: "TO_BE_CONFIRMED_BY_MEMBER",
      in_district_fee: 0,
      out_of_district_fee_state: "PAID_RATE_UNBOUND",
      beneficiary: "COMMUNITY_DIGITAL_DEVELOPMENT_FUND",
    },
    parameterSummary: "轄區：待本人確認；轄區內：免費訂閱；轄區外費率：尚未綁定；收入歸社區數位發展基金",
    expectedResult: "只產生適用資格與後續確認候選，不建立訂閱",
    changes: "若日後正式執行，可能建立一筆商業雲訂閱關係",
    unchanged: "不購買Founder、治理、會員主權根或管委會決策權",
    maximumEffect: "最多建立一筆經本人確認且符合Odoo資格規則的訂閱",
    risk: "涉及費用時必須顯示精確金額並重新取得專用批准",
    rollback: "本候選零副作用；正式訂閱須依Odoo帳務與取消規則處理",
    flags: { money: true, memberData: true, externalSend: false, deletion: false },
  },
  "property-service-review": {
    sceneRef: "PROPERTY_CLOUD",
    purpose: "建立物業服務協作候選，保留管委會決策權",
    feature: "物業雲服務候選",
    actionType: "PROPERTY_WORKFLOW_CANDIDATE",
    targetRefs: ["logical://taiji01/odoo", "candidate://property-cloud-service"],
    parameters: {
      district_scope: "TO_BE_CONFIRMED_BY_MEMBER",
      committee_decision_right: "PRESERVED",
      system_decision_authority: false,
    },
    parameterSummary: "轄區：待本人確認；管委會決策權：保留；系統決策權：無",
    expectedResult: "只產生物業服務協作候選，不發布公告或改變資料",
    changes: "若日後正式執行，可能建立一筆物業服務流程",
    unchanged: "不取代管委會決策、不改會員權限、不寫帳務",
    maximumEffect: "最多建立一筆受權限限制的物業服務流程",
    risk: "任何公告、帳務或資料變更都必須另行顯示並批准",
    rollback: "本候選零副作用；正式流程須使用Odoo既有補償契約",
    flags: { money: false, memberData: true, externalSend: false, deletion: false },
  },
});

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function humanFileSize(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function hasExpectedImageSignature(bytes, mimeType) {
  const textAt = (offset, length) =>
    String.fromCharCode(...bytes.slice(offset, offset + length));
  if (mimeType === "image/png") {
    return (
      bytes.length >= 8
      && bytes[0] === 0x89
      && textAt(1, 3) === "PNG"
      && bytes[4] === 0x0d
      && bytes[5] === 0x0a
      && bytes[6] === 0x1a
      && bytes[7] === 0x0a
    );
  }
  if (mimeType === "image/jpeg") {
    return bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  }
  if (mimeType === "image/webp") {
    return bytes.length >= 12 && textAt(0, 4) === "RIFF" && textAt(8, 4) === "WEBP";
  }
  return false;
}

async function sha256Bytes(bytes) {
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function readImageDimensions(objectUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => {
      resolve({ width: image.naturalWidth, height: image.naturalHeight });
    }, { once: true });
    image.addEventListener("error", () => {
      reject(new Error("圖像無法安全解碼，請改用有效的PNG、JPEG或WebP。"));
    }, { once: true });
    image.src = objectUrl;
  });
}

function setPersonalImageStep(stepName) {
  const steps = ["select", "adjust", "review"];
  const currentIndex = steps.indexOf(stepName);
  steps.forEach((name, index) => {
    const item = document.querySelector(`#image-step-${name}`);
    item.classList.toggle("is-current", index === currentIndex);
    item.classList.toggle("is-complete", index < currentIndex);
  });
}

function personalImagePositionLabel(value) {
  if (value < 40) return "偏上";
  if (value > 60) return "偏下";
  return "置中";
}

function createPersonalImageCandidate(parameters, fileSummary) {
  return Object.freeze({
    parameters: Object.freeze({ ...parameters }),
    fileSummary,
    summary:
      `${fileSummary}｜圖片大小 ${parameters.display_zoom_percent}%`
      + `｜上下位置 ${parameters.display_position_y_percent}%`,
  });
}

function updatePersonalImageAdjustment(parameterName, value) {
  if (!personalImageCandidate) return;
  personalImageCandidate = createPersonalImageCandidate(
    {
      ...personalImageCandidate.parameters,
      [parameterName]: Number(value),
    },
    personalImageCandidate.fileSummary,
  );
  document.querySelector("#xiaoj-image-file-state").textContent =
    personalImageCandidate.summary;
}

function resetPersonalImagePreview(message = "尚未選擇新圖像") {
  if (personalImagePreviewUrl) {
    URL.revokeObjectURL(personalImagePreviewUrl);
  }
  personalImagePreviewUrl = null;
  personalImageCandidate = null;
  const preview = document.querySelector("#personal-xiaoj-image-preview");
  preview.src = "./assets/xiaoj-white-haired-service-worker.png";
  preview.alt = "目前使用的白髮少女小J圖像預覽";
  preview.style.setProperty("--image-zoom", "1");
  preview.style.setProperty("--image-position-y", "50%");
  document.querySelector("#xiaoj-image-preview-state").textContent = "目前使用：白髮少女小J原設計";
  document.querySelector("#xiaoj-image-file-state").textContent = message;
  document.querySelector("#xiaoj-image-technical-state").textContent = "尚未產生圖片摘要。";
  document.querySelector("#xiaoj-image-input").value = "";
  document.querySelector("#xiaoj-image-zoom").value = "100";
  document.querySelector("#xiaoj-image-position").value = "50";
  document.querySelector("#xiaoj-image-zoom-value").textContent = "100%";
  document.querySelector("#xiaoj-image-position-value").textContent = "置中";
  document.querySelector("#xiaoj-image-adjustments").disabled = true;
  document.querySelector("#create-image-review").disabled = true;
  document.querySelector("#cancel-image-preview").disabled = true;
  setPersonalImageStep("select");
}

async function preparePersonalImageCandidate(file) {
  const policy = PRODUCT_CONTRACT.personalization.xiaojImage;
  if (!file) {
    resetPersonalImagePreview();
    return;
  }
  if (!policy.allowedMimeTypes.includes(file.type)) {
    throw new Error("只接受PNG、JPEG或WebP圖像；不接受SVG或其他可執行格式。");
  }
  if (file.size <= 0 || file.size > policy.maximumBytes) {
    throw new Error("圖像必須小於或等於5 MB。");
  }

  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  if (!hasExpectedImageSignature(bytes, file.type)) {
    throw new Error("檔案內容與圖像格式不一致，已安全阻擋。");
  }

  const objectUrl = URL.createObjectURL(file);
  try {
    const dimensions = await readImageDimensions(objectUrl);
    if (
      dimensions.width < 256
      || dimensions.height < 256
      || dimensions.width > 4096
      || dimensions.height > 4096
    ) {
      throw new Error("圖像長寬需介於256至4096像素。");
    }
    const imageSha256 = await sha256Bytes(buffer);
    if (personalImagePreviewUrl) {
      URL.revokeObjectURL(personalImagePreviewUrl);
    }
    personalImagePreviewUrl = objectUrl;
    const fileSummary =
      `${file.type.replace("image/", "").toUpperCase()}`
      + `｜${dimensions.width}×${dimensions.height}`
      + `｜${humanFileSize(file.size)}`
      + `｜SHA-256 ${imageSha256.slice(0, 12)}…`;
    personalImageCandidate = createPersonalImageCandidate(
      {
        owner_scope: policy.ownerScope,
        approval_policy: policy.approval,
        predecessor_asset_ref: CURRENT_XIAOJ_IMAGE.assetRef,
        predecessor_asset_sha256: CURRENT_XIAOJ_IMAGE.sha256,
        candidate_image_sha256: imageSha256,
        mime_type: file.type,
        byte_size: file.size,
        pixel_width: dimensions.width,
        pixel_height: dimensions.height,
        display_zoom_percent: 100,
        display_position_y_percent: 50,
        external_upload: false,
        persistent_write: false,
      },
      fileSummary,
    );
    const preview = document.querySelector("#personal-xiaoj-image-preview");
    preview.src = objectUrl;
    preview.alt = "本人選擇的新小J圖像，本機預覽尚未套用";
    preview.style.setProperty("--image-zoom", "1");
    preview.style.setProperty("--image-position-y", "50%");
    document.querySelector("#xiaoj-image-preview-state").textContent = "本機預覽｜尚未上傳、尚未套用";
    document.querySelector("#xiaoj-image-file-state").textContent = personalImageCandidate.summary;
    document.querySelector("#xiaoj-image-technical-state").textContent =
      `${file.type}｜${dimensions.width}×${dimensions.height} px`
      + `｜${humanFileSize(file.size)}｜SHA-256 ${imageSha256}`;
    document.querySelector("#xiaoj-image-adjustments").disabled = false;
    document.querySelector("#create-image-review").disabled = false;
    document.querySelector("#cancel-image-preview").disabled = false;
    setPersonalImageStep("adjust");
  } catch (error) {
    URL.revokeObjectURL(objectUrl);
    throw error;
  }
}

function personalImageReviewTemplate(candidate) {
  return Object.freeze({
    sceneRef: "RESIDENT",
    purpose: "將所選圖像設為本人專屬小J介面的候選",
    feature: "本人專屬小J圖像",
    actionType: "MEMBER_PERSONAL_XIAOJ_IMAGE_WRITE_CANDIDATE",
    capabilityRef: "candidate://wuchang-xiaoj/member-self/image-personalization",
    targetRefs: [
      "member-ui://current-member/xiaoj/image",
      "logical://taiji01/odoo/member-ui-projection",
    ],
    scopeRefs: [
      "scope://member-self/same-root-only",
      "scope://member-self/same-session-only",
    ],
    resourceRefs: [
      "authority://odoo",
      "governance://total-field",
      "asset://member-selected-image-hash-only",
    ],
    parameters: candidate.parameters,
    parameterSummary: candidate.summary,
    targetLabel: "僅限目前會員本人的小J介面",
    expectedResult: "建立一張與本人、同一session及圖像SHA-256綁定的更換候選",
    changes: "正式核准並通過權威驗證後，只能改變本人小J介面的圖像引用",
    unchanged: "不改共用小J原圖、不改其他會員、角色、Seat、權限、Odoo流程或正式資料",
    maximumEffect: "最多新增一個本會員專屬圖像引用；舊引用保留於可稽核歷程",
    risk: "圖像可能含個人資料；參數、會員、session或圖像雜湊不一致時必須阻擋",
    rollback: "恢復前一個已驗證圖像引用；候選模式只需取消本機預覽",
    flags: { money: false, memberData: true, externalSend: false, deletion: false },
  });
}

function setCurrentView(viewName) {
  const target = document.querySelector(`[data-view="${viewName}"]`);
  if (!target) return;
  currentView = viewName;
  document.querySelectorAll(".app-view").forEach((view) => {
    const active = view === target;
    view.hidden = !active;
    view.classList.toggle("is-active", active);
  });
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    const active = button.dataset.viewTarget === viewName;
    button.classList.toggle("is-active", active);
    if (button.matches(".nav-link, .mobile-nav button")) {
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    }
  });
  globalThis.history.replaceState(null, "", `#${viewName}`);
  target.querySelector("h1, h2")?.focus?.({ preventScroll: true });
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
}

function updateReviewCount() {
  const pending = [...actionStore.values()].filter((item) => item.state === "PENDING").length;
  const count = document.querySelector("#review-count");
  count.textContent = String(pending);
  count.setAttribute("aria-label", `${pending}筆待確認`);
}

function showToast(message, tone = "info") {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.dataset.tone = tone;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.hidden = true;
  }, 4200);
}

function createReviewField(label, value) {
  const row = element("div", "review-field");
  row.append(element("dt", "", label), element("dd", "", value));
  return row;
}

function createFlags(flags) {
  const labels = [
    ["money", "涉及金錢"],
    ["memberData", "涉及會員資料"],
    ["externalSend", "外部傳送"],
    ["deletion", "涉及刪除"],
  ];
  const container = element("div", "risk-flags");
  labels.forEach(([key, label]) => {
    const badge = element("span", flags[key] ? "flag flag-alert" : "flag", `${flags[key] ? "是" : "否"}｜${label}`);
    container.append(badge);
  });
  return container;
}

function renderReviewCard(record) {
  const list = document.querySelector("#review-list");
  document.querySelector("#review-empty")?.remove();
  const card = element("article", "review-card");
  card.dataset.actionId = record.packet.action_id;

  const header = element("header", "review-card-header");
  const titleBlock = element("div");
  titleBlock.append(
    element("p", "panel-label", record.template.feature),
    element("h2", "", record.template.purpose),
  );
  const status = element("span", "review-state", "等待您決定");
  header.append(titleBlock, status);

  const summary = element("dl", "review-summary");
  summary.append(
    createReviewField("場景", sceneLabel(record.packet.scene_ref)),
    createReviewField("將使用的功能", record.template.feature),
    createReviewField("執行對象", record.template.targetLabel || "Odoo權威流程（目前未連線）"),
    createReviewField("預計結果", record.template.expectedResult),
    createReviewField("會改變什麼", record.template.changes),
    createReviewField("不會改變什麼", record.template.unchanged),
  );

  const expiry = new Date(record.packet.expires_at).toLocaleString("zh-TW", {
    hour12: false,
    dateStyle: "short",
    timeStyle: "short",
  });
  const meta = element("div", "review-meta");
  meta.append(
    element("span", "", `有效期限｜${expiry}`),
    element("code", "", `操作雜湊｜${record.packet.action_hash.slice(0, 12)}…`),
  );

  const actions = element("div", "review-actions");
  const approve = element("button", "button button-primary", "批准執行");
  approve.type = "button";
  approve.dataset.reviewAction = "approve";
  const reject = element("button", "button button-danger", "拒絕");
  reject.type = "button";
  reject.dataset.reviewAction = "reject";
  const details = element("button", "button button-quiet", "查看詳細內容");
  details.type = "button";
  details.dataset.reviewAction = "details";
  actions.append(approve, reject, details);

  card.append(header, createFlags(record.template.flags), summary, meta, actions);
  list.prepend(card);
}

function sceneLabel(sceneRef) {
  return {
    RESIDENT: "居民服務",
    BUSINESS_CLOUD: "商業雲",
    PROPERTY_CLOUD: "物業雲",
  }[sceneRef] || sceneRef;
}

function appendDetail(dialogContent, label, value) {
  const row = element("div", "dialog-detail");
  row.append(element("strong", "", label), element("p", "", value));
  dialogContent.append(row);
}

function openReviewDetails(record) {
  const dialog = document.querySelector("#review-dialog");
  const content = document.querySelector("#dialog-content");
  content.replaceChildren();
  content.append(
    element("p", "section-kicker", "Action Review Packet"),
    element("h2", "", record.template.purpose),
  );
  content.querySelector("h2").id = "dialog-title";
  appendDetail(content, "小J理解的目的", record.template.purpose);
  appendDetail(content, "將使用的功能", record.template.feature);
  appendDetail(content, "場景", sceneLabel(record.packet.scene_ref));
  appendDetail(content, "執行對象", record.packet.target_refs.join("、"));
  appendDetail(content, "精確參數摘要", record.template.parameterSummary);
  appendDetail(content, "預計結果", record.template.expectedResult);
  appendDetail(content, "最大影響", record.template.maximumEffect);
  appendDetail(content, "風險", record.template.risk);
  appendDetail(content, "回滾方式", record.template.rollback);
  appendDetail(content, "Action hash", record.packet.action_hash);
  appendDetail(content, "Parameters SHA-256", record.packet.parameters_sha256);
  dialog.showModal();
}

async function createReviewCandidateFromTemplate(template, templateId) {
  if (!template) return;
  const packet = await createActionReviewPacket({
    session: SYNTHETIC_SESSION,
    sceneRef: template.sceneRef,
    capabilityRef: template.capabilityRef || "candidate://wuchang-xiaoj/create-action-review-packet",
    actionType: template.actionType,
    targetRefs: template.targetRefs,
    parameters: template.parameters,
    purposeRef: `purpose://wuchang-xiaoj/${templateId}`,
    scopeRefs: template.scopeRefs || [`scope://${template.sceneRef.toLowerCase()}/candidate-only`],
    resourceRefs: template.resourceRefs || ["authority://odoo", "governance://total-field"],
    effectClass: template.actionType,
    expectedResult: template.expectedResult,
    maximumEffect: template.maximumEffect,
    riskSummary: template.risk,
    rollbackRef: "candidate://rollback/zero-live-effect",
  });
  const projection = buildOdooProjectionCandidate({
    actionType: packet.action_type,
    targetRefs: packet.target_refs,
    parametersSha256: packet.parameters_sha256,
  });
  const record = { packet, template, projection, state: "PENDING", receipt: null };
  actionStore.set(packet.action_id, record);
  renderReviewCard(record);
  updateReviewCount();
  setCurrentView("review");
  showToast("候選已建立。請先查看完整效果，再決定是否批准。");
}

async function createReviewCandidate(templateId) {
  return createReviewCandidateFromTemplate(ACTION_TEMPLATES[templateId], templateId);
}

async function handleReviewAction(button) {
  const card = button.closest(".review-card");
  const record = actionStore.get(card?.dataset.actionId);
  if (!record) return;
  if (button.dataset.reviewAction === "details") {
    openReviewDetails(record);
    return;
  }
  try {
    if (button.dataset.reviewAction === "approve") {
      record.receipt = await approveActionReview({
        packet: record.packet,
        parameters: record.template.parameters,
        currentSession: SYNTHETIC_SESSION,
        currentSceneRef: record.packet.scene_ref,
      });
      record.state = "APPROVED_DRY_RUN";
      card.querySelector(".review-state").textContent = "已批准｜正式執行封鎖";
      card.querySelector(".review-state").classList.add("approved");
      card.querySelectorAll(".review-actions button").forEach((item) => {
        item.disabled = true;
      });
      if (record.template.actionType === "MEMBER_PERSONAL_XIAOJ_IMAGE_WRITE_CANDIDATE") {
        document.querySelector("#xiaoj-image-preview-state").textContent =
          "候選已批准｜隔離模式仍未上傳或套用";
      }
      showToast("批准回執已建立；候選模式不會執行、寫入或外傳。", "success");
    }
    if (button.dataset.reviewAction === "reject") {
      record.receipt = await rejectActionReview({
        packet: record.packet,
        currentSession: SYNTHETIC_SESSION,
      });
      record.state = "REJECTED";
      card.querySelector(".review-state").textContent = "已拒絕｜零副作用";
      card.querySelector(".review-state").classList.add("rejected");
      card.querySelectorAll(".review-actions button").forEach((item) => {
        item.disabled = true;
      });
      if (record.template.actionType === "MEMBER_PERSONAL_XIAOJ_IMAGE_WRITE_CANDIDATE") {
        resetPersonalImagePreview("圖像候選已拒絕，已恢復目前圖像。");
      }
      showToast("已拒絕。沒有執行任何操作。", "success");
    }
  } catch (error) {
    showToast(`已安全阻擋：${error.message}`, "error");
  }
  updateReviewCount();
}

function appendChatMessage(role, title, body, action) {
  const list = document.querySelector("#message-list");
  const article = element("article", `message ${role === "user" ? "user-message" : "assistant-message"}`);
  const avatar = element("span", "message-avatar", role === "user" ? "我" : "J");
  avatar.setAttribute("aria-hidden", "true");
  const content = element("div");
  content.append(element("strong", "", title), element("p", "", body));
  if (action) {
    const button = element("button", "button button-quiet button-small", action.nextLabel);
    button.type = "button";
    button.dataset.viewTarget = action.nextView;
    button.addEventListener("click", () => setCurrentView(action.nextView));
    content.append(button);
  }
  article.append(avatar, content);
  list.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function handleXiaojSubmit(value) {
  const text = String(value || "").trim();
  if (!text) {
    showToast("請先說明您想完成的事。", "error");
    return;
  }
  appendChatMessage("user", "您", text);
  const result = getLocalXiaojCandidate(text);
  window.setTimeout(() => {
    appendChatMessage("assistant", result.title, result.body, result);
  }, 180);
}

document.addEventListener("click", (event) => {
  const viewTarget = event.target.closest("[data-view-target]");
  if (viewTarget) {
    event.preventDefault();
    setCurrentView(viewTarget.dataset.viewTarget);
    return;
  }
  const sceneTarget = event.target.closest("[data-scene-target]");
  if (sceneTarget) {
    const scene = sceneTarget.dataset.sceneTarget;
    document.querySelectorAll("[data-scene-target]").forEach((tab) => {
      const active = tab === sceneTarget;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
    });
    document.querySelectorAll("[data-scene]").forEach((panel) => {
      const active = panel.dataset.scene === scene;
      panel.hidden = !active;
      panel.classList.toggle("is-active", active);
    });
    return;
  }
  const actionButton = event.target.closest("[data-action-template]");
  if (actionButton) {
    createReviewCandidate(actionButton.dataset.actionTemplate);
    return;
  }
  const reviewButton = event.target.closest("[data-review-action]");
  if (reviewButton) {
    handleReviewAction(reviewButton);
    return;
  }
  const promptButton = event.target.closest("[data-prompt-value]");
  if (promptButton) {
    const input = document.querySelector("#xiaoj-input");
    input.value = promptButton.dataset.promptValue;
    input.focus();
    return;
  }
  const xiaojPrompt = event.target.closest("[data-xiaoj-prompt]");
  if (xiaojPrompt) {
    setCurrentView("xiaoj");
    document.querySelector("#xiaoj-input").value = xiaojPrompt.dataset.xiaojPrompt;
    document.querySelector("#xiaoj-input").focus();
  }
});

document.querySelector("#xiaoj-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.querySelector("#xiaoj-input");
  handleXiaojSubmit(input.value);
  input.value = "";
});

document.querySelector("#xiaoj-image-input").addEventListener("change", async (event) => {
  try {
    await preparePersonalImageCandidate(event.target.files?.[0]);
  } catch (error) {
    resetPersonalImagePreview(`已安全阻擋：${error.message}`);
    showToast(`已安全阻擋：${error.message}`, "error");
  }
});

document.querySelector("#xiaoj-image-zoom").addEventListener("input", (event) => {
  const value = Number(event.target.value);
  document.querySelector("#personal-xiaoj-image-preview")
    .style.setProperty("--image-zoom", String(value / 100));
  document.querySelector("#xiaoj-image-zoom-value").textContent = `${value}%`;
  updatePersonalImageAdjustment("display_zoom_percent", value);
});

document.querySelector("#xiaoj-image-position").addEventListener("input", (event) => {
  const value = Number(event.target.value);
  document.querySelector("#personal-xiaoj-image-preview")
    .style.setProperty("--image-position-y", `${value}%`);
  document.querySelector("#xiaoj-image-position-value").textContent =
    personalImagePositionLabel(value);
  updatePersonalImageAdjustment("display_position_y_percent", value);
});

document.querySelector("#cancel-image-preview").addEventListener("click", () => {
  resetPersonalImagePreview("已取消預覽，沒有建立或套用變更。");
  showToast("已取消圖像預覽。沒有任何副作用。", "success");
});

document.querySelector("#xiaoj-image-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!personalImageCandidate) {
    showToast("請先選擇並檢查新圖像。", "error");
    return;
  }
  try {
    await createReviewCandidateFromTemplate(
      personalImageReviewTemplate(personalImageCandidate),
      "member-personal-xiaoj-image",
    );
    document.querySelector("#create-image-review").disabled = true;
    document.querySelector("#xiaoj-image-preview-state").textContent =
      "待本人確認｜圖像仍只在本機預覽";
    setPersonalImageStep("review");
  } catch (error) {
    showToast(`已安全阻擋：${error.message}`, "error");
  }
});

window.addEventListener("hashchange", () => {
  const requested = window.location.hash.slice(1);
  if (requested && requested !== currentView && document.querySelector(`[data-view="${requested}"]`)) {
    setCurrentView(requested);
  }
});

document.documentElement.dataset.productMode = PRODUCT_CONTRACT.mode;
const initialView = window.location.hash.slice(1);
if (initialView && document.querySelector(`[data-view="${initialView}"]`)) {
  setCurrentView(initialView);
}
