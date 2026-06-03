#!/usr/bin/env bash
set -euo pipefail

ROOT="${TAIJI_ROOT:-$HOME/Taiji_Hub}"
cd "$ROOT" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p \
  topology/community_3d_map \
  data/community_3d_map/source \
  data/community_3d_map/derived \
  configs \
  runtime/ledger \
  runtime/reports \
  runtime/dead_letter

GEOJSON="data/community_3d_map/source/wuchang_community_jurisdiction_anchor_2026-05-12.geojson"
INDEX="topology/community_3d_map/spatial_index.json"
SUMMARY="data/community_3d_map/derived/community_3d_map_memory_summary.md"
MANIFEST="topology/community_3d_map/manifest.json"

if [ ! -f "$GEOJSON" ]; then
  echo "missing: $GEOJSON"
  echo "先確認 anchored 步驟是否完成。"
  exit 1
fi

python3 - <<'PY'
from pathlib import Path
import json, hashlib, datetime

geo = Path("data/community_3d_map/source/wuchang_community_jurisdiction_anchor_2026-05-12.geojson")
index = Path("topology/community_3d_map/spatial_index.json")
summary = Path("data/community_3d_map/derived/community_3d_map_memory_summary.md")
manifest = Path("topology/community_3d_map/manifest.json")

def walk_coords(obj, acc):
    if isinstance(obj, list):
        if len(obj) >= 2 and all(isinstance(x, (int, float)) for x in obj[:2]):
            acc.append((obj[0], obj[1]))
        else:
            for x in obj:
                walk_coords(x, acc)

raw = geo.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
data = json.loads(raw.decode("utf-8"))

features = data.get("features", []) if data.get("type") == "FeatureCollection" else []
geom_types = {}
coords = []

for f in features:
    g = f.get("geometry") or {}
    gt = g.get("type", "Unknown")
    geom_types[gt] = geom_types.get(gt, 0) + 1
    walk_coords(g.get("coordinates"), coords)

bbox = None
if coords:
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    bbox = {
        "min_lng": min(xs),
        "min_lat": min(ys),
        "max_lng": max(xs),
        "max_lat": max(ys)
    }

idx = {
    "id": "wuchang_community_3d_map_spatial_index",
    "created_at": datetime.datetime.now().astimezone().isoformat(),
    "fusion_state": "indexed",
    "fusion_level": 2,
    "source_geojson": str(geo),
    "source_sha256": sha,
    "feature_count": len(features),
    "geometry_types": geom_types,
    "bbox": bbox,
    "privacy_default": "mask_household_identity",
    "gateway_required": True,
    "dead_letter": "runtime/dead_letter/routing_rejected.jsonl",
    "allowed_use": [
        "local_query",
        "topology_reference",
        "property_case_context",
        "community_guidance",
        "disaster_prevention_planning"
    ],
    "denied_use": [
        "publish_personal_location_without_review",
        "infer_sensitive_household_identity",
        "external_upload_without_human_approval"
    ]
}

index.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

summary.write_text(f"""# 五常社區 3D 地圖記憶摘要

狀態：indexed  
層級：fusion_level 2  
來源：{geo}  
SHA256：{sha}  
Feature count：{len(features)}  
Geometry types：{geom_types}  
Bounding box：{bbox}

用途：
- 社區空間記憶
- 物業脈絡
- 路線脈絡
- 防災規劃
- 文化地理脈絡
- Gateway 拓樸參照

隱私規則：
- 家戶身分預設遮罩
- 個人位置需人工審核
- 不可未審核對外發布
- 高風險任務進 routing_rejected.jsonl

目前說明：
本階段已融入 GeoJSON 社區邊界/管轄錨點並完成空間索引。
尚未匯入完整 3D mesh、GLB、tileset 或建物模型。
""", encoding="utf-8")

if manifest.exists():
    m = json.loads(manifest.read_text(encoding="utf-8"))
else:
    m = {"id": "wuchang_community_3d_map"}

m["fusion_state"] = "indexed"
m["fusion_level"] = 2
m["spatial_index"] = str(index)
m["memory_summary"] = str(summary)
m["updated_at"] = datetime.datetime.now().astimezone().isoformat()
manifest.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
PY

python3 - <<'PY'
from pathlib import Path
p = Path("configs/community_3d_map_topology.yaml")
if p.exists():
    s = p.read_text(encoding="utf-8")
    s = s.replace("fusion_state: anchored", "fusion_state: indexed")
    s = s.replace("fusion_state: prepared", "fusion_state: indexed")
    s = s.replace("fusion_level: 1", "fusion_level: 2")
    p.write_text(s, encoding="utf-8")
PY

sha256sum \
  "$GEOJSON" \
  "$INDEX" \
  "$SUMMARY" \
  "$MANIFEST" \
  configs/community_3d_map_topology.yaml 2>/dev/null \
  | tee "runtime/reports/community_3d_map_indexed_${STAMP}.sha256"

printf '{"ts":"%s","event":"community_3d_map_spatial_index_created","fusion_state":"indexed","index":"%s","summary":"%s"}\n' \
  "$(date -Is)" \
  "$INDEX" \
  "$SUMMARY" \
  >> runtime/ledger/community_3d_map_events.jsonl

if [ -d /mnt/c/Taiji_Runtime ]; then
  mkdir -p /mnt/c/Taiji_Runtime/memory/community_3d_map
  cp -a "$INDEX" /mnt/c/Taiji_Runtime/memory/community_3d_map/ 2>/dev/null || true
  cp -a "$SUMMARY" /mnt/c/Taiji_Runtime/memory/community_3d_map/ 2>/dev/null || true
  cp -a "$MANIFEST" /mnt/c/Taiji_Runtime/memory/community_3d_map/ 2>/dev/null || true
  cp -a configs/community_3d_map_topology.yaml /mnt/c/Taiji_Runtime/memory/community_3d_map/ 2>/dev/null || true
fi

echo "=== community 3D map indexed ==="
cat "$MANIFEST"

echo
echo "=== latest ledger ==="
tail -n 5 runtime/ledger/community_3d_map_events.jsonl
