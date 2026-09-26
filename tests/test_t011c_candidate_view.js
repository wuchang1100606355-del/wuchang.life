const assert = require("assert");
const nodeCrypto = require("crypto");

if (!globalThis.crypto) globalThis.crypto = nodeCrypto.webcrypto;
if (!globalThis.TextEncoder) globalThis.TextEncoder = require("util").TextEncoder;

require("../web/xiaoj_member_browser_extension/t011c_candidate_view.js");

const text = JSON.stringify({
  candidate_summary: "safe local candidate",
  next_interface: "total-field-verifier",
  risk_flags: []
});
const digest = nodeCrypto.createHash("sha256").update(text, "utf8").digest("hex");

function envelope() {
  return {
    schema_version: "w7tp.t011c-interface-candidate.v1",
    state: "PASS_T011C_INTERFACE_CANDIDATE",
    candidate_only: true,
    runtime_effect: false,
    chrome_view: {
      state: "TOTAL_FIELD_REVIEWED_CANDIDATE",
      display_only: true,
      execution_allowed: false,
      candidate_sha256: digest,
      candidate_text: text,
      provider_ref: "MSI_OLLAMA_LOCAL",
      model_ref: "taiji-qwen2.5-coder-7b:ctx16k",
      total_field_decision: "ALLOW",
      allowed_user_actions: ["review_candidate", "copy_candidate"]
    },
    codex_task_packet_candidate: {
      packet_type: "W7TP_CODEX_TASK_PACKET",
      version: "v0.1",
      codex_authority: false,
      candidate_only: true,
      work_id: "codex_task_test",
      title: "test",
      intent: text,
      allowed_files: ["tools/example.py"],
      forbidden_actions: ["auto_commit"],
      safety_flags: {
        CODEX_AUTHORITY: false,
        AUTO_STAGE: false,
        AUTO_COMMIT: false,
        DEPLOY: false,
        SERVICE_RESTART: false
      }
    },
    codex_invocation_performed: false,
    authority: {
      model_authority: false,
      codex_authority: false,
      browser_authority: false,
      formal_effect_boundary: "TAIJI01_TOTAL_FIELD"
    }
  };
}

(async () => {
  const adapter = globalThis.T011CCandidateView;
  assert(adapter);

  const view = await adapter.buildView(envelope());
  assert.strictEqual(view.ok, true);
  assert.strictEqual(view.display_only, true);
  assert.strictEqual(view.execution_allowed, false);
  assert.strictEqual(view.codex_invocation_performed, false);
  assert.strictEqual(view.candidate_sha256, digest);
  assert.strictEqual(view.total_field_decision, "ALLOW");
  assert.deepStrictEqual(view.allowed_user_actions, ["review_candidate", "copy_candidate"]);

  const badBoundary = envelope();
  badBoundary.codex_invocation_performed = true;
  const blocked = await adapter.buildView(badBoundary);
  assert.strictEqual(blocked.ok, false);
  assert.strictEqual(blocked.execution_allowed, false);
  assert.strictEqual(blocked.reason, "codex_invocation_forbidden");

  const tampered = envelope();
  tampered.chrome_view.candidate_text = "tampered";
  const hashBlocked = await adapter.buildView(tampered);
  assert.strictEqual(hashBlocked.ok, false);
  assert.strictEqual(hashBlocked.reason, "candidate_hash_mismatch");

  const badAuthority = envelope();
  badAuthority.authority.browser_authority = true;
  const authorityBlocked = await adapter.buildView(badAuthority);
  assert.strictEqual(authorityBlocked.ok, false);
  assert.strictEqual(authorityBlocked.reason, "authority_boundary");

  console.log("PASS_T011C_CHROME_CANDIDATE_VIEW");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
