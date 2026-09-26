(() => {
  const SCHEMA = "w7tp.t011c-interface-candidate.v1";

  function fail(reason) {
    return {
      ok: false,
      state: "HOLD_T011C_CHROME_CANDIDATE_VIEW",
      reason,
      display_only: true,
      execution_allowed: false,
      candidate_only: true,
      codex_invocation_performed: false
    };
  }

  async function sha256Hex(text) {
    const digest = await crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(String(text))
    );
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  async function validate(envelope) {
    if (!envelope || typeof envelope !== "object") return fail("envelope_not_object");
    if (envelope.schema_version !== SCHEMA) return fail("schema_mismatch");
    if (envelope.state !== "PASS_T011C_INTERFACE_CANDIDATE") return fail("candidate_not_ready");
    if (envelope.candidate_only !== true) return fail("candidate_only_required");
    if (envelope.runtime_effect !== false) return fail("runtime_effect_forbidden");
    if (envelope.codex_invocation_performed !== false) return fail("codex_invocation_forbidden");

    const authority = envelope.authority || {};
    if (
      authority.model_authority !== false ||
      authority.codex_authority !== false ||
      authority.browser_authority !== false ||
      authority.formal_effect_boundary !== "TAIJI01_TOTAL_FIELD"
    ) {
      return fail("authority_boundary");
    }

    const view = envelope.chrome_view || {};
    if (view.state !== "TOTAL_FIELD_REVIEWED_CANDIDATE") return fail("total_field_review_required");
    if (view.display_only !== true || view.execution_allowed !== false) return fail("display_only_boundary");
    if (view.provider_ref !== "MSI_OLLAMA_LOCAL") return fail("provider_boundary");
    if (view.total_field_decision !== "ALLOW") return fail("total_field_allow_required");
    if (!/^[0-9a-f]{64}$/.test(String(view.candidate_sha256 || ""))) return fail("candidate_hash_invalid");
    if (typeof view.candidate_text !== "string" || view.candidate_text.length > 8192) return fail("candidate_text_invalid");
    const computed = await sha256Hex(view.candidate_text);
    if (computed !== view.candidate_sha256) return fail("candidate_hash_mismatch");

    const codex = envelope.codex_task_packet_candidate || {};
    const safety = codex.safety_flags || {};
    if (
      codex.packet_type !== "W7TP_CODEX_TASK_PACKET" ||
      codex.codex_authority !== false ||
      codex.candidate_only !== true ||
      safety.CODEX_AUTHORITY !== false ||
      safety.AUTO_STAGE !== false ||
      safety.AUTO_COMMIT !== false ||
      safety.DEPLOY !== false ||
      safety.SERVICE_RESTART !== false
    ) {
      return fail("codex_candidate_boundary");
    }
    return { ok: true };
  }

  async function buildView(envelope) {
    const check = await validate(envelope);
    if (!check.ok) return check;
    const view = envelope.chrome_view;
    return {
      ok: true,
      state: "PASS_T011C_CHROME_CANDIDATE_VIEW",
      display_only: true,
      execution_allowed: false,
      candidate_only: true,
      codex_invocation_performed: false,
      candidate_sha256: view.candidate_sha256,
      candidate_text: view.candidate_text,
      provider_ref: view.provider_ref,
      model_ref: view.model_ref,
      total_field_decision: view.total_field_decision,
      allowed_user_actions: Array.isArray(view.allowed_user_actions)
        ? [...view.allowed_user_actions]
        : [],
      codex_task_packet_candidate_ready: true
    };
  }

  globalThis.T011CCandidateView = Object.freeze({
    validate,
    buildView
  });
})();
