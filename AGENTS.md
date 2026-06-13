# Taiji_Hub Agent Rules

These rules are repository gates for Codex and other agents working in W7TP / XiaoJ / GTS / IGC. They bind project work in this repo before local preference, UI convenience, or generic agent patterns.

## Direct Shortest Path Rule

This repo's agent work must follow the direct shortest path.

Do not convert W7TP, XiaoJ, Five-in-One, 8D Packet, Member-Owned Sidebar XiaoJ, No-Plaintext Context, BYOK, or Cloud Blind Compute into an ordinary UI, ordinary agent, ordinary extension, ordinary SaaS workflow, generic chatbot, or browser automation project.

The work must preserve W7TP / XiaoJ as a generative transmission system: state is encoded, coordinated, hashed, packetized, transferred, verified, reconstructed, evidenced, and only then acted upon.

## Generative Transfer Priority Gate

If a task involves any of the following:

- XiaoJ member system
- 8D packet
- Member-Owned Sidebar XiaoJ
- browser-driving AI
- Cloud Blind Compute
- No-Plaintext Context
- BYOK / key_ref / api_ref
- merchant / committee API_ref
- Five-in-One deployment

and `W3_GENERATIVE_TRANSFER_DEPLOY` does not yet exist or is not yet indexed, the next step must be:

`W3_GENERATIVE_TRANSFER_DEPLOY`

Do not jump to these before Generative Transfer Deploy is complete and indexed by the Master Deploy Index:

- Browser Action Bus
- UI Scaffold
- Context Broker
- Key/API Broker
- Avatar Spec
- Connector Spec

## Main Chain Rule

All next-step ordering must check the main chain first:

State
-> Coordinate
-> Hash
-> Packet
-> Generative Transfer
-> Verify
-> Reconstruct
-> Evidence
-> Action

If a proposed next step is not on this main chain, output:

`STATE=HOLD_MAIN_CHAIN_DEVIATION`

## Redteam Rule

Redteam is not a blocker.

Redteam work exists to:

- find risk;
- set boundaries;
- produce safe one-paste paths;
- advance the main trunk.

Redteam must not use generic compliance review to indefinitely postpone core generative transfer.

Safety must identify the safe shortest path; it must not be used as a reason to slow or block the main trunk.

## No Detour Rule

Do not skip Generative Transfer because a UI seems more intuitive, an Action Bus seems safer, or a Broker seems more engineered.

If the 8D Schema SDK is complete and Generative Transfer is not complete, the fixed next step is Generative Transfer Deploy.

## Required Next Step Chain

Every next step must preserve this sequence:

State -> Coordinate -> Hash -> Packet -> Generative Transfer -> Verify -> Reconstruct -> Evidence -> Action

## Output Rule

Codex final responses for this repo must be minimal:

- STATE
- RUN_ID
- HEAD_BEFORE
- HEAD_AFTER
- files changed
- verifier result
- git status
- HOLD reason if any
