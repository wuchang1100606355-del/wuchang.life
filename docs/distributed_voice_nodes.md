# Distributed AI Voice Nodes

This repo now has a portable AI gateway container for shared use across a
distributed compute group. The default operating mode is LAN-first.

## Goal

Every machine should run the same container image and differ only by environment
variables:

- `NODE_ID`: stable node name, such as `shop-pos-01` or `gpu-node-02`
- `NODE_ROLE`: current role, default `gateway`
- `TAIJI_GATEWAY_PORT`: host port mapped to container port `9002`
- `LAN_BASE_URL`: the URL other machines on the same LAN should use
- `CLAW_PORT`: host port for the optional native claw service
- `CLAW_SANDBOX_DIR`: writable workspace used by command/file-writing tools
- `ALLOWED_CLIENT_CIDRS`: source IP ranges allowed to call gateway/claw
- `VOICE_PROVIDER`: `local` for free local TTS today
- `GEMINI_API_KEY`: optional cloud brain key

## Start One LAN Node

```bash
cp .env.example .env
docker compose -f docker-compose.ai.yml up --build -d
```

Set `LAN_BASE_URL` to the machine's LAN address:

```env
NODE_ID=front-desk-pc
TAIJI_GATEWAY_PORT=9002
LAN_BASE_URL=http://192.168.1.10:9002
```

OpenAI-compatible endpoints:

- `GET http://NODE_IP:9002/v1/models`
- `POST http://NODE_IP:9002/v1/chat/completions`
- `POST http://NODE_IP:9002/v1/audio/speech`
- `GET http://NODE_IP:9002/v1/audio/voices`
- `POST http://NODE_IP:9004/api/openclaw/ask`

## Cheap Organization Mode

Use `VOICE_PROVIDER=local` first. The container installs `espeak-ng`, so it can
generate WAV files without paying a commercial voice provider. If local speech
breaks on a weak node, the code returns a valid fallback WAV instead of crashing
the WebUI.

## Later Commercial Mode

When budget exists, keep the same endpoint and swap only environment variables,
for example:

```env
VOICE_PROVIDER=azure
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastasia
VOICE_NAME=zh-TW-HsiaoChenNeural
```

The WebUI should keep calling `/v1/audio/speech`; only the backend adapter
changes.

## Multi-Machine Pattern

Run one container per node. On the same LAN, point WebUI to the chosen node:

```text
http://<lan-ip>:9002/v1
```

For failover, keep the same `.env.example` contract and change only `NODE_ID`,
`LAN_BASE_URL`, and `TAIJI_GATEWAY_PORT` per machine.

## Claw

The claw is still present as `legacy_core/taiji_native_claw.py`. In compose it
runs as `taiji-claw` on port `9004`.

Use it on the LAN or VPN with:

```text
http://<lan-or-vpn-ip>:9004/api/openclaw/ask
```

It should write only inside `CLAW_SANDBOX_DIR`. Keep that directory mounted to
`./data/claw_workspace` so every machine has a predictable local safe area.

Both gateway and claw enforce `ALLOWED_CLIENT_CIDRS`. The default allows
localhost, private LAN ranges, Tailscale/Headscale `100.64.0.0/10`, and local
IPv6 ranges.

For stricter VPN-only access:

```env
ALLOWED_CLIENT_CIDRS=100.64.0.0/10
```

For one exact machine:

```env
ALLOWED_CLIENT_CIDRS=100.101.22.33/32
```

## LAN Checklist

- Give gateway machines DHCP reservations on the router, or set static LAN IPs.
- Keep the container mapped to `0.0.0.0:${TAIJI_GATEWAY_PORT}` so other LAN
  devices can reach it.
- In WebUI, use `http://<lan-ip>:9002/v1` as the OpenAI-compatible base URL.
- If you need native claw access, allow inbound TCP on `9004` only inside LAN/VPN.
- If Windows Firewall blocks access, allow inbound TCP on `9002`.
- Keep `.env` private. Share `.env.example`, not real keys.
