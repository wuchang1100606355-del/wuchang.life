# taiji01 Odoo/Postgres 唯讀盤點

timestamp: 2026-06-02T00:29:35+08:00
host: MSI
whoami: taiji_admin

## Governance
readonly_inventory: PASS
db_login: NO
db_write: NO
secret_read: NO
service_restart: NO
docker_mutation: NO

## Docker Containers
NAMES                             IMAGE                                                             STATUS       PORTS
wuchang_os_odoo_18                odoo:18.0                                                         Up 2 hours   127.0.0.1:8069->8069/tcp, 8071-8072/tcp
xiaoj-intent-field                wuchang/xiaoj-intent-field:dev                                    Up 2 hours   0.0.0.0:9107->9107/tcp, [::]:9107->9107/tcp
wuchang_os_pg                     postgres:15                                                       Up 2 hours   5432/tcp
taiji_syslog                      alpine:latest                                                     Up 2 hours   
taiji_worklist                    alpine:latest                                                     Up 2 hours   
taiji_audit                       alpine:latest                                                     Up 2 hours   
taiji_progress                    alpine:latest                                                     Up 2 hours   
taiji_voice_gateway               taiji_voice_gateway:local                                         Up 2 hours   127.0.0.1:9201->9201/tcp
taiji_device_resilience_adapter   taiji_device_resilience_adapter-taiji_device_resilience_adapter   Up 2 hours   
taiji_pos_google_voice_tool       taiji_pos_google_voice_tool-taiji_pos_google_voice_tool           Up 2 hours   
taiji_claw_safe                   taiji_claw_safe-taiji_claw_safe                                   Up 2 hours   127.0.0.1:9004->9004/tcp
wuchang_gpu_brain                 ollama/ollama:latest                                              Up 2 hours   11434/tcp

## Safe Inspect: Odoo
Name=/wuchang_os_odoo_18
Image=odoo:18.0
Status=running
StartedAt=2026-06-01T14:25:36.180942488Z
RestartCount=0
Networks={"taiji_odoo_default":{"IPAMConfig":null,"Links":null,"Aliases":["wuchang_os_odoo_18","wuchang_os_odoo_18"],"DriverOpts":null,"GwPriority":0,"NetworkID":"82f451bc1aecd92f4e0e9b32e789a3905079bef98f86c577a1265b6cc412f372","EndpointID":"5030ca87f0eb7c584d4f584d32080d01e896c283e3ff7375266ce68d57165db5","Gateway":"172.18.0.1","IPAddress":"172.18.0.2","MacAddress":"6e:75:b3:7d:a8:7a","IPPrefixLen":16,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["wuchang_os_odoo_18","bf1ee4239294"]}}

## Safe Inspect: Postgres
Name=/wuchang_os_pg
Image=postgres:15
Status=running
StartedAt=2026-06-01T14:25:36.198223889Z
RestartCount=0
Networks={"taiji_odoo_default":{"IPAMConfig":null,"Links":null,"Aliases":["wuchang_os_pg","wuchang_os_pg"],"DriverOpts":null,"GwPriority":0,"NetworkID":"82f451bc1aecd92f4e0e9b32e789a3905079bef98f86c577a1265b6cc412f372","EndpointID":"4c5c606c0ad9b63a692d41430e50a1f699a7c99b72afdd45bca52b61f537e6c7","Gateway":"172.18.0.1","IPAddress":"172.18.0.3","MacAddress":"1a:de:e2:09:a1:2f","IPPrefixLen":16,"IPv6Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"DNSNames":["wuchang_os_pg","7c0d4754f643"]}}

## Volumes / Mounts Metadata Only
Type=bind Source=/home/taiji_admin/Taiji_Hub/Taiji_Odoo/config/odoo.conf Destination=/etc/odoo/odoo.conf RW=false
Type=bind Source=/home/taiji_admin/Taiji_Hub/Taiji_Odoo/addons Destination=/mnt/extra-addons RW=true
Type=bind Source=/mnt/c/Taiji_Runtime Destination=/mnt/taiji_runtime RW=false
Type=bind Source=/home/taiji_admin/Taiji_Hub/Taiji_Odoo/odoo_data Destination=/var/lib/odoo RW=true

Type=bind Source=/home/taiji_admin/Taiji_Hub/Taiji_Odoo/postgres_data Destination=/var/lib/postgresql/data RW=true


## Images
REPOSITORY                                                        TAG                       IMAGE ID       CREATED       SIZE
wuchang/xiaoj-intent-field                                        dev                       29b14db84bdc   3 days ago    225MB
taiji_claw_container-wuchang_claw                                 latest                    ac574d0f2e10   4 weeks ago   383MB
postgres                                                          15                        29342cb52157   5 weeks ago   633MB
odoo                                                              18.0                      065a3fd327e6   5 weeks ago   3.14GB

## Decision
odoo_pg_inventory: PASS_READONLY
real_cutover_ready: NO
next_gate: rollback_snapshot_plan + no_secret_linter + human_review
