# Metric Information Watermark Boundary

版本：2026-05-12

## Rule

All licensed metric information and community vector datasets may carry a
non-personal audit watermark.

The watermark traces:

- dataset version
- release window
- license hash
- recipient class
- SHA256 baseline

It must not trace:

- individual members
- private devices
- personal identity
- secrets

## Principle

Metric information may circulate.

The audit chain must not break.

If leaked, the package should be traceable through non-personal watermark and
SHA256 lineage.

