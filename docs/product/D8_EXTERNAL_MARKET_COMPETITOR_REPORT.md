# D8 External Market Competitor Report

## Scope

This report compares the Phase 13 D8 internal product baseline against external coding-agent, agent-workflow, Odoo/POS, and AI-safety products.

Internal baseline:

- Product: D8 Total Field Agent Governance Console / D8 總場代理治理操作台
- First vertical: 聊國咖啡館重新總店 / Odoo POS / 主權 AI 營運安全操作台
- Core evidence: local D8 memory, redteam quarantine, possible alerts, guard evaluator, mandatory preflight, operator console, dashboard, voice/text operator, read-only Odoo/POS safe bridge, recovery/handoff seals.

External research was conducted from public web sources. No external code was copied.

## Competitors Found

| Competitor / category | What it does | Source | Where D8 differs |
|---|---|---|---|
| OpenAI Codex | Cloud coding agent that can read, edit, run code, and work in a cloud environment. | [OpenAI Codex web docs](https://developers.openai.com/codex/cloud), [Codex GitHub](https://github.com/openai/codex) | D8 is not trying to be a coding agent. It is the local governance console before and after agent work. |
| Claude Code | Agentic coding tool in terminal/IDE/GitHub workflows. | [Anthropic Claude Code GitHub](https://github.com/anthropics/claude-code) | D8 does not compete on code-generation model quality. It competes on task gating, incident memory, and sealed local governance. |
| Cursor | AI code editor with agent workflows and planning guidance. | [Cursor docs](https://cursor.com/docs), [Cursor agent best practices](https://cursor.com/blog/agent-best-practices) | Cursor is the workbench; D8 is the safety console around workbench usage and local operations. |
| Devin | Cloud AI software engineer with planning, execution, shell, editor, browser, knowledge, and secrets features. | [Devin docs](https://docs.devin.ai/get-started/devin-intro), [Devin product](https://devin.ai/), [Cognition Devin launch](https://cognition.ai/blog/introducing-devin) | Devin sells autonomous engineering capacity. D8 sells local governance, redteam writeback, and operational boundary proof. |
| Continue | Open-source coding agent available as CLI, VS Code extension, and JetBrains plugin. | [Continue docs](https://docs.continue.dev/), [Continue GitHub](https://github.com/continuedev/continue) | Continue is developer tooling. D8 can govern Continue-like agents but should not present itself as a Continue replacement. |
| Aider | Terminal AI pair programming tool for editing local git repos. | [Aider docs](https://aider.chat/docs/), [Aider GitHub](https://github.com/aider-ai/aider), [Aider license](https://github.com/Aider-AI/aider/blob/main/LICENSE.txt) | Aider is interactive coding. D8's differentiator is preflight, guard decisioning, and non-executable failure memory. |
| OpenHands | Open-source software development agent platform and SDK. | [OpenHands docs](https://docs.openhands.dev/overview/introduction), [OpenHands GitHub](https://github.com/OpenHands/openhands) | OpenHands is an agent platform. D8 should remain an agent governance and SMB operations safety layer. |
| LangGraph / LangChain HITL | Agent workflow framework with human-in-the-loop tool-call review. | [LangChain HITL docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop), [LangGraph overview](https://www.langchain.com/langgraph) | D8 is less a framework and more a local productized governance surface with sealed reports and vertical Odoo/POS evidence. |
| Odoo AI / AI Agents | AI assistant and agents inside Odoo, with tools/sources and natural-language help. | [Odoo AI docs](https://www.odoo.com/documentation/19.0/applications/productivity/ai.html), [Odoo AI agents](https://www.odoo.com/documentation/19.0/applications/productivity/ai/agents.html) | D8 should not be an Odoo AI replacement. D8 is the external safety layer for read-only evidence and guarded operation. |
| Odoo POS / restaurant POS | POS for shops/restaurants, tables, orders, bills, tips, and restaurant operations. | [Odoo POS docs](https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale.html), [Odoo restaurant POS docs](https://www.odoo.com/documentation/19.0/applications/sales/point_of_sale/restaurant.html) | D8 must not claim POS replacement. It can safely govern AI/Odoo/POS workflows without order/payment writes. |
| OWASP / NIST / OPA safety ecosystems | AI risk, agent threats, excessive agency, policy-as-code, and risk management guidance. | [OWASP Agentic AI](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/), [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/), [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), [OPA](https://openpolicyagent.org/) | D8 can position as a practical local implementation pattern inspired by these risk categories, not a replacement for enterprise GRC tools. |

## Where D8 Is Strong

- Local-first operational governance for AI agents.
- Redteam/failure writeback as future alert memory.
- Non-executable redteam quarantine.
- Explicit PASS / INFO / WARN / HOLD / BLOCK task gating.
- Sealed reports and handoff state.
- Concrete Odoo/POS read-only vertical proof.
- Useful for small teams that cannot adopt full enterprise AI governance tooling.

## Where D8 Is Weaker

- It does not yet have public benchmark validation.
- It does not yet have external customer proof.
- It is not a full agent framework like LangGraph or OpenHands.
- It is not a high-powered coding agent like Codex, Claude Code, Cursor, or Devin.
- It does not yet have a polished product UI or packaged installer.
- It needs formal security review before any production claim.

## What Claims Should Be Avoided

- Do not claim D8 is the first or only agent governance system.
- Do not claim absolute safety or unbreakability.
- Do not claim patent novelty before legal prior-art review.
- Do not claim D8 replaces Codex, Claude Code, Cursor, Devin, Odoo AI, or Odoo POS.
- Do not claim production readiness until formal release gates pass.
- Do not reveal internal-only rules, dictionaries, weights, or WHY_IT_RUNS-style material.

## Positioning Recommendation

Best external-facing product:

D8 Total Field Agent Governance Console for SMB / Odoo / POS local operations.

Recommended category:

Local-first AI Agent Governance Console for SMB operations.

Recommended first wedge:

AI Agent Safety / Governance for Odoo + POS + cafe/community local operations.

D8 should be shown as the safety and audit layer that sits around coding agents and store-operation AI, not as another autonomous coding assistant.
