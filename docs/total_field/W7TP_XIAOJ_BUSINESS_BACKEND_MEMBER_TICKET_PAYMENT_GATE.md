# W7TP XiaoJ Business Backend Member Ticket Payment Gate

## Position

This gate is the P1-safe checkpoint before any formal POS/payment path. It only builds a dry-run packet for staff review.

Packet:

`W7TP_XIAOJ_BUSINESS_BACKEND_MEMBER_TICKET_PAYMENT_GATE_PACKET_V1`

Odoo model:

`wuchang.business.backend.member.ticket.payment.gate`

Action/menu:

`Build Member Ticket Payment Gate`

## Scope

The gate joins these refs before payment:

- member authority ref and state
- ticket, entitlement, voucher, and happiness coin refs and states
- cart and Odoo product refs
- product/menu quality ref and state
- price ref
- custom options ref
- real or staff-approved photo evidence ref
- consent ref and state

No member plaintext, token, secret, raw audio, raw video, card data, or external payload is allowed. Use refs, states, hashes, and placeholders only.

## Decision

`ALLOW_DRYRUN` means the candidate can continue as a dry-run review packet only.

`HOLD` means at least one ref/state is not strong enough.

`REJECT` means the operator asked for an unsafe payment action or the gate found a hard boundary issue.

Product/menu quality must be `pass`, `approved`, or `ready`; otherwise the gate is `HOLD`.

Generated image only is not accepted as product photo evidence. It must remain `HOLD` until real or staff-approved photo evidence exists.

## P1 Safety

This implementation must not perform payment capture, ticket redemption, refund, POS write, production DB write, external API call, deploy, restart, or Odoo upgrade.

The runtime packet carries side-effect flags and every flag must be false:

- secret_read
- member_plaintext_read
- raw_audio_saved
- db_write
- pos_write
- payment_capture
- ticket_redeem
- external_api_call
- service_restart
- deploy

## Review Flow

1. Staff creates or opens a gate record.
2. Staff fills refs and states only.
3. Staff clicks `Build Member Ticket Payment Gate`.
4. Odoo computes blockers and writes `packet_json`, `packet_hash`, `final_gate_decision`, and `pre_payment_gate_state`.
5. Staff reviews the packet before any future formal checkout implementation.
