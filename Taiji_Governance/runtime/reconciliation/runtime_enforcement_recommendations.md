# Runtime Enforcement Recommendations

1. Add a local `TensorPacket` builder before any Gateway action.
2. Add replay index append/check before shell, deployment, payment, multimodal, and deadbox recovery actions.
3. Add a governance interceptor in `services/gateway/policies/` that refuses non-packetized actions.
4. Keep A5 live operation disabled until enforcement tests prove:
   - TensorPacket exists.
   - replay check passed.
   - authority vector is valid.
   - topology vector is trusted.
   - audit channel is writable.
   - rollback horizon exists.
5. Treat direct production mutation without packet lineage as `L3_metric_hazard`.
6. Bind POS/Odoo/service intents to TensorPacket rather than raw natural language.
7. Keep raw plaintext out of runtime memory; store hashes and redacted summaries only.
