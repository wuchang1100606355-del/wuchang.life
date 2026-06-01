# Domain Governance Map

| Domain | Governance meaning | Scope |
| --- | --- | --- |
| `wuchang.life` | root organization domain | governed identity and policy |
| `gov.wuchang.life` | public-interest governance | association governance |
| `community.wuchang.life` | community services | public services and community industry |
| `audit.wuchang.life` | audit visibility | audit metadata only |
| `cafe.wuchang.life` | community/private cafe service boundary | must be scoped |
| `order.wuchang.life` | ordering endpoint | POS/order gateway |
| `line.wuchang.life` | LINE ordering node | line_order_gateway |
| `pos.wuchang.life` | POS service | POS runtime |
| `gateway.wuchang.life` | governed ingress | Taiji Gateway |
| `taiji.wuchang.life` | runtime governance | tensor runtime |
| `ai.wuchang.life` | AI service interface | redacted/local/governed AI |

ASUS DDNS or fixed IP may support fallback/development/emergency ingress, but must not become the legal identity boundary.
