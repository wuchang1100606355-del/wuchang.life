# W7TP Generative Transfer Converter Core v1

Public deterministic L1 path:

`SOURCE -> STATE-FIELD PACKET -> RECONSTRUCT -> VERIFY -> SEAL`

The converter accepts only inputs that reduce to a deterministic repeated-byte or repeated-block recipe. W7TP-GTF 1.0.0 packets carry a portable relative target, reconstruction conditions, a canonical packet hash, and the expected result SHA-256. The default minimum source-to-packet reduction is 16x.

It is not a general file copier, compressor, backup format, download mechanism, or full-source Base64/hex wrapper. Unsupported, insufficiently reduced, oversized, malformed, tampered, or path-escaping packets fail closed. Reconstruction uses a temporary file and atomically publishes it only after SHA-256 verification. Existing outputs are never overwritten.

Integrity and authenticity are separate. SHA-256 can verify reconstructed bytes and canonical packet consistency; an unsigned packet always reports `AUTHENTICITY=UNVERIFIED`.

```bash
python3 -m w7tp_runtime.gt_converter_cli capabilities
python3 -m w7tp_runtime.gt_converter_cli run \
  --source SOURCE --packet PACKET --output-root OUTPUT_ROOT --report REPORT \
  --target reconstructed.bin
```

Commands are `capabilities`, `pack`, `inspect`, `reconstruct`, `verify`, and
`run`. Stable exit codes are PASS=0, HOLD=10, BLOCK=20, and ERROR=40. Packet and
seal JSON use sorted-key compact UTF-8 canonical serialization. Reconstruction
is chunked, output-root confined, lock protected, hash checked, and atomically
published without overwrite. Seal reports contain no payload, recipe block,
raw key, or absolute local path.

No model call, database write, deployment action, member plaintext, or private lookup data is part of this public converter.
