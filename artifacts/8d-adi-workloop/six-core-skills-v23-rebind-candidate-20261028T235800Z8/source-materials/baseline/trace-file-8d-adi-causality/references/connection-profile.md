# Private fixed-IP connection profile

Store this JSON outside the skill, repository, prompt, and evidence output. Restrict its filesystem permissions to the current user.

```json
{
  "schema_version": "trace-file-8d-adi-fixed-ip-profile/1.0",
  "node_ref": "node://opaque-primary-total-field",
  "host_ip": "<fixed IP literal>",
  "ssh_user": "<SSH account>",
  "ssh_port": 22,
  "remote_repo": "/absolute/repository/path",
  "remote_output_dir": "/absolute/repository/path/evidence/total_field/file_8d_adi_causal_index/<run-id>",
  "connect_timeout_seconds": 10,
  "analysis_timeout_seconds": 900
}
```

The profile must contain no password, token, private key, member plaintext, SSH option injection, hostname, command, or fallback address. Authentication and host trust must already be configured for OpenSSH. The runner uses `BatchMode=yes` and `StrictHostKeyChecking=yes`.

The IP address is dynamic infrastructure evidence and remains outside the shared skill. A successful connection proves only carrier availability; it grants no execution, activation, router, canonical, or Total Field authority.

The remote node requires only `python3`. Git and the VS Code `code` CLI are not required.

Pass Founder intent and the human-visible product effect as ephemeral `remote_runner.py` arguments. Do not persist them in the private connection profile. They form the 8D field root; the fixed IP remains only a carrier coordinate.

`analysis_timeout_seconds` is optional, defaults to 900, and accepts 60 through 3600 seconds. It bounds the already-authorized analyzer execution; it grants no new network or execution authority.
