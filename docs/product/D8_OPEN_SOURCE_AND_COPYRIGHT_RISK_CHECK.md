# D8 Open Source And Copyright Risk Check

## Projects Reviewed

| Project | License / status observed | Source | Risk for D8 |
|---|---|---|---|
| Continue | Apache 2.0; repository reported read-only/not actively maintained. | [Continue docs](https://docs.continue.dev/), [Continue GitHub](https://github.com/continuedev/continue), [Continue license](https://github.com/continuedev/continue/blob/main/LICENSE) | Do not copy code. Concepts like CLI/IDE agent are common; D8 should remain governance layer. |
| Aider | Apache 2.0. | [Aider docs](https://aider.chat/docs/), [Aider GitHub](https://github.com/aider-ai/aider), [Aider license](https://github.com/Aider-AI/aider/blob/main/LICENSE.txt) | Do not copy code or UI/CLI behavior. Aider is a coding tool, not D8's governance loop. |
| OpenHands | MIT for core; enterprise directory has separate license. | [OpenHands docs](https://docs.openhands.dev/overview/introduction), [OpenHands GitHub](https://github.com/OpenHands/openhands) | Do not copy implementation. Avoid presenting D8 as an OpenHands clone. |
| Open Policy Agent | Open-source policy engine with Rego. | [OPA](https://openpolicyagent.org/), [OPA GitHub](https://github.com/open-policy-agent/OPA) | Policy-as-code is established. D8 should implement its own guard logic or clearly comply with OPA license if reused. |
| LangGraph / LangChain | Agent workflow/HITL framework ecosystem. | [LangGraph overview](https://www.langchain.com/langgraph), [LangChain HITL docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) | Do not copy docs/examples into D8. D8 can integrate later, but MVP should keep clean-room language. |

## License Concerns

- Apache 2.0 projects require preserving notices and license terms if code is reused.
- MIT projects require preserving copyright and license notices.
- Enterprise or proprietary directories must not be copied.
- Odoo Apps Store modules may carry OPL-1, AGPL-3, or proprietary terms; do not copy module code.
- Public docs can inform market comparison but should not be copied into product copy.

## Code Reuse Warning

D8 Phase14 did not copy external source code.

Future implementation must follow clean-room rules:

- Use public docs only for feature comparison.
- Do not paste external code.
- Do not reproduce unique UI flows, prompts, labels, or proprietary implementation details.
- If open-source code is reused later, record exact repository, commit, license, NOTICE obligations, and human approval.

## What Must Not Be Copied

- Agent prompts or internal rules from any external product.
- Cursor/Claude/Codex/Devin UX copy or workflow naming.
- OpenHands enterprise code.
- Odoo third-party POS AI module code.
- Any patented claim language.
- Any private leaked code or extracted proprietary material.

## Clean-Room Guidance

1. Keep D8 product language grounded in local D8 evidence.
2. Implement only from D8 requirements and local architecture.
3. Use external sources for category mapping and risk awareness only.
4. Maintain a source matrix for all inspiration.
5. Require human legal review before code reuse, patent filing, or public novelty claims.
