# Official documentation boundary — checked 2026-08-19

Only current OpenAI and Tailscale official documentation was used for MCP/Connector and Serve/Funnel/SSH conclusions.

## OpenAI

- [Build an MCP server](https://developers.openai.com/plugins/build/mcp-server): focused tools, explicit schemas/output metadata, accurate annotations, server-side authorization, Streamable HTTP `/mcp`, and no secrets in model-visible results.
- [Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt): ChatGPT testing requires a reachable public HTTPS endpoint or Secure MCP Tunnel; local startup alone is not a Connector connection.
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): private servers can remain non-public via an outbound OpenAI tunnel, but tunnel identity, API credential, organization/workspace association, and permissions are separate prerequisites.

This candidate creates none of those remote or account-side prerequisites.

## Tailscale

- [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve): proxies a local service to other authorized devices in the same tailnet and is governed by tailnet access controls.
- [Tailscale Funnel](https://tailscale.com/docs/features/tailscale-funnel): exposes a local resource to the public internet; enabling it changes the public surface and related tailnet configuration.
- [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh): a general SSH carrier requiring destination and policy configuration; it is not a bounded MCP capability gateway.

Therefore `127.0.0.1` startup is local validation only. Serve, Funnel, SSH, ACL, subnet, Cloudflare, OAuth, Connector registration, and remote commands remain outside this build and were not invoked.
