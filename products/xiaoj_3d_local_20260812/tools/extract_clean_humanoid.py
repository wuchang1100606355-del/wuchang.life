#!/usr/bin/env python3
"""Extract the single human component from the quarantined raw Stage1 GLB.

The source is read-only. Selection is constrained by explicit humanoid geometry
criteria and fails closed unless exactly one component matches.
"""
from pathlib import Path
import argparse, hashlib, json
import trimesh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--receipt", type=Path, required=True)
args = parser.parse_args()

source_scene = trimesh.load(args.source, force="scene", process=False)
aggregate = trimesh.util.concatenate(tuple(source_scene.geometry.values()))
components = aggregate.split(only_watertight=False)
ranked = sorted(components, key=lambda item: len(item.faces), reverse=True)

matches = []
for rank, component in enumerate(ranked):
    x, y, z = map(float, component.extents)
    humanoid_shape = 1.8 <= y <= 2.1 and 0.55 <= x <= 0.9 and 0.35 <= z <= 0.65
    humanoid_density = 250_000 <= len(component.faces) <= 450_000
    if humanoid_shape and humanoid_density and component.is_watertight:
        matches.append((rank, component))

if len(matches) != 1:
    raise SystemExit(f"HOLD_AMBIGUOUS_HUMANOID_COMPONENT: matches={len(matches)}")

selected_rank, human = matches[0]
human.remove_unreferenced_vertices()
human.fix_normals()
args.output.parent.mkdir(parents=True, exist_ok=True)
clean_scene = trimesh.Scene(human)
args.output.write_bytes(trimesh.exchange.gltf.export_glb(clean_scene, include_normals=True))

receipt = {
    "schema": "w7tp.local-3d.clean-humanoid-extraction.v1",
    "source": {"path": str(args.source), "sha256": sha256(args.source)},
    "source_component_count": len(ranked),
    "component_face_counts": [int(len(item.faces)) for item in ranked],
    "selection": {
        "rank": selected_rank,
        "faces": int(len(human.faces)),
        "vertices": int(len(human.vertices)),
        "bounds": human.bounds.tolist(),
        "extents": human.extents.tolist(),
        "watertight": bool(human.is_watertight),
        "criteria_match_count": len(matches),
    },
    "rejected_background_component_faces": int(len(ranked[0].faces)),
    "rejected_small_fragment_faces": int(sum(len(item.faces) for item in ranked[2:])),
    "output": {"path": str(args.output), "sha256": sha256(args.output), "bytes": args.output.stat().st_size},
    "pass": True,
}
args.receipt.parent.mkdir(parents=True, exist_ok=True)
args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, ensure_ascii=False, indent=2))
