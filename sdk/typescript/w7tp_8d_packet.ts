export type ActorType =
  | "member"
  | "staff"
  | "merchant"
  | "committee"
  | "system"
  | "browser_worker"
  | "counter_avatar"
  | "service";

export type RiskLevel = "low" | "medium" | "high" | "blocked";
export type TransactionIntent =
  | "none"
  | "browse"
  | "service_request"
  | "order_draft"
  | "payment_intent_requires_human"
  | "handoff"
  | "governance_review";

export type Channel =
  | "member_sidebar"
  | "no_plaintext_context_broker"
  | "hybrid_key_api_broker"
  | "browser_action_bus"
  | "counter_avatar"
  | "merchant_connector"
  | "committee_connector";

export type SafeBrowserAction =
  | "navigate_ref"
  | "click_ref"
  | "fill_ref"
  | "select_ref"
  | "read_text_ref"
  | "screenshot_ref"
  | "wait_ref"
  | "extract_ref"
  | "open_sidebar_ref"
  | "close_sidebar_ref"
  | "render_sidebar_ref"
  | "read_context_ref"
  | "write_draft_ref"
  | "route_to_connector_ref"
  | "broker_api_call_ref"
  | "cache_lookup_ref"
  | "read_menu_ref"
  | "create_order_draft_ref"
  | "queue_service_ref"
  | "notify_staff_ref"
  | "ask_human_confirm"
  | "handoff_to_human";

export interface D1Identity {
  actor_ref: string;
  actor_type: ActorType;
  device_ref: string;
  role: string;
  plaintext_identity_forbidden: true;
}

export interface D2Intent {
  primary_intent: string;
  secondary_intent: string;
  transaction_intent: TransactionIntent;
  risk_level: RiskLevel;
}

export interface D3State {
  session_state: "new" | "active" | "paused" | "closed";
  task_state: "draft" | "dry_run" | "pending_verify" | "verified" | "blocked" | "landed";
  browser_state: "not_requested" | "dry_run" | "active_readonly" | "blocked";
  order_state: "none" | "draft" | "quoted" | "pending_human_confirm" | "blocked";
  context_mode: "no_plaintext" | "ref_only" | "encrypted_ref_only";
}

export interface D4Topology {
  channel: Channel;
  site_ref: string;
  device_topology: string;
  origin_scope: "member_owned" | "staff_owned" | "merchant_owned" | "committee_owned" | "system_owned" | "broker_owned";
}

export interface D5Resource {
  key_policy: "broker_managed" | "hybrid_ref_only" | "no_raw_key" | "offline_none";
  selected_key_ref: `key_ref:${string}`;
  api_refs: Array<`api_ref:${string}`>;
  model_tier: "none" | "small" | "standard" | "high_reasoning" | "local_only";
  cache_policy: "no_cache" | "redacted_cache" | "ref_cache_only";
  cost_policy: "blocked" | "metered" | "budget_cap_ref" | "human_approved";
}

export interface D6Governance {
  allowed_actions: SafeBrowserAction[];
  forbidden_actions: string[];
  no_plaintext_context: true;
  human_confirm_required: boolean;
  staff_confirm_required: boolean;
}

export interface D7Verification {
  redaction_check_required: true;
  leak_check_required: true;
  action_allowlist_required: true;
  response_verify_required: true;
  usage_log_required: true;
}

export interface D8Envelope {
  packet_ref: `packet_ref:${string}`;
  nonce: string;
  counter: number;
  ttl_seconds: number;
  created_at: string;
  schema_version: "8d.packet.v1";
  content_hash: string;
  hmac_ref: `hmac_ref:${string}`;
  signature_ref: `signature_ref:${string}`;
  replay_protection: true;
}

export interface XiaoJ8DPacket {
  packet_type: "xiaoj_8d_packet";
  D1_identity: D1Identity;
  D2_intent: D2Intent;
  D3_state: D3State;
  D4_topology: D4Topology;
  D5_resource: D5Resource;
  D6_governance: D6Governance;
  D7_verification: D7Verification;
  D8_envelope: D8Envelope;
}

export interface BrowserActionPacket extends Omit<XiaoJ8DPacket, "packet_type"> {
  packet_type: "xiaoj_8d_action_packet";
  browser_action: {
    action_ref: `action_ref:${string}`;
    action_type: SafeBrowserAction;
    target_ref: string;
    params: Record<string, string | number | boolean | null>;
    dry_run: true;
    submit_forbidden: true;
  };
}

export interface XiaoJResponsePacket extends Omit<XiaoJ8DPacket, "packet_type"> {
  packet_type: "xiaoj_8d_response_packet";
  response: {
    response_ref: `response_ref:${string}`;
    status: "PASS" | "ISOLATE" | "MISSING" | "DOWN" | "BLOCK" | "MASK" | "HOLD" | "REPAIR";
    human_message_ref: string;
    redacted_output_ref: string;
    action_result_ref: string;
    errors: string[];
    warnings: string[];
    plaintext_response_forbidden: true;
  };
}
