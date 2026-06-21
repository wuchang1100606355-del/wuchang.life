# GT8D Local Lookup Rule

STATE=INTERNAL_RULE
RULE_CODE=GT8D_LOCAL_CODE_LOOKUP_ROUTING
AUTHORITY=local_code_table
LLM_ROUTE_GENERATION=NOT_REQUIRED
OPTIONAL_LLM_TABLE_SELECT=ALLOWED_FOR_AMBIGUOUS_INPUT
LOCAL_RECONSTRUCTION_REQUIRED=TRUE

Core rule:
- route_code and lookup_key are selected from local table.
- LLM may suggest lookup_key only when ambiguous.
- local code validates route_code and lookup_key.
- cloud may return candidate_result only.
- local node reconstructs, verifies, and decides whether to land.

Forbidden by default:
- SECRET_READ
- MEMBER_PLAINTEXT_READ
- TOKEN_PRINT
- DB_WRITE
- SERVICE_RESTART
- DEPLOY
- PRODUCTION_RELEASE
