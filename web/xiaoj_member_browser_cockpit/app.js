const SAFE_ACTIONS = [
  "navigate_ref",
  "click_ref",
  "fill_ref",
  "select_ref",
  "read_text_ref",
  "screenshot_ref",
  "wait_ref",
  "extract_ref",
  "open_sidebar_ref",
  "close_sidebar_ref",
  "render_sidebar_ref",
  "read_context_ref",
  "write_draft_ref",
  "route_to_connector_ref",
  "broker_api_call_ref",
  "cache_lookup_ref",
  "read_menu_ref",
  "create_order_draft_ref",
  "queue_service_ref",
  "notify_staff_ref",
  "ask_human_confirm",
  "handoff_to_human"
];

const FORBIDDEN_ACTIONS = [
  "login_with_plaintext",
  "submit_payment",
  "submit_order_without_human",
  "read_raw_cookie",
  "read_raw_local_storage",
  "write_database",
  "router_change",
  "tailscale_change",
  "dns_change",
  "service_restart",
  "docker_restart",
  "systemctl_restart"
];

const state = {
  preference: "concise",
  packet: null,
  decision: null,
  cloudReturn: null
};

const $ = (id) => document.getElementById(id);

function stableStringify(value) {
  if (Array.isArray(value)) {
    return "[" + value.map(stableStringify).join(",") + "]";
  }
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map((key) => {
      return JSON.stringify(key) + ":" + stableStringify(value[key]);
    }).join(",") + "}";
  }
  return JSON.stringify(value);
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
  const parts = [h1, h2, h3, h4, h1 ^ h3, h2 ^ h4, h1 + h4, h2 + h3];
  return parts.map((n) => (n >>> 0).toString(16).padStart(8, "0")).join("").slice(0, 64);
}

function ref(prefix, value) {
  return `${prefix}:${pseudoHash64(String(value)).slice(0, 16)}`;
}

function uid(prefix) {
  const random = Math.floor(Math.random() * 0xffffffff).toString(16).padStart(8, "0");
  return `${prefix}_${pseudoHash64(`${Date.now()}:${random}`).slice(0, 24)}`;
}

function detectBoundaryHits(text) {
  const hits = [];
  const rules = [
    ["phone_like", /(?:\+?886[- ]?)?09\d{2}[- ]?\d{3}[- ]?\d{3}/],
    ["email_like", /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/],
    ["raw_secret", /(sk-[A-Za-z0-9_-]{10,}|api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|secret\s*[:=]\s*\S+)/i],
    ["raw_storage", /(cookie|localStorage|sessionStorage|bearer\s+)/i],
    ["member_plaintext_term", /(會員明文|完整姓名|完整地址|身分證|身份證)/],
    ["payment_term", /(直接付款|提交付款|自動扣款|刷卡號|payment capture|capture payment)/i]
  ];
  rules.forEach(([name, pattern]) => {
    if (pattern.test(text)) hits.push(name);
  });
  return Array.from(new Set(hits)).sort();
}

function chooseAction(intent, hits) {
  const lower = intent.toLowerCase();
  if (hits.length) return ["handoff_to_human", "governance_review", "blocked", "blocked"];
  if (/側邊欄|小J|打開/.test(intent)) return ["open_sidebar_ref", "browse", "low", "dry_run"];
  if (/翻譯|translate/.test(lower)) return ["read_text_ref", "browse", "low", "dry_run"];
  if (/摘要|summarize|解釋|explain/.test(lower)) return ["read_text_ref", "browse", "low", "dry_run"];
  if (/活動報名|報名活動|參加活動|志工報名|熱舞社報名|rsvp/i.test(intent) || (/(活動|志工|熱舞社|運動社團)/.test(intent) && /(報名|參加|rsvp)/i.test(intent))) return ["write_draft_ref", "activity_rsvp_candidate", "medium", "dry_run"];
  if (/填表|表單|草稿|draft|填寫/.test(lower)) return ["write_draft_ref", "service_request", "medium", "dry_run"];
  if (/菜單|menu|活動|公告|福利/.test(lower)) return ["cache_lookup_ref", "browse", "low", "dry_run"];
  if (/點|下單|訂單|order/.test(lower)) return ["create_order_draft_ref", "order_draft", "medium", "dry_run"];
  if (/notify|remind|提醒/.test(lower)) return ["notify_staff_ref", "service_request", "medium", "dry_run"];
  return ["read_context_ref", "browse", "low", "dry_run"];
}

function preferenceRef() {
  return `preference_ref:member:${state.preference}`;
}

function serviceStyleRef() {
  return `service_style_ref:${$("serviceStyle").value}`;
}

function cloudComputeRef() {
  return `cloud_compute_ref:${$("computeLane").value}`;
}

function buildActionPacket() {
  const intent = $("intentText").value.trim() || "會員日常協力";
  const contextRef = $("contextRef").value.trim() || "redacted_ref:none";
  const memberRef = $("memberRef").value.trim() || "actor_ref:member_browser_1b:demo_member";
  const keyRef = $("keyRef").value.trim() || "key_ref:member_browser_1b:broker_managed_default";
  const hits = detectBoundaryHits(`${intent}\n${contextRef}\n${memberRef}\n${keyRef}`);
  const [actionType, transactionIntent, riskLevel, taskState] = chooseAction(intent, hits);
  const behaviorRef = ref("behavior_ref", `${intent}:${actionType}:${state.preference}`);
  const humanConfirmRequired = riskLevel !== "low" || actionType === "create_order_draft_ref" || actionType === "handoff_to_human";
  const packet = {
    packet_type: "xiaoj_8d_action_packet",
    D1_identity: {
      actor_ref: memberRef,
      actor_type: "member",
      device_ref: "device_ref:member_browser_cockpit:pwa",
      role: "member_role_ref",
      plaintext_identity_forbidden: true
    },
    D2_intent: {
      primary_intent: ref("intent_ref", intent),
      secondary_intent: contextRef,
      transaction_intent: transactionIntent,
      risk_level: riskLevel
    },
    D3_state: {
      session_state: "active",
      task_state: taskState,
      browser_state: riskLevel === "blocked" ? "blocked" : "dry_run",
      order_state: actionType === "create_order_draft_ref" ? "draft" : (riskLevel === "blocked" ? "blocked" : "none"),
      context_mode: "ref_only"
    },
    D4_topology: {
      channel: "browser_action_bus",
      site_ref: "site_ref:community_xiaoj_member_browser_cockpit",
      device_topology: "member_browser_to_total_field",
      origin_scope: "member_owned"
    },
    D5_resource: {
      key_policy: "hybrid_ref_only",
      selected_key_ref: keyRef,
      api_refs: ["api_ref:member_browser_1b:local_controller"],
      model_tier: "small",
      cache_policy: "ref_cache_only",
      cost_policy: "budget_cap_ref"
    },
    D6_governance: {
      allowed_actions: SAFE_ACTIONS,
      forbidden_actions: FORBIDDEN_ACTIONS,
      no_plaintext_context: true,
      human_confirm_required: humanConfirmRequired,
      staff_confirm_required: actionType === "create_order_draft_ref" || actionType === "notify_staff_ref"
    },
    D7_verification: {
      redaction_check_required: true,
      leak_check_required: true,
      action_allowlist_required: true,
      response_verify_required: true,
      usage_log_required: true
    },
    D8_envelope: {
      packet_ref: ref("packet_ref", `${intent}:${Date.now()}`),
      nonce: ref("nonce_ref", `${Date.now()}:${Math.random()}`),
      counter: 1,
      ttl_seconds: 300,
      created_at: new Date().toISOString(),
      schema_version: "8d.packet.v1",
      content_hash: "",
      hmac_ref: "hmac_ref:xiaoj_member_browser_cockpit:verifier_required",
      signature_ref: "signature_ref:xiaoj_member_browser_cockpit:verifier_required",
      replay_protection: true
    },
    browser_action: {
      action_ref: ref("action_ref", `${actionType}:${intent}`),
      action_type: actionType,
      target_ref: ref("target_ref", `${intent}:${contextRef}`),
      params: {
        controller_ref: "controller_ref:xiaoj_member_browser_1b",
        intent_ref: ref("intent_ref", intent),
        safe_context_ref: contextRef,
        member_preference_ref: preferenceRef(),
        service_style_ref: serviceStyleRef(),
        behavior_info_ref: behaviorRef,
        cloud_compute_ref: cloudComputeRef(),
        benefit_ref: "benefit_ref:community_ai_member_daily",
        quota_bucket_ref: "quota_bucket_ref:member_daily_fair_use",
        public_activity_cache_ref: /活動|志工|熱舞社|運動社團/.test(intent) ? "public_activity_cache_ref:web/community_activities.json" : "public_activity_cache_ref:none",
        generative_transmission_ref: "gt_ref:w7tp_member_browser_no_plaintext",
        return_packet_schema: "w7tp.cloud_candidate_return_packet.v1",
        cloud_candidate_only: true,
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
  packet.D8_envelope.content_hash = pseudoHash64(stableStringify(hashPacket));
  state.packet = packet;
  state.decision = null;
  state.cloudReturn = null;
  renderAll();
}

function verifyPacket() {
  if (!state.packet) buildActionPacket();
  const packet = state.packet;
  const payload = stableStringify(packet);
  const hits = detectBoundaryHits(payload);
  const reasons = [];
  let decision = "ALLOW_CANDIDATE";
  if (hits.length) {
    decision = "BLOCK";
    reasons.push(`redaction_hits:${hits.join(",")}`);
  }
  if (!SAFE_ACTIONS.includes(packet.browser_action.action_type)) {
    decision = "BLOCK";
    reasons.push("action_not_allowlisted");
  }
  if (!packet.browser_action.dry_run || !packet.browser_action.submit_forbidden) {
    decision = "BLOCK";
    reasons.push("browser_action_not_dry_run");
  }
  if (!packet.browser_action.params.candidate_only || !packet.browser_action.params.requires_total_field_verify) {
    decision = "BLOCK";
    reasons.push("missing_candidate_or_total_field_gate");
  }
  if (packet.D2_intent.risk_level === "blocked") {
    decision = "BLOCK";
    reasons.push("risk_level_blocked");
  }
  if (packet.D6_governance.human_confirm_required && decision === "ALLOW_CANDIDATE") {
    decision = "HOLD";
    reasons.push("human_confirm_required");
  }
  if (!reasons.length) reasons.push("candidate_only_verified");
  state.decision = {
    verifier_ref: ref("verifier_ref", packet.D8_envelope.content_hash),
    decision,
    reasons,
    execution_allowed: false,
    candidate_only: true,
    member_plaintext_transferred: false,
    secret_transferred: false,
    checked_at: new Date().toISOString()
  };
  renderAll();
}

function buildCloudReturn() {
  if (!state.packet) buildActionPacket();
  if (!state.decision) verifyPacket();
  const packet = state.packet;
  const candidateId = uid("CAND");
  const jobId = uid("JOB");
  const candidatePayloadHash = pseudoHash64(stableStringify({
    action_type: packet.browser_action.action_type,
    behavior_info_ref: packet.browser_action.params.behavior_info_ref,
    decision: state.decision.decision
  }));
  const ret = {
    schema_version: "w7tp.cloud_candidate_return_packet.v1",
    packet_type: "CLOUD_CANDIDATE_RETURN_PACKET",
    return_packet_id: uid("RET"),
    task_id: uid("TASK"),
    job_id: jobId,
    source_packet_id: packet.D8_envelope.packet_ref.replace("packet_ref:", "PKT_"),
    source_packet_hash: packet.D8_envelope.content_hash,
    candidate_id: candidateId,
    candidate_payload_hash: candidatePayloadHash,
    candidate_only: true,
    must_not_execute: true,
    requires_total_field_verify: true,
    member_plaintext_transferred: false,
    secret_transferred: false,
    raw_audio_transferred: false,
    cloud_received_packet_only: true,
    cloud_provider_ref: "CLOUD_PROVIDER_REF:" + $("computeLane").value,
    d1_intent: {
      intent_ref: packet.browser_action.params.intent_ref,
      action_type_candidate: packet.browser_action.action_type
    },
    d2_state: {
      input_state_ref: ref("STATE_REF", packet.D8_envelope.content_hash),
      candidate_state: state.decision.decision
    },
    d3_coordinate: {
      source: "xiaoj_member_browser_cockpit",
      cloud_lane: $("computeLane").value,
      authority: "candidate_only",
      cloud_compute_ref: cloudComputeRef().replace("cloud_compute_ref:", "CLOUD_COMPUTE_REF:"),
      compute_provider_ref: "CLOUD_PROVIDER_REF:" + $("computeLane").value,
      compute_cost_bucket_ref: "COMPUTE_COST_BUCKET_REF:member_daily_fair_use"
    },
    d4_evidence: {
      source_packet_hash: packet.D8_envelope.content_hash,
      candidate_payload_hash: candidatePayloadHash,
      evidence_ref: ref("EVIDENCE_REF", candidatePayloadHash),
      behavior_info_ref: packet.browser_action.params.behavior_info_ref.replace("behavior_ref:", "BEHAVIOR_INFO_REF:"),
      action_trace_ref: ref("ACTION_TRACE_REF", `${packet.browser_action.action_type}:${state.decision.decision}`),
      member_tendency_ref: preferenceRef().replace("preference_ref:", "MEMBER_TENDENCY_REF:")
    },
    d5_execution: {
      execution_allowed: false,
      allowed_next_actions: ["present_candidate", "route_to_total_field_verifier", "hold_for_human_review"],
      forbidden_actions: ["db_write", "odoo_db_write", "production_db_write", "pos_write", "payment_capture", "deploy", "service_restart", "member_plaintext_read", "secret_read"],
      human_confirm_required: state.decision.decision !== "ALLOW_CANDIDATE"
    },
    d6_generative_transmission: {
      return_mode: "packetized_candidate_result",
      reconstruction_hint_ref: ref("RECONSTRUCT_REF", candidatePayloadHash),
      cloud_candidate_only: true,
      member_plaintext_transferred: false,
      secret_transferred: false
    },
    d7_risk: {
      risk_flags: state.decision.reasons,
      final_status_candidate: state.decision.decision === "BLOCK" ? "BLOCKED" : (state.decision.decision === "HOLD" ? "HOLD" : "CANDIDATE_READY"),
      hold_required: state.decision.decision === "HOLD",
      block_required: state.decision.decision === "BLOCK"
    },
    d8_envelope: {
      ttl_seconds: 300,
      nonce: ref("NONCE_REF", `${Date.now()}:${Math.random()}`),
      created_at: new Date().toISOString(),
      return_packet_hash: "",
      total_field_verifier_required: true,
      replay_protection: true
    }
  };
  const hashRet = JSON.parse(JSON.stringify(ret));
  hashRet.d8_envelope.return_packet_hash = "";
  ret.d8_envelope.return_packet_hash = pseudoHash64(stableStringify(hashRet));
  state.cloudReturn = ret;
  renderAll();
}

function renderDecision() {
  const list = $("decisionList");
  list.innerHTML = "";
  const decision = state.decision;
  if (!decision) {
    list.innerHTML = '<div class="decisionItem"><strong>WAIT</strong><span>尚未准駁</span></div>';
    $("decisionStatus").className = "badge warn";
    $("decisionStatus").textContent = "WAIT";
    $("verifierState").textContent = "待准駁";
    return;
  }
  const cls = decision.decision === "ALLOW_CANDIDATE" ? "allow" : (decision.decision === "HOLD" ? "hold" : "block");
  $("decisionStatus").className = `badge ${cls === "allow" ? "ok" : (cls === "hold" ? "warn" : "bad")}`;
  $("decisionStatus").textContent = decision.decision;
  $("verifierState").textContent = decision.decision;
  list.innerHTML = `
    <div class="decisionItem ${cls}">
      <strong>${decision.decision}</strong>
      <span>${decision.reasons.join(" / ")}</span>
    </div>
    <div class="decisionItem">
      <strong>execution_allowed=false</strong>
      <span>${decision.verifier_ref}</span>
    </div>
  `;
}

function renderActionQueue() {
  const queue = $("actionQueue");
  if (!state.packet) {
    queue.innerHTML = '<div class="actionItem"><strong>IDLE</strong><span>尚未有候選動作</span></div>';
    $("actionStatus").textContent = "IDLE";
    $("actionStatus").className = "badge neutral";
    return;
  }
  const packet = state.packet;
  const action = packet.browser_action;
  $("actionStatus").textContent = action.action_type;
  $("actionStatus").className = packet.D2_intent.risk_level === "blocked" ? "badge bad" : "badge ok";
  queue.innerHTML = `
    <div class="actionItem">
      <strong>${action.action_type}</strong>
      <span>${action.target_ref}</span>
    </div>
    <div class="actionItem">
      <strong>dry_run=true / submit_forbidden=true</strong>
      <span>${action.params.behavior_info_ref}</span>
    </div>
    <div class="actionItem">
      <strong>${action.params.member_preference_ref}</strong>
      <span>${action.params.service_style_ref}</span>
    </div>
  `;
}

function renderAll() {
  $("preferenceRef").textContent = preferenceRef();
  $("serviceStyleRef").textContent = serviceStyleRef();
  $("cloudComputeRef").textContent = cloudComputeRef();
  $("packetOut").textContent = state.packet ? JSON.stringify(state.packet, null, 2) : "尚未產生";
  $("cloudOut").textContent = state.cloudReturn ? JSON.stringify(state.cloudReturn, null, 2) : "候選尚未封包化";
  $("packetStatus").textContent = state.packet ? state.packet.D2_intent.risk_level.toUpperCase() : "WAIT";
  $("packetStatus").className = state.packet && state.packet.D2_intent.risk_level === "blocked" ? "badge bad" : (state.packet ? "badge ok" : "badge warn");
  $("cloudState").textContent = state.cloudReturn ? "已封包化" : "未呼叫";
  $("plainState").textContent = "無明文外送";
  renderDecision();
  renderActionQueue();
}

function clearAll() {
  state.packet = null;
  state.decision = null;
  state.cloudReturn = null;
  $("intentText").value = "";
  renderAll();
}

function bindEvents() {
  $("packetBtn").addEventListener("click", buildActionPacket);
  $("verifyBtn").addEventListener("click", verifyPacket);
  $("cloudBtn").addEventListener("click", buildCloudReturn);
  $("clearBtn").addEventListener("click", clearAll);
  $("serviceStyle").addEventListener("change", renderAll);
  $("computeLane").addEventListener("change", renderAll);
  document.querySelectorAll("#preferenceButtons button").forEach((button) => {
    button.addEventListener("click", () => {
      state.preference = button.dataset.pref;
      document.querySelectorAll("#preferenceButtons button").forEach((b) => b.classList.toggle("active", b === button));
      renderAll();
    });
  });
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}

bindEvents();
buildActionPacket();
