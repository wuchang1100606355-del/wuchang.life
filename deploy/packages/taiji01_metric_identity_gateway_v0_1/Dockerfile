FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
WORKDIR /app
RUN pip install --no-cache-dir jsonschema==4.10.3
COPY deploy/packages/taiji01_metric_identity_gateway_v0_1/taiji01_metric_identity_gateway.py /app/taiji01_metric_identity_gateway.py
COPY runtime_adapters/sovereign_ai_candidate_intake.py /app/runtime_adapters/sovereign_ai_candidate_intake.py
COPY tools/d3_coordinate_transition_candidate.py /app/tools/d3_coordinate_transition_candidate.py
COPY tools/domain_completion_total_field_gateway.py /app/tools/domain_completion_total_field_gateway.py
COPY tools/eightd_gte_parser_candidate.py /app/tools/eightd_gte_parser_candidate.py
COPY tools/sovereign_ai_domain_completion_candidate.py /app/tools/sovereign_ai_domain_completion_candidate.py
COPY tools/tfct_true8d_runtime_candidate.py /app/tools/tfct_true8d_runtime_candidate.py
COPY tools/total_field_candidate_gateway.py /app/tools/total_field_candidate_gateway.py
COPY schemas/sovereign_ai_candidate_intake_request.schema.json /app/schemas/sovereign_ai_candidate_intake_request.schema.json
COPY schemas/field/8d_governance_tensor_expression_candidate.schema.json /app/schemas/field/8d_governance_tensor_expression_candidate.schema.json
COPY schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json /app/schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json
COPY schemas/field/sovereign_ai_domain_completion_candidate.schema.json /app/schemas/field/sovereign_ai_domain_completion_candidate.schema.json
COPY runtime/total_field/candidate/d3_coordinate_transition_rules_v0_3.json /app/runtime/total_field/candidate/d3_coordinate_transition_rules_v0_3.json
COPY runtime/total_field/candidate/sovereign_ai_domain_completion_policy_v0_1.json /app/runtime/total_field/candidate/sovereign_ai_domain_completion_policy_v0_1.json
COPY runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json /app/runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json
USER 65532:65532
ENTRYPOINT ["python3", "/app/taiji01_metric_identity_gateway.py"]
