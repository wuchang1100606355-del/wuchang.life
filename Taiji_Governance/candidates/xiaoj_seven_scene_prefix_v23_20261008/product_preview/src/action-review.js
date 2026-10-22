const replayLedger = new Set();

export const ACTION_REVIEW_FIELDS = Object.freeze([
  "action_id",
  "member_ref_hash",
  "root_ref",
  "root_generation",
  "session_ref",
  "scene_ref",
  "capability_ref",
  "action_type",
  "target_refs",
  "parameters_sha256",
  "purpose_ref",
  "scope_refs",
  "resource_refs",
  "effect_class",
  "expected_result",
  "maximum_effect",
  "risk_summary",
  "rollback_ref",
  "nonce",
  "expires_at",
  "review_state",
  "reviewer_receipt_ref",
  "reviewer_receipt_sha256",
  "action_hash",
]);

function stableValue(value) {
  if (Array.isArray(value)) {
    return value.map(stableValue);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stableValue(value[key])]),
    );
  }
  return value;
}

export function canonicalJson(value) {
  return JSON.stringify(stableValue(value));
}

export async function sha256Text(value) {
  const bytes = new TextEncoder().encode(String(value));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function randomRef(prefix) {
  if (typeof globalThis.crypto.randomUUID === "function") {
    return `${prefix}:${globalThis.crypto.randomUUID()}`;
  }
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  return `${prefix}:${[...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

function actionHashBody(packet) {
  return {
    action_id: packet.action_id,
    member_ref_hash: packet.member_ref_hash,
    root_ref: packet.root_ref,
    root_generation: packet.root_generation,
    session_ref: packet.session_ref,
    scene_ref: packet.scene_ref,
    capability_ref: packet.capability_ref,
    action_type: packet.action_type,
    target_refs: packet.target_refs,
    parameters_sha256: packet.parameters_sha256,
    purpose_ref: packet.purpose_ref,
    scope_refs: packet.scope_refs,
    resource_refs: packet.resource_refs,
    effect_class: packet.effect_class,
    expected_result: packet.expected_result,
    maximum_effect: packet.maximum_effect,
    risk_summary: packet.risk_summary,
    rollback_ref: packet.rollback_ref,
    nonce: packet.nonce,
    expires_at: packet.expires_at,
  };
}

export async function calculateActionHash(packet) {
  return sha256Text(canonicalJson(actionHashBody(packet)));
}

export function validateActionReviewPacket(packet) {
  const missing = ACTION_REVIEW_FIELDS.filter(
    (field) => !(field in packet) || packet[field] === undefined,
  );
  if (missing.length) {
    throw new Error(`HOLD_ACTION_REVIEW_FIELDS_MISSING:${missing.join(",")}`);
  }
  if (!Array.isArray(packet.target_refs) || !packet.target_refs.length) {
    throw new Error("HOLD_ACTION_TARGET_REFS_REQUIRED");
  }
  if (!Array.isArray(packet.scope_refs) || !Array.isArray(packet.resource_refs)) {
    throw new Error("HOLD_ACTION_SCOPE_RESOURCE_REFS_REQUIRED");
  }
  if (!/^[0-9a-f]{64}$/.test(packet.parameters_sha256)) {
    throw new Error("HOLD_PARAMETERS_SHA256_INVALID");
  }
  if (!/^[0-9a-f]{64}$/.test(packet.action_hash)) {
    throw new Error("HOLD_ACTION_HASH_INVALID");
  }
  if (packet.review_state !== "PENDING_HUMAN_REVIEW") {
    throw new Error("HOLD_REVIEW_STATE_NOT_PENDING");
  }
  return true;
}

export async function createActionReviewPacket({
  session,
  sceneRef,
  capabilityRef,
  actionType,
  targetRefs,
  parameters,
  purposeRef,
  scopeRefs,
  resourceRefs,
  effectClass,
  expectedResult,
  maximumEffect,
  riskSummary,
  rollbackRef,
  ttlSeconds = 600,
  now = new Date(),
}) {
  const parametersSha256 = await sha256Text(canonicalJson(parameters));
  const packet = {
    action_id: randomRef("action"),
    member_ref_hash: session.memberRefHash,
    root_ref: session.rootRef,
    root_generation: session.rootGeneration,
    session_ref: session.sessionRef,
    scene_ref: sceneRef,
    capability_ref: capabilityRef,
    action_type: actionType,
    target_refs: [...targetRefs],
    parameters_sha256: parametersSha256,
    purpose_ref: purposeRef,
    scope_refs: [...scopeRefs],
    resource_refs: [...resourceRefs],
    effect_class: effectClass,
    expected_result: expectedResult,
    maximum_effect: maximumEffect,
    risk_summary: riskSummary,
    rollback_ref: rollbackRef,
    nonce: randomRef("nonce"),
    expires_at: new Date(now.getTime() + ttlSeconds * 1000).toISOString(),
    review_state: "PENDING_HUMAN_REVIEW",
    reviewer_receipt_ref: null,
    reviewer_receipt_sha256: null,
    action_hash: "",
  };
  packet.action_hash = await calculateActionHash(packet);
  validateActionReviewPacket(packet);
  return Object.freeze(packet);
}

export async function approveActionReview({
  packet,
  parameters,
  currentSession,
  currentSceneRef,
  now = new Date(),
}) {
  validateActionReviewPacket(packet);
  if (replayLedger.has(packet.action_hash)) {
    throw new Error("HOLD_REVIEW_RECEIPT_REPLAY");
  }
  if (packet.member_ref_hash !== currentSession.memberRefHash) {
    throw new Error("HOLD_CROSS_MEMBER_APPROVAL");
  }
  if (packet.session_ref !== currentSession.sessionRef) {
    throw new Error("HOLD_CROSS_SESSION_APPROVAL");
  }
  if (packet.scene_ref !== currentSceneRef) {
    throw new Error("HOLD_CROSS_SCENE_APPROVAL");
  }
  if (new Date(packet.expires_at).getTime() <= now.getTime()) {
    throw new Error("HOLD_APPROVAL_EXPIRED");
  }
  const currentParametersHash = await sha256Text(canonicalJson(parameters));
  if (currentParametersHash !== packet.parameters_sha256) {
    throw new Error("HOLD_PARAMETERS_CHANGED_AFTER_REVIEW");
  }
  const currentActionHash = await calculateActionHash(packet);
  if (currentActionHash !== packet.action_hash) {
    throw new Error("HOLD_ACTION_HASH_MISMATCH");
  }
  replayLedger.add(packet.action_hash);
  const receipt = {
    reviewer_receipt_ref: randomRef("reviewer-receipt"),
    action_hash: packet.action_hash,
    review_state: "APPROVED",
    reviewed_at: now.toISOString(),
    member_ref_hash: currentSession.memberRefHash,
    session_ref: currentSession.sessionRef,
    total_field_decision: "HOLD_CANDIDATE_NO_LIVE_EFFECT",
    effect_executed: false,
    database_write: false,
    external_send: false,
    runtime_change: false,
  };
  receipt.reviewer_receipt_sha256 = await sha256Text(canonicalJson(receipt));
  return Object.freeze(receipt);
}

export async function rejectActionReview({ packet, currentSession, now = new Date() }) {
  validateActionReviewPacket(packet);
  if (packet.member_ref_hash !== currentSession.memberRefHash) {
    throw new Error("HOLD_CROSS_MEMBER_REJECTION");
  }
  replayLedger.add(packet.action_hash);
  return Object.freeze({
    reviewer_receipt_ref: randomRef("reviewer-receipt"),
    action_hash: packet.action_hash,
    review_state: "REJECTED",
    reviewed_at: now.toISOString(),
    effect_executed: false,
    side_effect_count: 0,
  });
}

export function resetReplayLedgerForTests() {
  replayLedger.clear();
}
