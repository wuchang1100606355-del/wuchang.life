const EXTENSION_ALLOWED_ACTIONS = new Set([
  "open_sidebar_ref",
  "read_text_ref",
  "write_draft_ref"
]);

const EXTENSION_BLOCKED_ACTIONS = new Set([
  "click_ref",
  "fill_ref",
  "select_ref",
  "screenshot_ref",
  "extract_ref",
  "create_order_draft_ref",
  "submit_payment",
  "submit_order_without_human",
  "login_with_plaintext",
  "read_raw_cookie",
  "read_raw_local_storage",
  "write_database",
  "payment_capture",
  "service_restart",
  "deploy"
]);

const NATIVE_HOST_NAME = "tw.taiji.xiaoj_member_browser_gateway";

function hashRef(prefix, value) {
  const text = String(value || "");
  let h1 = 0x811c9dc5;
  let h2 = 0x45d9f3b;
  for (let i = 0; i < text.length; i += 1) {
    const c = text.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 16777619);
    h2 = Math.imul(h2 + c, 1597334677);
  }
  const digest = [(h1 >>> 0), (h2 >>> 0), ((h1 ^ h2) >>> 0), ((h1 + h2) >>> 0)]
    .map((n) => n.toString(16).padStart(8, "0"))
    .join("")
    .slice(0, 16);
  return `${prefix}:${digest}`;
}

function blocked(reason, detail = {}) {
  return {
    ok: false,
    decision: "BLOCK",
    reason,
    execution_allowed: false,
    candidate_only: true,
    requires_total_field_verify: true,
    member_plaintext_transferred: false,
    secret_transferred: false,
    ...detail
  };
}

function allowed(detail = {}) {
  return {
    ok: true,
    decision: "ALLOW_LOCAL_MINIMUM_PRIVILEGE",
    execution_allowed: false,
    candidate_only: true,
    requires_total_field_verify: true,
    member_plaintext_transferred: false,
    secret_transferred: false,
    ...detail
  };
}

function validatePacket(packet) {
  if (!packet || typeof packet !== "object") return blocked("packet_not_object");
  if (packet.packet_type !== "xiaoj_8d_action_packet") return blocked("packet_type_not_supported");
  const action = packet.browser_action || {};
  const params = action.params || {};
  if (action.dry_run !== true) return blocked("dry_run_required");
  if (action.submit_forbidden !== true) return blocked("submit_forbidden_required");
  if (params.candidate_only !== true) return blocked("candidate_only_required");
  if (params.requires_total_field_verify !== true) return blocked("total_field_verify_required");
  if (packet.D6_governance && packet.D6_governance.no_plaintext_context !== true) {
    return blocked("no_plaintext_context_required");
  }
  if (EXTENSION_BLOCKED_ACTIONS.has(action.action_type)) {
    return blocked("action_blocked_by_extension_policy", { action_type: action.action_type });
  }
  if (!EXTENSION_ALLOWED_ACTIONS.has(action.action_type)) {
    return blocked("action_not_allowed_by_extension_policy", { action_type: action.action_type });
  }
  return allowed({ action_type: action.action_type });
}

function buildBridgeReturnPacket(packet, result) {
  const action = packet && packet.browser_action ? packet.browser_action : {};
  const params = action.params || {};
  const payload = {
    schema_version: "xiaoj.browser_bridge_return_packet.v1",
    packet_type: "BROWSER_BRIDGE_RETURN_PACKET",
    candidate_only: true,
    must_not_execute: true,
    requires_total_field_verify: true,
    member_plaintext_transferred: false,
    secret_transferred: false,
    raw_browser_page_transferred: false,
    raw_text_returned: false,
    D1_identity: {
      actor_ref: packet && packet.D1_identity ? packet.D1_identity.actor_ref : "actor_ref:unknown",
      device_ref: "device_ref:member_browser_extension:chrome_mv3",
      plaintext_identity_forbidden: true
    },
    D2_intent: {
      intent_ref: params.intent_ref || "intent_ref:missing",
      action_type_candidate: action.action_type || "unknown",
      bridge_decision: result.decision || "UNKNOWN"
    },
    D3_state: {
      browser_result_ref: result.browser_result_ref || hashRef("browser_result_ref", result.reason || "none"),
      execution_allowed: false,
      dry_run: true,
      submit_forbidden: true
    },
    D4_evidence: {
      behavior_info_ref: params.behavior_info_ref || "behavior_ref:missing",
      action_trace_ref: hashRef("action_trace_ref", `${action.action_type || "unknown"}:${result.decision || "UNKNOWN"}`),
      selected_text_ref: result.result && result.result.selected_text_ref ? result.result.selected_text_ref : "selected_text_ref:none",
      draft_ref: params.draft_ref || "draft_ref:none"
    },
    D5_execution: {
      execution_allowed: false,
      allowed_next_actions: ["present_candidate", "route_to_total_field_verifier", "ask_member_confirm"],
      forbidden_actions: Array.from(EXTENSION_BLOCKED_ACTIONS),
      human_confirm_required: Boolean(params.human_confirmed !== true && action.action_type === "write_draft_ref")
    },
    D6_generative_transmission: {
      return_mode: "browser_bridge_packetized_candidate_result",
      cloud_compute_ref: params.cloud_compute_ref || "cloud_compute_ref:missing",
      reconstruction_hint_ref: hashRef("reconstruct_ref", JSON.stringify(result)),
      cloud_candidate_only: true,
      member_plaintext_transferred: false,
      secret_transferred: false
    },
    D7_risk: {
      bridge_ok: Boolean(result.ok),
      decision: result.decision || "UNKNOWN",
      reason_ref: hashRef("reason_ref", result.reason || "none")
    },
    D8_envelope: {
      ttl_seconds: 300,
      nonce: hashRef("nonce_ref", `${Date.now()}:${Math.random()}`),
      created_at: new Date().toISOString(),
      return_packet_hash: "",
      total_field_verifier_required: true,
      replay_protection: true
    }
  };
  payload.D8_envelope.return_packet_hash = hashRef("return_packet_hash", JSON.stringify(payload));
  return payload;
}

function attachBridgeReturn(packet, result) {
  if (!packet || typeof packet !== "object") return result;
  return {
    ...result,
    browser_bridge_return_packet: buildBridgeReturnPacket(packet, result)
  };
}

function nativeGatewayPayload(message) {
  const packet = message.packet || {};
  const action = packet.browser_action || {};
  const params = action.params || {};
  return {
    type: "XIAOJ_NATIVE_GATEWAY_REQUEST",
    intent: message.intent || params.intent_ref || "會員日常協力",
    safe_context_ref: params.safe_context_ref || "redacted_ref:extension_native_gateway",
    selected_text: message.selectedText || "",
    local_draft_text: message.localDraftText || "",
    active_field_type: message.activeFieldType || "textarea",
    member_ref: packet.D1_identity && packet.D1_identity.actor_ref ? packet.D1_identity.actor_ref : "actor_ref:member_browser_extension:active_member",
    device_ref: "device_ref:member_browser_extension:chrome_mv3",
    key_ref: packet.D5_resource && packet.D5_resource.selected_key_ref ? packet.D5_resource.selected_key_ref : "key_ref:member_browser_extension:broker_default",
    api_ref: "api_ref:member_browser_extension:native_gateway",
    quota_ref: params.quota_bucket_ref || "quota_ref:member_browser_extension:daily",
    member_preference_ref: params.member_preference_ref || "preference_ref:member:sidepanel_default",
    service_style_ref: params.service_style_ref || "service_style_ref:community_xiaoj_warm_daily",
    behavior_info_ref: params.behavior_info_ref || "",
    cloud_compute_ref: params.cloud_compute_ref || "cloud_compute_ref:native_host_local_gateway",
    benefit_ref: params.benefit_ref || "benefit_ref:community_ai_member_daily"
  };
}

function callNativeGateway(message) {
  return new Promise((resolve) => {
    if (!chrome.runtime.sendNativeMessage) {
      resolve(blocked("native_messaging_api_unavailable", { native_gateway_available: false }));
      return;
    }
    chrome.runtime.sendNativeMessage(NATIVE_HOST_NAME, nativeGatewayPayload(message), (response) => {
      if (chrome.runtime.lastError) {
        resolve(blocked("native_gateway_unavailable", {
          native_gateway_available: false,
          error_ref: hashRef("native_error_ref", chrome.runtime.lastError.message || "unknown")
        }));
        return;
      }
      resolve({
        ok: Boolean(response && response.ok),
        decision: response && response.decision ? response.decision : "UNKNOWN",
        native_gateway_available: true,
        candidate_only: true,
        requires_total_field_verify: true,
        member_plaintext_transferred: false,
        secret_transferred: false,
        gateway_result: response ? response.gateway_result : null
      });
    });
  });
}

function getActiveTab() {
  return chrome.tabs.query({ active: true, currentWindow: true }).then((tabs) => tabs[0]);
}

function collectSelectedTextRef() {
  function inPage() {
    function localHash(prefix, value) {
      const text = String(value || "");
      let h1 = 0x811c9dc5;
      let h2 = 0x45d9f3b;
      for (let i = 0; i < text.length; i += 1) {
        const c = text.charCodeAt(i);
        h1 = Math.imul(h1 ^ c, 16777619);
        h2 = Math.imul(h2 + c, 1597334677);
      }
      const digest = [(h1 >>> 0), (h2 >>> 0), ((h1 ^ h2) >>> 0), ((h1 + h2) >>> 0)]
        .map((n) => n.toString(16).padStart(8, "0"))
        .join("")
        .slice(0, 16);
      return `${prefix}:${digest}`;
    }
    const selection = String(window.getSelection ? window.getSelection() : "");
    const visibleTitle = document.title || "";
    return {
      selected_text_ref: localHash("selected_text_ref", selection),
      selected_text_length: selection.length,
      page_title_ref: localHash("page_title_ref", visibleTitle),
      raw_text_returned: false
    };
  }
  return getActiveTab().then((tab) => {
    if (!tab || !tab.id) return blocked("no_active_tab");
    return chrome.scripting.executeScript({ target: { tabId: tab.id }, func: inPage }).then((frames) => {
      const result = frames && frames[0] ? frames[0].result : null;
      if (!result) return blocked("selection_ref_unavailable");
      return allowed({
        action_type: "read_text_ref",
        browser_result_ref: hashRef("browser_result_ref", JSON.stringify(result)),
        result
      });
    });
  });
}

function writeDraftWithConfirmation(packet, localDraftText) {
  const params = packet.browser_action.params || {};
  if (params.human_confirmed !== true) {
    return Promise.resolve(blocked("human_confirm_required_before_write_draft"));
  }
  const draftText = String(localDraftText || "");
  if (!draftText || draftText.length > 500) {
    return Promise.resolve(blocked("draft_preview_missing_or_too_long"));
  }
  if (/(sk-[A-Za-z0-9_-]{10,}|api[_-]?key|password|secret|09\d{2}[- ]?\d{3}[- ]?\d{3})/i.test(draftText)) {
    return Promise.resolve(blocked("draft_preview_sensitive_pattern"));
  }
  function inPage(text) {
    const active = document.activeElement;
    if (!active) return { filled: false, reason: "no_active_element" };
    const tag = String(active.tagName || "").toLowerCase();
    const type = String(active.getAttribute("type") || "").toLowerCase();
    const name = `${active.getAttribute("name") || ""} ${active.getAttribute("autocomplete") || ""}`.toLowerCase();
    const blockedTypes = new Set(["password", "email", "tel", "number", "date", "datetime-local", "month", "week", "time"]);
    if (blockedTypes.has(type)) return { filled: false, reason: "sensitive_input_type_blocked" };
    if (/(card|cc-|credit|password|otp|token|secret|address|phone|tel|email)/.test(name)) {
      return { filled: false, reason: "sensitive_input_name_blocked" };
    }
    if (tag === "textarea" || (tag === "input" && !blockedTypes.has(type))) {
      active.value = text;
      active.dispatchEvent(new Event("input", { bubbles: true }));
      return { filled: true, reason: "draft_written_to_editable_field" };
    }
    if (active.isContentEditable) {
      active.textContent = text;
      active.dispatchEvent(new Event("input", { bubbles: true }));
      return { filled: true, reason: "draft_written_to_contenteditable" };
    }
    return { filled: false, reason: "active_element_not_editable" };
  }
  return getActiveTab().then((tab) => {
    if (!tab || !tab.id) return blocked("no_active_tab");
    return chrome.scripting.executeScript({ target: { tabId: tab.id }, func: inPage, args: [draftText] }).then((frames) => {
      const result = frames && frames[0] ? frames[0].result : { filled: false, reason: "no_frame_result" };
      if (!result.filled) return blocked(result.reason || "draft_not_written");
      return allowed({
        action_type: "write_draft_ref",
        browser_result_ref: hashRef("browser_result_ref", JSON.stringify(result)),
        result: {
          filled: true,
          reason: result.reason,
          raw_draft_returned: false
        }
      });
    });
  });
}

async function executeCandidatePacket(packet, localDraftText = "") {
  const gate = validatePacket(packet);
  if (!gate.ok) return attachBridgeReturn(packet, gate);
  const actionType = packet.browser_action.action_type;
  if (actionType === "open_sidebar_ref") {
    const tab = await getActiveTab();
    if (tab && tab.windowId) await chrome.sidePanel.open({ windowId: tab.windowId });
    return attachBridgeReturn(packet, allowed({ action_type: actionType, side_panel_opened: true }));
  }
  if (actionType === "read_text_ref") return collectSelectedTextRef().then((result) => attachBridgeReturn(packet, result));
  if (actionType === "write_draft_ref") return writeDraftWithConfirmation(packet, localDraftText).then((result) => attachBridgeReturn(packet, result));
  return attachBridgeReturn(packet, blocked("unreachable_action_policy"));
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});

chrome.action.onClicked.addListener((tab) => {
  if (tab && tab.windowId) chrome.sidePanel.open({ windowId: tab.windowId }).catch(() => {});
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message) return false;
  if (message.type === "XIAOJ_NATIVE_GATEWAY_REQUEST") {
    callNativeGateway(message)
      .then(sendResponse)
      .catch((error) => sendResponse(blocked("native_gateway_exception", { error_ref: hashRef("error_ref", String(error)) })));
    return true;
  }
  if (message.type !== "XIAOJ_EXECUTE_CANDIDATE_ACTION") return false;
  executeCandidatePacket(message.packet, message.localDraftText || "")
    .then(sendResponse)
    .catch((error) => sendResponse(attachBridgeReturn(message.packet, blocked("bridge_exception", { error_ref: hashRef("error_ref", String(error)) }))));
  return true;
});
