const SAFE_ACTIONS = [
  "open_sidebar_ref",
  "read_text_ref",
  "write_draft_ref"
];

const $ = (id) => document.getElementById(id);

function stableStringify(value) {
  if (Array.isArray(value)) return "[" + value.map(stableStringify).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key.normalize("NFC")) + ":" + stableStringify(value[key])).join(",") + "}";
  }
  if (typeof value === "string") return JSON.stringify(value.normalize("NFC"));
  return JSON.stringify(value);
}

async function sha256Hex(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function pseudoHash64(text) {
  let h1 = 0x811c9dc5;
  let h2 = 0x45d9f3b;
  let h3 = 0x27d4eb2d;
  let h4 = 0x165667b1;
  for (let i = 0; i < text.length; i += 1) {
    const c = text.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 16777619);
    h2 = Math.imul(h2 + c, 1597334677);
    h3 = Math.imul(h3 ^ (c + i), 2246822519);
    h4 = Math.imul(h4 + (c << (i % 8)), 3266489917);
  }
  return [h1, h2, h3, h4, h1 ^ h3, h2 ^ h4, h1 + h4, h2 + h3]
    .map((n) => (n >>> 0).toString(16).padStart(8, "0"))
    .join("")
    .slice(0, 64);
}

function ref(prefix, value) {
  return `${prefix}:${pseudoHash64(String(value || "")).slice(0, 16)}`;
}

function detectBoundaryHits(text) {
  const hits = [];
  [
    ["phone_like", /(?:\+?886[- ]?)?09\d{2}[- ]?\d{3}[- ]?\d{3}/],
    ["email_like", /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/],
    ["raw_secret", /(sk-[A-Za-z0-9_-]{10,}|api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|secret\s*[:=]\s*\S+)/i],
    ["raw_storage", /(cookie|localStorage|sessionStorage|bearer\s+)/i],
    ["payment_term", /(付款|刷卡|扣款|payment capture|capture payment)/i],
    ["member_plaintext_term", /(會員明文|完整姓名|完整地址|身分證|身份證)/]
  ].forEach(([name, pattern]) => {
    if (pattern.test(text)) hits.push(name);
  });
  return Array.from(new Set(hits)).sort();
}

async function buildPacket() {
  const intent = $("intentText").value.trim() || "會員日常協力";
  const actionType = $("actionType").value;
  const draftText = $("draftText").value.trim();
  const humanConfirmed = $("humanConfirmed").checked;
  const hits = detectBoundaryHits(`${intent}\n${draftText}`);
  const allowedByPanel = SAFE_ACTIONS.includes(actionType);
  const riskLevel = hits.length || !allowedByPanel ? "blocked" : (actionType === "write_draft_ref" ? "medium" : "low");
  const transactionIntent = actionType === "write_draft_ref" ? "service_request" : (riskLevel === "blocked" ? "governance_review" : "browse");
  const packet = {
    packet_type: "xiaoj_8d_action_packet",
    D1_identity: {
      actor_ref: "actor_ref:member_browser_extension:active_member",
      actor_type: "member",
      device_ref: "device_ref:member_browser_extension:chrome_mv3",
      role: "member_role_ref",
      plaintext_identity_forbidden: true
    },
    D2_intent: {
      primary_intent: ref("intent_ref", intent),
      secondary_intent: "redacted_ref:browser_extension_sidepanel",
      transaction_intent: transactionIntent,
      risk_level: riskLevel
    },
    D3_state: {
      session_state: "active",
      task_state: riskLevel === "blocked" ? "blocked" : "dry_run",
      browser_state: riskLevel === "blocked" ? "blocked" : "dry_run",
      order_state: "none",
      context_mode: "ref_only"
    },
    D4_topology: {
      channel: "browser_action_bus",
      site_ref: "site_ref:xiaoj_member_browser_extension",
      device_topology: "member_browser_extension_to_total_field",
      origin_scope: "member_owned"
    },
    D5_resource: {
      key_policy: "hybrid_ref_only",
      selected_key_ref: "key_ref:member_browser_extension:broker_managed_default",
      api_refs: ["api_ref:member_browser_extension:local_bridge"],
      model_tier: "small",
      cache_policy: "ref_cache_only",
      cost_policy: "budget_cap_ref"
    },
    D6_governance: {
      allowed_actions: SAFE_ACTIONS,
      forbidden_actions: [
        "submit_payment",
        "submit_order_without_human",
        "login_with_plaintext",
        "read_raw_cookie",
        "read_raw_local_storage",
        "write_database",
        "payment_capture",
        "service_restart",
        "deploy"
      ],
      no_plaintext_context: true,
      reconstruction_level: "L3_CANDIDATE",
      human_confirm_required: actionType === "write_draft_ref" || riskLevel === "blocked",
      staff_confirm_required: false
    },
    D7_verification: {
      redaction_check_required: true,
      leak_check_required: true,
      action_allowlist_required: true,
      response_verify_required: true,
      usage_log_required: true
    },
    D8_envelope: {
      packet_id: `PKT_BROWSER_${crypto.randomUUID().replaceAll("-", "")}`,
      packet_ref: ref("packet_ref", `${intent}:${Date.now()}`),
      trace_id: `TRACE_BROWSER_${crypto.randomUUID().replaceAll("-", "")}`,
      nonce: `nonce_ref:${crypto.randomUUID()}`,
      counter: 1,
      ttl_seconds: 300,
      created_at: new Date().toISOString(),
      schema_version: "8d.packet.v1",
      content_hash: "",
      content_sha256: "",
      hmac_ref: "hmac_ref:xiaoj_member_browser_extension:verifier_required",
      signature_ref: "signature_ref:xiaoj_member_browser_extension:verifier_required",
      replay_protection: true,
      authority_granted: false
    },
    browser_action: {
      action_ref: ref("action_ref", `${actionType}:${intent}`),
      action_type: actionType,
      target_ref: ref("target_ref", `${actionType}:active_tab`),
      params: {
        controller_ref: "controller_ref:xiaoj_member_browser_1b",
        intent_ref: ref("intent_ref", intent),
        safe_context_ref: "redacted_ref:active_tab_selection",
        member_preference_ref: "preference_ref:member:sidepanel_default",
        service_style_ref: "service_style_ref:community_xiaoj_warm_daily",
        behavior_info_ref: ref("behavior_ref", `${actionType}:${intent}`),
        cloud_compute_ref: "cloud_compute_ref:local_1b_first_extension_bridge",
        benefit_ref: "benefit_ref:community_ai_member_daily",
        quota_bucket_ref: "quota_bucket_ref:member_daily_fair_use",
        generative_transmission_ref: "gt_ref:w7tp_member_browser_extension_no_plaintext",
        return_packet_schema: "w7tp.cloud_candidate_return_packet.v1",
        cloud_candidate_only: true,
        human_confirmed: humanConfirmed,
        draft_ref: actionType === "write_draft_ref" ? ref("draft_ref", draftText) : "draft_ref:none",
        boundary_hits_ref: ref("risk_ref", hits.join(",") || "none"),
        candidate_only: true,
        requires_total_field_verify: true
      },
      dry_run: true,
      submit_forbidden: true
    }
  };
  const hashPacket = JSON.parse(JSON.stringify(packet));
  hashPacket.D8_envelope.content_hash = "";
  hashPacket.D8_envelope.content_sha256 = "";
  const contentSha256 = await sha256Hex(stableStringify(hashPacket));
  packet.D8_envelope.content_hash = contentSha256;
  packet.D8_envelope.content_sha256 = contentSha256;
  return packet;
}

async function runBridge() {
  const packet = await buildPacket();
  $("packetOut").textContent = JSON.stringify(packet, null, 2);
  const result = await chrome.runtime.sendMessage({
    type: "XIAOJ_NATIVE_GATEWAY_REQUEST",
    packet
  });
  $("resultOut").textContent = JSON.stringify(result, null, 2);
  $("decisionText").textContent = result && result.decision ? result.decision : "UNKNOWN";
  $("decisionText").className = result && result.ok ? "allowed" : "blocked";
}

$("runBtn").addEventListener("click", () => {
  runBridge().catch((error) => {
    $("resultOut").textContent = JSON.stringify({
      ok: false,
      decision: "BLOCK",
      reason: "sidepanel_exception",
      error_ref: ref("error_ref", String(error)),
      execution_allowed: false
    }, null, 2);
  });
});

buildPacket()
  .then((packet) => {
    $("packetOut").textContent = JSON.stringify(packet, null, 2);
  })
  .catch((error) => {
    $("packetOut").textContent = JSON.stringify({
      state: "HOLD",
      reason: "packet_hash_initialization_failed",
      error_ref: ref("error_ref", String(error))
    }, null, 2);
  });
