/** @odoo-module **/

import { ROLES, SUITES } from "./suite_contract.js";

const CUSTOMER_ROLES = new Set(["online_ordering", "in_store_self_service"]);
const FORBIDDEN_OFFLINE_KEYS = new Set([
  "member_ref", "phone", "email", "voucher_ref", "payment_token", "card_number", "cvv",
  "pricing_receipt_ref", "confirmed_order_ref",
]);

function exactInteger(value, label) {
  if (!/^-?\d+$/.test(String(value))) throw new Error(`NON_INTEGER_MONEY:${label}`);
  return BigInt(String(value));
}

export function validateSourcePricingMatrix(rows, acceptance) {
  if (!Array.isArray(rows) || rows.length !== 641) throw new Error("PRICE_MATRIX_ROW_COUNT_INVALID");
  const optionIds = new Set();
  const products = new Set();
  const groups = new Set();
  const questions = new Set();
  let positive = 0;
  let zero = 0;
  let negative = 0;
  for (const row of rows) {
    optionIds.add(row.option_id);
    products.add(row.product_id);
    groups.add(row.group_id);
    questions.add(row.question_id);
    const base = exactInteger(row.base_price, "base_price");
    const selected = exactInteger(row.selected_option_delta, "selected_option_delta");
    const defaults = exactInteger(row.other_required_default_delta, "other_required_default_delta");
    const totalDelta = exactInteger(row.selected_total_delta, "selected_total_delta");
    const total = exactInteger(row.total_price, "total_price");
    if (selected + defaults !== totalDelta || base + totalDelta !== total) {
      throw new Error(`PRICE_EQUATION_MISMATCH:${row.product_id}:${row.option_id}`);
    }
    if (selected > 0n) positive += 1;
    else if (selected < 0n) negative += 1;
    else zero += 1;
    if (row.semantics_identical_two_surfaces !== true) throw new Error("SURFACE_PRICE_DRIFT");
  }
  const counts = acceptance?.counts ?? {};
  const observed = {
    rows: rows.length,
    optionIds: optionIds.size,
    products: products.size,
    groups: groups.size,
    questions: questions.size,
    positive,
    zero,
    negative,
  };
  const expected = {
    rows: counts.normalized_product_choice_price_cases,
    optionIds: counts.active_options_applicable_to_products,
    products: counts.existing_interop_products,
    groups: counts.active_option_groups,
    questions: 42,
    positive: counts.positive_delta_cases,
    zero: counts.zero_delta_cases,
    negative: counts.negative_delta_cases,
  };
  if (JSON.stringify(observed) !== JSON.stringify(expected)) throw new Error("PRICING_COUNTS_DRIFT");
  return { state: "PASS_SOURCE_BOUND_201_OPTIONS_641_CASES", ...observed };
}

export function buildPriceRequest(row, { role, suiteId, sourceSha256 }) {
  if (!ROLES.includes(role)) return { state: "HOLD_UNKNOWN_ROLE" };
  if (!SUITES[suiteId]) return { state: "HOLD_UNKNOWN_SUITE" };
  if (!row?.product_id || !row?.option_id || !sourceSha256) return { state: "HOLD_PRICE_BINDING_INCOMPLETE" };
  return {
    state: "PASS_PRICE_REQUEST_CANDIDATE",
    request: {
      source_sha256: sourceSha256,
      product_id: String(row.product_id),
      quantity: Number(row.quantity),
      selected_option_ids: [String(row.option_id)],
    },
  };
}

export function acceptServerPrice(response) {
  const required = ["pricing_receipt_ref", "calculation_hash", "currency", "grand_total", "order_revision"];
  if (!response || required.some((key) => response[key] === undefined || response[key] === "")) {
    return { state: "HOLD_SERVER_PRICE_RECEIPT_REQUIRED" };
  }
  if (!Number.isInteger(response.grand_total) || response.grand_total < 0 || !Number.isInteger(response.order_revision)) {
    return { state: "HOLD_INVALID_SERVER_PRICE_RECEIPT" };
  }
  return {
    state: "PASS_SERVER_PRICE_ACCEPTED",
    total: response.grand_total,
    receipt: response.pricing_receipt_ref,
    orderRevision: response.order_revision,
  };
}

export async function mutationEnvelope({ orderRef, expectedRevision, operation, nonce }) {
  if (!orderRef || !Number.isInteger(expectedRevision) || expectedRevision < 0 || !operation || !nonce) {
    return { state: "HOLD_MUTATION_BINDING_INCOMPLETE" };
  }
  const body = { orderRef, expectedRevision, operation, nonce };
  const digest = await globalThis.crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(JSON.stringify(body)),
  );
  const idempotencyKey = [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  return {
    state: "PASS_MUTATION_CANDIDATE",
    order_ref: orderRef,
    expected_order_revision: expectedRevision,
    operation,
    idempotency_key: idempotencyKey,
  };
}

function containsForbiddenOfflineValue(value) {
  if (Array.isArray(value)) return value.some(containsForbiddenOfflineValue);
  if (value && typeof value === "object") {
    return Object.entries(value).some(([key, item]) => FORBIDDEN_OFFLINE_KEYS.has(key) || containsForbiddenOfflineValue(item));
  }
  return false;
}

export function stageOfflineDraft({ storeRef, sessionRef, ownerRole, cart, revision = 0 }) {
  if (!storeRef || !sessionRef || !CUSTOMER_ROLES.has(ownerRole) || !Array.isArray(cart)) {
    return { state: "HOLD_OFFLINE_DRAFT_BINDING_INCOMPLETE" };
  }
  if (containsForbiddenOfflineValue(cart)) return { state: "HOLD_OFFLINE_SENSITIVE_OR_EFFECT_DATA_FORBIDDEN" };
  return {
    state: "HELD_LOCAL_DRAFT_NOT_ORDERED",
    draft: {
      store_ref: storeRef,
      session_ref: sessionRef,
      owner_role: ownerRole,
      cart: structuredClone(cart),
      local_revision: revision,
      order_effect: false,
      payment_effect: false,
      voucher_effect: false,
    },
  };
}

export function replayOfflineDraft({ draft, actorRole, actorSessionRef, currentStoreRef, serverDecision }) {
  if (!draft || draft.state === "CONFIRMED") return { state: "HOLD_REPLAY_DRAFT_INVALID" };
  if (draft.owner_role !== actorRole || draft.session_ref !== actorSessionRef) {
    return { state: "HOLD_CROSS_ROLE_OR_SESSION_REPLAY" };
  }
  if (draft.store_ref !== currentStoreRef) return { state: "HOLD_CROSS_STORE_REPLAY" };
  if (!serverDecision || serverDecision.accepted !== true || !Number.isInteger(serverDecision.order_revision)) {
    return { state: "HOLD_SERVER_REPLAY_DECISION_REQUIRED" };
  }
  return {
    state: "PASS_REPLAY_REQUEST_ACCEPTED_BY_SERVER_FIXTURE",
    order_revision: serverDecision.order_revision,
    replay_receipt_ref: serverDecision.replay_receipt_ref,
  };
}

export function evaluateCancel({ orderState, actorRole, capabilities, serverPolicyAllows, mutation }) {
  if (!serverPolicyAllows) return { state: "HOLD_SERVER_CANCEL_POLICY_DENIED" };
  if (actorRole !== "staff_pos" || !capabilities.includes("order.cancel")) {
    return { state: "HOLD_CANCEL_CAPABILITY_REQUIRED" };
  }
  if (!["draft", "submitted"].includes(orderState)) return { state: "HOLD_ORDER_STATE_NOT_CANCELLABLE" };
  if (!mutation || mutation.operation !== "cancel" || !mutation.idempotency_key) {
    return { state: "HOLD_CANCEL_IDEMPOTENCY_BINDING_REQUIRED" };
  }
  return { state: "PASS_CANCEL_REQUEST_CANDIDATE_REQUIRES_SERVER_EFFECT" };
}

export function projectOrderForRole({ order, actorRole, actorSessionRef, actorStoreRef, capabilities = [] }) {
  if (!ROLES.includes(actorRole) || order.store_ref !== actorStoreRef) return { state: "HOLD_ORDER_SCOPE_MISMATCH" };
  if (actorRole === "staff_pos") {
    if (!capabilities.includes("order.read")) return { state: "HOLD_STAFF_ORDER_READ_CAPABILITY_REQUIRED" };
    return {
      state: "PASS_MASKED_STAFF_ORDER_PROJECTION",
      order: {
        order_ref: order.order_ref,
        state: order.state,
        grand_total: order.grand_total,
        customer_label_masked: order.customer_label_masked ?? null,
      },
    };
  }
  if (!CUSTOMER_ROLES.has(actorRole) || order.owner_role !== actorRole || order.owner_session_ref !== actorSessionRef) {
    return { state: "HOLD_CROSS_ROLE_OR_SESSION_READ" };
  }
  return {
    state: "PASS_CUSTOMER_OWN_SESSION_PROJECTION",
    order: {
      order_ref: order.order_ref,
      state: order.state,
      grand_total: order.grand_total,
      items: structuredClone(order.items ?? []),
    },
  };
}
