#!/usr/bin/env python3
"""Deterministic 15-component lookup and exhaustive 15-bit ranking.

No AI, skin, morph, bone, or runtime deformation is used as a decision input.
The only selection core is a replayable integer mask lookup.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import shutil
import sys
import traceback

import cv2
import numpy as np
import trimesh


CANDIDATE = Path(__file__).resolve().parents[1]
SOURCE = Path("/home/taiji_admin/Taiji_Hub/products/xiaoj_3d_local_20260812")
RAW_GLB = SOURCE / "assets/xiaoj_single_core_geometry.glb"
REFERENCE_DIR = SOURCE / "assets/references"
EXPECTED = {
    RAW_GLB: "5d9d07e55d5d1515537e9ba73ed677659cff362b9b282ad318694ef55cbcf44a",
    REFERENCE_DIR / "front.png": "2dfcb9a25ba13ad9edfb6dc90c3f05daffe69634117528f588cd00e98361dd40",
    REFERENCE_DIR / "left.png": "176bfa518013c68d9abd03271b5cfc7c0efe34f1bd2c909398302e90b56ac645",
    REFERENCE_DIR / "back.png": "a5e244749813a22036d38b46dab4524004d00e834107415b1843f8214e9105b6",
    REFERENCE_DIR / "identity_anchor.png": "5232a0f17c1589b8eced2233b6a0198fe07de253e9b574acc900f6a70ec194e9",
}
WIDTH, HEIGHT = 128, 192
VIEW_NAMES = ("front", "left", "back")


def sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeError(f"APPEND_ONLY_COLLISION:{path}")
    path.write_bytes(payload)


def copy_new(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"APPEND_ONLY_COLLISION:{destination}")
    shutil.copyfile(source, destination)


def mask_to_bits(mask: np.ndarray) -> int:
    packed = np.packbits(mask.astype(np.uint8).reshape(-1), bitorder="little")
    return int.from_bytes(packed.tobytes(), "little")


def bits_to_mask(bits: int) -> np.ndarray:
    byte_count = (WIDTH * HEIGHT + 7) // 8
    packed = np.frombuffer(bits.to_bytes(byte_count, "little"), dtype=np.uint8)
    return np.unpackbits(packed, bitorder="little")[: WIDTH * HEIGHT].reshape(HEIGHT, WIDTH).astype(np.uint8)


def write_mask_png(path: Path, mask: np.ndarray) -> None:
    ok, encoded = cv2.imencode(".png", mask.astype(np.uint8) * 255)
    if not ok:
        raise RuntimeError(f"PNG_ENCODE_FAILED:{path}")
    write_new(path, encoded.tobytes())


def reference_mask(path: Path, view: str) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"REFERENCE_READ_FAILED:{path}")
    height, width = image.shape[:2]
    if view == "left":
        rect = (int(width * .29), int(height * .01), int(width * .43), int(height * .97))
    else:
        rect = (int(width * .19), int(height * .01), int(width * .62), int(height * .97))
    labels = np.zeros((height, width), dtype=np.uint8)
    background_model = np.zeros((1, 65), dtype=np.float64)
    foreground_model = np.zeros((1, 65), dtype=np.float64)
    cv2.setRNGSeed(0)
    cv2.grabCut(image, labels, rect, background_model, foreground_model, 5, cv2.GC_INIT_WITH_RECT)
    foreground = np.logical_or(labels == cv2.GC_FGD, labels == cv2.GC_PR_FGD).astype(np.uint8)
    count, components, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    if count <= 1:
        raise RuntimeError(f"REFERENCE_SEGMENTATION_EMPTY:{path}")
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    foreground = (components == largest).astype(np.uint8)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)
    return cv2.resize(foreground, (WIDTH, HEIGHT), interpolation=cv2.INTER_NEAREST).astype(np.uint8)


def project_vertices(vertices: np.ndarray, view: str, global_bounds: np.ndarray) -> np.ndarray:
    minimum, maximum = global_bounds
    if view == "front":
        horizontal, low, high = vertices[:, 0], minimum[0], maximum[0]
    elif view == "back":
        horizontal, low, high = -vertices[:, 0], -maximum[0], -minimum[0]
    else:
        horizontal, low, high = -vertices[:, 2], -maximum[2], -minimum[2]
    x = np.rint((horizontal - low) / max(float(high - low), 1e-12) * (WIDTH - 5) + 2).astype(np.int32)
    y = np.rint((maximum[1] - vertices[:, 1]) / max(float(maximum[1] - minimum[1]), 1e-12) * (HEIGHT - 5) + 2).astype(np.int32)
    return np.stack((np.clip(x, 0, WIDTH - 1), np.clip(y, 0, HEIGHT - 1)), axis=1)


def rasterize_component(projected: np.ndarray, faces: np.ndarray) -> np.ndarray:
    mask = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    triangles = projected[faces]
    chunk_size = 20_000
    for start in range(0, len(triangles), chunk_size):
        cv2.fillPoly(mask, list(triangles[start : start + chunk_size]), 1)
    return mask


def graph_floating_count(selection: int, adjacency: list[int]) -> int:
    remaining = selection
    groups = 0
    while remaining:
        groups += 1
        seed = remaining & -remaining
        frontier = seed
        visited = 0
        while frontier:
            current = frontier & -frontier
            frontier ^= current
            index = current.bit_length() - 1
            visited |= current
            frontier |= adjacency[index] & remaining & ~visited
        remaining &= ~visited
    return max(0, groups - 1)


def component_payload(component_id: str, face_ids: np.ndarray, mesh: trimesh.Trimesh, masks: dict[str, np.ndarray]) -> dict:
    vertex_ids = np.unique(mesh.faces[face_ids].reshape(-1)).astype(np.int64)
    positions = np.asarray(mesh.vertices[vertex_ids], dtype=np.float32)
    canonical = b"".join(
        (
            vertex_ids.astype("<i8").tobytes(),
            positions.astype("<f4").tobytes(),
            face_ids.astype("<i8").tobytes(),
            np.asarray(mesh.faces[face_ids], dtype="<u4").tobytes(),
        )
    )
    bounds = np.asarray((positions.min(axis=0), positions.max(axis=0)), dtype=np.float64)
    projection = {}
    for view in VIEW_NAMES:
        path = CANDIDATE / "tables/component_masks" / component_id / f"{view}.png"
        write_mask_png(path, masks[view])
        projection[view] = {
            "path": str(path.relative_to(CANDIDATE)),
            "pixel_count": int(masks[view].sum()),
            "raw_mask_sha256": sha_bytes(masks[view].tobytes()),
            "png_sha256": sha_file(path),
        }
    return {
        "component_id": component_id,
        "vertex_range": {"min": int(vertex_ids.min()), "max": int(vertex_ids.max()), "count": int(len(vertex_ids)), "contiguous": bool(vertex_ids.max() - vertex_ids.min() + 1 == len(vertex_ids))},
        "triangle_range": {"min": int(face_ids.min()), "max": int(face_ids.max()), "count": int(len(face_ids)), "contiguous": bool(face_ids.max() - face_ids.min() + 1 == len(face_ids))},
        "flat_index_range": {"min": int(face_ids.min() * 3), "max_exclusive": int((face_ids.max() + 1) * 3), "referenced_count": int(len(face_ids) * 3)},
        "local_frame": {"origin": ((bounds[0] + bounds[1]) / 2).tolist(), "axes": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "bounds": bounds.tolist()},
        "component_hash": sha_bytes(canonical),
        "projection_masks": projection,
    }


def main() -> None:
    for path, expected in EXPECTED.items():
        if not path.is_file():
            raise RuntimeError(f"SOURCE_MISSING:{path}")
        actual = sha_file(path)
        if actual != expected:
            raise RuntimeError(f"SOURCE_HASH_MISMATCH:{path}:{actual}:{expected}")

    copy_new(RAW_GLB, CANDIDATE / "evidence/source/xiaoj_original.glb")
    for name in ("front.png", "left.png", "back.png", "identity_anchor.png"):
        copy_new(REFERENCE_DIR / name, CANDIDATE / "evidence/references" / name)
    for relative in (
        "diagnostics/raw_views/front.png", "diagnostics/raw_views/left.png", "diagnostics/raw_views/back.png",
        "diagnostics/action_views/stand.png", "diagnostics/action_views/sit.png", "diagnostics/action_views/walk.png",
        "diagnostics/action_views/jog.png", "diagnostics/action_views/jump.png",
        "receipts/PASS_REVOCATION_RECEIPT.json", "receipts/LOCAL_VALIDATION_RECEIPT.json", "receipts/BROWSER_SMOKE_RECEIPT.json",
    ):
        source_path = SOURCE / relative
        if source_path.is_file():
            copy_new(source_path, CANDIDATE / "evidence/prior_failure" / Path(relative).name)

    scene = trimesh.load(RAW_GLB, force="scene", process=False)
    mesh = trimesh.util.concatenate(tuple(scene.geometry.values()))
    vertices = np.asarray(mesh.vertices, dtype=np.float32)
    faces = np.asarray(mesh.faces, dtype=np.uint32)
    face_groups = trimesh.graph.connected_components(mesh.face_adjacency, nodes=np.arange(len(faces)), min_len=1, engine="scipy")
    face_groups = sorted((np.sort(group.astype(np.int64)) for group in face_groups), key=lambda group: (-len(group), int(group.min())))
    if len(face_groups) != 15:
        raise RuntimeError(f"COMPONENT_COUNT_NOT_15:{len(face_groups)}")

    global_bounds = np.asarray((vertices.min(axis=0), vertices.max(axis=0)), dtype=np.float64)
    projected = {view: project_vertices(vertices, view, global_bounds) for view in VIEW_NAMES}
    component_masks: list[dict[str, np.ndarray]] = []
    component_rows = []
    for index, face_ids in enumerate(face_groups):
        component_id = f"C{index:02d}"
        masks = {view: rasterize_component(projected[view], faces[face_ids]) for view in VIEW_NAMES}
        component_masks.append(masks)
        component_rows.append(component_payload(component_id, face_ids, mesh, masks))

    anchor_hash = EXPECTED[REFERENCE_DIR / "identity_anchor.png"]
    lookup_key_payload = {
        "schema": "w7tp.component-table.v1",
        "source_glb_sha256": EXPECTED[RAW_GLB],
        "identity_anchor_sha256": anchor_hash,
        "component_hashes": [row["component_hash"] for row in component_rows],
    }
    component_table = {
        "schema": "w7tp.component-table.v1",
        "decision_core": "DISCRETE_LOOKUP_ONLY",
        "source_glb": {"absolute_path": str(RAW_GLB), "sha256": EXPECTED[RAW_GLB], "mode": "READ_ONLY"},
        "identity_anchor_lineage": {"absolute_path": str(REFERENCE_DIR / "identity_anchor.png"), "sha256": anchor_hash, "role": "PRIMARY_KEY_LINEAGE"},
        "lookup_primary_key": sha_bytes(canonical_json(lookup_key_payload)),
        "projection": {"width": WIDTH, "height": HEIGHT, "pixel_arithmetic": "INTEGER_BINARY"},
        "component_count": len(component_rows),
        "components": component_rows,
    }
    write_new(CANDIDATE / "tables/component_table.json", canonical_json(component_table))

    ref_masks = {view: reference_mask(REFERENCE_DIR / f"{view}.png", view) for view in VIEW_NAMES}
    ref_bits = {view: mask_to_bits(ref_masks[view]) for view in VIEW_NAMES}
    for view in VIEW_NAMES:
        write_mask_png(CANDIDATE / "evidence/masks/reference" / f"{view}.png", ref_masks[view])

    component_bits = {view: [mask_to_bits(masks[view]) for masks in component_masks] for view in VIEW_NAMES}
    adjacency = [0] * 15
    kernel = np.ones((3, 3), np.uint8)
    dilated = [{view: cv2.dilate(component_masks[index][view], kernel, iterations=1) for view in VIEW_NAMES} for index in range(15)]
    for left in range(15):
        for right in range(left + 1, 15):
            touches = any(bool(np.any(dilated[left][view] & component_masks[right][view])) for view in VIEW_NAMES)
            if touches:
                adjacency[left] |= 1 << right
                adjacency[right] |= 1 << left

    rankings = []
    for selection in range(1, 1 << 15):
        unions = {}
        selected = [index for index in range(15) if selection & (1 << index)]
        for view in VIEW_NAMES:
            union = 0
            for index in selected:
                union |= component_bits[view][index]
            unions[view] = union
        intersection = {view: (unions[view] & ref_bits[view]).bit_count() for view in VIEW_NAMES}
        candidate_area = {view: unions[view].bit_count() for view in VIEW_NAMES}
        reference_area = {view: ref_bits[view].bit_count() for view in VIEW_NAMES}
        union_area = {view: (unions[view] | ref_bits[view]).bit_count() for view in VIEW_NAMES}
        overflow = {view: (unions[view] & ~ref_bits[view]).bit_count() for view in VIEW_NAMES}
        missed = {view: (ref_bits[view] & ~unions[view]).bit_count() for view in VIEW_NAMES}
        iou_ppm = {view: intersection[view] * 1_000_000 // max(1, union_area[view]) for view in VIEW_NAMES}
        coverage_ppm = {view: intersection[view] * 1_000_000 // max(1, reference_area[view]) for view in VIEW_NAMES}
        consistency = max(coverage_ppm.values()) - min(coverage_ppm.values())
        floating = graph_floating_count(selection, adjacency)
        symmetric_difference = sum(overflow.values()) + sum(missed.values())
        rank_key = [symmetric_difference, sum(overflow.values()), floating, consistency, -sum(iou_ppm.values()), len(selected), selection]
        rankings.append({
            "selection_integer": selection,
            "selection_bits": format(selection, "015b"),
            "component_ids": [f"C{index:02d}" for index in selected],
            "rank_key": rank_key,
            "metrics": {"intersection_pixels": intersection, "union_pixels": union_area, "overflow_pixels": overflow, "missed_pixels": missed, "candidate_pixels": candidate_area, "reference_pixels": reference_area, "iou_ppm": iou_ppm, "coverage_ppm": coverage_ppm, "floating_regions": floating, "three_view_consistency_ppm_span": consistency, "symmetric_difference_pixels": symmetric_difference},
            "union_bits": unions,
        })

    rankings.sort(key=lambda item: tuple(item["rank_key"]))
    ranking_path = CANDIDATE / "ranking/full_ranking.jsonl"
    ranking_path.parent.mkdir(parents=True, exist_ok=True)
    if ranking_path.exists():
        raise RuntimeError(f"APPEND_ONLY_COLLISION:{ranking_path}")
    with ranking_path.open("xb") as stream:
        for rank, item in enumerate(rankings, 1):
            public_item = {key: value for key, value in item.items() if key != "union_bits"}
            public_item["rank"] = rank
            stream.write(canonical_json(public_item))

    best = rankings[0]
    best_selected = [index for index in range(15) if best["selection_integer"] & (1 << index)]
    selected_faces = np.sort(np.concatenate([face_groups[index] for index in best_selected])).astype(np.int64)
    used_vertices = np.unique(faces[selected_faces].reshape(-1)).astype(np.int64)
    remap = np.full(len(vertices), -1, dtype=np.int64)
    remap[used_vertices] = np.arange(len(used_vertices), dtype=np.int64)
    candidate_mesh = trimesh.Trimesh(vertices=vertices[used_vertices], faces=remap[faces[selected_faces]], process=False)
    candidate_path = CANDIDATE / "candidate/xiaoj_reference_aligned_candidate.glb"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    if candidate_path.exists():
        raise RuntimeError(f"APPEND_ONLY_COLLISION:{candidate_path}")
    candidate_path.write_bytes(trimesh.exchange.gltf.export_glb(trimesh.Scene(candidate_mesh), include_normals=True))

    original_bits = {}
    for view in VIEW_NAMES:
        union = 0
        for bits in component_bits[view]:
            union |= bits
        original_bits[view] = union
        original_mask = bits_to_mask(union)
        candidate_mask = bits_to_mask(best["union_bits"][view])
        reference = ref_masks[view]
        write_mask_png(CANDIDATE / "evidence/masks/original" / f"{view}.png", original_mask)
        write_mask_png(CANDIDATE / "evidence/masks/candidate" / f"{view}.png", candidate_mask)
        difference = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        overlap = (candidate_mask & reference).astype(bool)
        candidate_only = (candidate_mask & (1-reference)).astype(bool)
        reference_only = (reference & (1-candidate_mask)).astype(bool)
        difference[overlap] = [70, 190, 90]
        difference[candidate_only] = [40, 70, 235]
        difference[reference_only] = [235, 90, 50]
        ok, encoded = cv2.imencode(".png", difference)
        if not ok:
            raise RuntimeError(f"DIFF_PNG_FAILED:{view}")
        write_new(CANDIDATE / "evidence/masks/difference" / f"{view}.png", encoded.tobytes())

    baseline_hash = sha_file(candidate_path)
    best_public = {key: value for key, value in best.items() if key != "union_bits"}
    best_public.update({
        "schema": "w7tp.reference-aligned-candidate-selection.v1",
        "rank": 1,
        "candidate_glb": {"path": str(candidate_path.relative_to(CANDIDATE)), "sha256": baseline_hash, "bytes": candidate_path.stat().st_size},
        "identity_anchor_lineage_sha256": anchor_hash,
        "decision": "HOLD_HUMAN_REVIEW",
        "identity_pass": False,
    })
    write_new(CANDIDATE / "ranking/best_candidate.json", canonical_json(best_public))

    controls = []
    for state_key in (
        "BASE_NEUTRAL", "EMOTION_JOY_1", "EMOTION_JOY_2", "EMOTION_JOY_3",
        "EMOTION_ANGER_1", "EMOTION_ANGER_2", "EMOTION_ANGER_3",
        "EMOTION_SADNESS_1", "EMOTION_SADNESS_2", "EMOTION_SADNESS_3",
        "EMOTION_HAPPINESS_1", "EMOTION_HAPPINESS_2", "EMOTION_HAPPINESS_3",
        "VISEME_A", "VISEME_E", "VISEME_I", "VISEME_O", "VISEME_U", "VISEME_M",
        "ACTION_SIT", "ACTION_RISE", "ACTION_WALK", "ACTION_JOG", "ACTION_JUMP",
    ):
        base = state_key == "BASE_NEUTRAL"
        controls.append({
            "state_key": state_key,
            "source_hash": baseline_hash,
            "coordinate_domain": "LOCKED_CANDIDATE_VERTEX_INDEX" if base else None,
            "deterministic_transform": "IDENTITY" if base else None,
            "vertex_delta": "ZERO" if base else None,
            "bounds": {"max_abs_delta": 0.0},
            "reset_method": "RELOAD_BASELINE_HASH",
            "result_hash": baseline_hash if base else None,
            "evidence": "ranking/best_candidate.json" if base else None,
            "status": "PENDING_HUMAN_ACCEPTANCE" if base else "UNSUPPORTED_NO_OP",
        })
    control_lookup = {
        "schema": "w7tp.control-lookup.v1",
        "version": "1.0.0-candidate",
        "lookup_key": component_table["lookup_primary_key"],
        "topology_lock": {"candidate_sha256": baseline_hash, "selection_integer": best["selection_integer"], "status": "PENDING_HUMAN_ACCEPTANCE"},
        "decision_core": "STATE_KEY_TO_DETERMINISTIC_REPLAY_RESULT",
        "runtime_eligible": False,
        "controls": controls,
    }
    write_new(CANDIDATE / "contracts/control_lookup.json", canonical_json(control_lookup))

    float_contract = {
        "schema": "w7tp.adi-float-contract.v1",
        "version": "1.0.0-candidate",
        "current_policy": "ZERO_ONLY_AND_HOLD",
        "prerequisites": ["LOOKUP_STATE_HIT", "HUMAN_ACCEPTED_BASE", "TABLE_CONTROLLED", "RUNTIME_ELIGIBLE"],
        "protected_fields": ["lookup_key", "identity", "topology", "component_membership", "decision_index", "evidence_lineage"],
        "residual": {"allowed": False, "type": "float32", "finite_only": True, "min": 0.0, "max": 0.0, "clamp": "ZERO", "nan": "ZERO_AND_HOLD", "positive_infinity": "ZERO_AND_HOLD", "negative_infinity": "ZERO_AND_HOLD"},
        "offline_ai_candidate": {"allowed": True, "activation": "ONLY_AFTER_VALIDATION_AND_HASH_FREEZE_IN_CONTROL_LOOKUP"},
        "runtime_ai": {"allowed": False, "reason": "STATE_NOT_RUNTIME_ELIGIBLE"},
    }
    write_new(CANDIDATE / "contracts/float_contract.json", canonical_json(float_contract))

    transition_lines = [
        {"sequence": 1, "from": None, "to": "CREATED", "result": "PASS", "evidence": "candidate directory created"},
        {"sequence": 2, "from": "CREATED", "to": "RAW_VALIDATED", "result": "PASS", "evidence": {"source_sha256": EXPECTED[RAW_GLB], "component_count": 15}},
        {"sequence": 3, "from": "RAW_VALIDATED", "to": "REFERENCE_ALIGNED_CANDIDATE", "result": "PASS", "evidence": {"selection_integer": best["selection_integer"], "ranking_count": len(rankings), "candidate_sha256": baseline_hash}},
        {"sequence": 4, "from": "REFERENCE_ALIGNED_CANDIDATE", "to": "HUMAN_ACCEPTED_BASE", "result": "HOLD_HUMAN_REVIEW", "state_changed": False, "identity_pass": False},
    ]
    write_new(CANDIDATE / "receipts/transition_receipts.jsonl", b"".join(canonical_json(line) for line in transition_lines))

    isolation = {
        "schema": "w7tp.failure-isolation.v1",
        "source_root": str(SOURCE),
        "source_mode": "READ_ONLY",
        "disabled_in_candidate": ["arbitrary_scale", "external_fake_binding", "unbounded_vertex_deformation", "runtime_ai", "formal_entry_modification"],
        "preserved_failure_directory": "evidence/prior_failure",
        "candidate_runtime": "ABSENT",
        "status": "PASS_ISOLATED",
    }
    write_new(CANDIDATE / "receipts/A_FAILURE_ISOLATION_RECEIPT.json", canonical_json(isolation))

    summary = {
        "schema": "w7tp.discrete-enumeration-receipt.v1",
        "state": "REFERENCE_ALIGNED_CANDIDATE",
        "component_count": 15,
        "enumerated_nonempty_masks": 32767,
        "ranking_arithmetic": "INTEGER_ONLY",
        "ai_used_for_component_decision": False,
        "best_selection_integer": best["selection_integer"],
        "best_selection_bits": best["selection_bits"],
        "best_component_ids": best["component_ids"],
        "best_rank_key": best["rank_key"],
        "candidate_sha256": baseline_hash,
        "identity_anchor_lineage_sha256": anchor_hash,
        "identity_pass": False,
        "decision": "HOLD_HUMAN_REVIEW",
        "unique_next_state": "HUMAN_ACCEPTED_BASE",
    }
    write_new(CANDIDATE / "receipts/C_ENUMERATION_RECEIPT.json", canonical_json(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        failure = {
            "schema": "w7tp.append-only-failure.v1",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "state": "HOLD_BUILD_ERROR",
        }
        receipts = CANDIDATE / "receipts"
        receipts.mkdir(parents=True, exist_ok=True)
        sequence = len(list(receipts.glob("FAILURE_*.json"))) + 1
        failure_path = receipts / f"FAILURE_{sequence:04d}.json"
        failure_path.write_bytes(canonical_json(failure))
        print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
        raise
