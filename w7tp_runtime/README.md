# W7TP Generative Transfer Converter v0.1

This package implements the public, deterministic W7TP-GTF 1.0.0 L1 path:

`SOURCE -> PACKET -> RECONSTRUCT -> VERIFY -> SEAL`

It accepts only byte streams that have a deterministic repeated-byte or repeated-block recipe. The packet carries one repeat block, its repeat count, the target size, and the expected SHA-256. Reconstruction creates a new local output from that recipe and verification requires an exact SHA-256 match.

It is not a general file copier, compressor, backup format, download mechanism, or full-source Base64 wrapper. Inputs without a supported repeat recipe stop with `STATE=HOLD_NOT_GENERATIVELY_REDUCIBLE`.

CLI example:

```bash
python3 -m w7tp_runtime.gt_converter_cli run SOURCE PACKET OUTPUT SEAL
```

The public packet contains no model call, database write, deployment action, member plaintext, or private lookup data.
