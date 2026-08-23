# Information-flow contract

Supply the policy; do not rely on hidden defaults.

Input fields:

- `label_rank`: map from declared label to integer rank
- `current_labels`: labels already carried by the session or artifact
- `incoming_labels`: labels introduced by this operation
- `destination_max_label`: highest label the destination accepts
- `redaction_available`: whether an approved transformation is available
- `redaction_output_labels`: labels after that declared transformation
- `declassification_authorized`: structural flag only; authority provenance must remain referenced separately

The output must preserve labels unless a declared transform or valid declassification rule changes them.
