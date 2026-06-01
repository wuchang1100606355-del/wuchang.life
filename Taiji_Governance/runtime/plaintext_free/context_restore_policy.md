# Context Restore Policy

Context restoration may use:

- rescue snapshot metadata
- TensorPacket hash and lineage
- governance summaries
- topology state
- redacted audit events

Context restoration may not use:

- raw secret material
- private account content
- reversible personal data labels
- unreviewed cloud transcripts

Restore requires human decision when the target action crosses into L2 or L3.
