# Minimal Patch Plan

STATE=MINIMAL_PATCH_PLAN_CONVERGED

## Patch Target

Existing Odoo modules only:

1. `wuchang_member_registration`
2. `wuchang_core`
3. `wuchang_cafe_menu_options`
4. `wuchang_google_member_login`
5. `wuchang_line_login`

No sidecar, no standalone HTML demo, no Odoo core modification.

## Patch Step 1: Group Member 8D Registration

Status: patch-ready from prior step.

- Models: `wuchang.member.group.registration.batch`, `wuchang.member.group.registration.packet`
- Routes: `/wuchang/member/register/group/<packet_ref>` and claim/status/confirm dry-run
- Google/LINE callback continuity by `group_packet_ref`
- Requires operator module upgrade confirmation.

## Patch Step 2: Product GUI Route

Add to `wuchang_core` or a narrow existing Wuchang addon:

- Controller route: `/wuchang/xiaoj/ordering`
- JSON route: `/wuchang/xiaoj/ordering/candidate`
- JSON route: `/wuchang/xiaoj/ordering/confirm_dry_run`
- Static asset: Odoo-bundled GUI, not external server

Writes allowed in this step: none, except optional transient dry-run/evidence record if operator confirms.

## Patch Step 3: 8D Operation Registry

Add a static registry file or Odoo model after review:

- `menu.browse.v1`
- `order.candidate.create.v1`
- `order.candidate.validate.v1`
- `order.confirm.dry_run.v1`
- `member.group.register.v1`
- `voice.say_candidate.v1`
- `display.render_candidate.v1`
- `anchor.render_state.v1`
- `evidence.seal.v1`

## Patch Step 4: Voice And Anchor Adapter Interfaces

- SUNMI adapter interface, no production API call until operator provides API docs.
- Browser SpeechSynthesis fallback.
- Cloud anchor iframe/SDK placeholder with config key names only.

## Patch Step 5: Formal Gate

Only after evidence:

- authenticated staff role.
- replay-resistant `packet_ref`.
- Odoo recomputes totals.
- no payment capture without separate payment gate.

## Verification

```bash
python3 scripts/verify/verify_product_av_ordering_ai_convergence.py
```

## Rollback

- Remove docs under `docs/evidence/product_av_ordering_ai`.
- Remove specs under `packets/product_av_ordering_ai`.
- Remove verifier `scripts/verify/verify_product_av_ordering_ai_convergence.py`.
- Do not remove existing POS P2 or group member 8D patches unless rolling those back separately.

