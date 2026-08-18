import { PRODUCT_CONTRACT } from "./product-contract.js";

export const ODOO_AUTHORITY_BOUNDARY = Object.freeze({
  authority: PRODUCT_CONTRACT.authority.membership,
  runtimeBinding: "UNBOUND_ISOLATED_CANDIDATE",
  apiEndpoint: null,
  databaseWrite: false,
  liveMemberData: false,
});

export function buildOdooProjectionCandidate({ actionType, targetRefs, parametersSha256 }) {
  if (!actionType || !Array.isArray(targetRefs) || !parametersSha256) {
    throw new Error("HOLD_ODOO_CANDIDATE_FIELDS_REQUIRED");
  }
  return Object.freeze({
    authorityRef: "logical://taiji01/odoo",
    actionType,
    targetRefs: [...targetRefs],
    parametersSha256,
    state: "CANDIDATE_ONLY",
    endpoint: null,
    databaseWrite: false,
  });
}

export async function executeOdooEffect() {
  throw new Error("HOLD_LIVE_ODOO_EFFECT_FORBIDDEN_IN_ISOLATED_CANDIDATE");
}
