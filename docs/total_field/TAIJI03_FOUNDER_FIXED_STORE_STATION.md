# TAIJI03 Founder Fixed Store Station

STATE=TAIJI03_FOUNDER_FIXED_STORE_STATION
NODE_ID=taiji03
NODE_CLASS=FOUNDER_FIXED_STORE_STATION
LOCATION_CLASS=STORE_FIXED_POINT
MOBILITY=NON_PORTABLE
OWNER_SCOPE=FOUNDER_PERSONAL_USE
DNS_POLICY=STATIC_DNS_ALLOWED
AUTHORITY_CLASS=HIGHEST_HUMAN_OPERATOR_CANDIDATE
PUBLIC_EXPOSURE=FORBIDDEN_UNLESS_SEPARATE_RELEASE_PACKET
MEMBER_PUBLIC_USE=FORBIDDEN
SECRET_DISCLOSURE=FORBIDDEN
DB_WRITE=HOLD_UNLESS_EXPLICIT_RUN_PACKET
DEPLOY=HOLD_UNLESS_EXPLICIT_RUN_PACKET
RESTART=HOLD_UNLESS_EXPLICIT_RUN_PACKET
ROUTER_WRITE=HOLD_UNLESS_EXPLICIT_RUN_PACKET

## Meaning

taiji03 is a fixed in-store founder-only operation station.

It may be assigned fixed DNS and high operational authority, but it must still obey Total Field governance:
- no plaintext secret leakage
- no member plaintext exposure
- no public network exposure without release packet
- no deploy/restart/DB write without explicit run evidence
- no bypass of 8D / Total Field verifier chain

## Recommended DNS Position

Preferred internal names:
- taiji03.lan
- taiji03.store.wuchang.life
- taiji03.internal.wuchang.life

Public exposure remains HOLD until a separate release packet.
