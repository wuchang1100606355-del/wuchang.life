# Gateway contract

A gateway contract carries the capability effect, not the source implementation.

Required fields:

- `capability_id`
- `source_ref`
- `target_coordinate`
- `protocols`
- `input_contract`
- `output_contract`
- `state_transition`
- `side_effects`
- `failure_modes`
- `evidence_requirements`

Generated contracts must set:

- `source_runtime_required=false`
- `source_authority_inherited=false`
- `w7tp_d8_authority_created=false`

A gateway may translate protocol shape, but it must not translate external authorization into W7TP effect authority.
