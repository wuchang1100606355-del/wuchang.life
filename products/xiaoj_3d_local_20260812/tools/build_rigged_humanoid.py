#!/usr/bin/env python3
"""Build a standards-based skinned GLB from the Stage1-clean humanoid.

The mesh is unchanged in bind pose. All coordinate transforms are explicit and
the receipt records joint bounds, normalized weights and bind-pose error.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import trimesh
from pygltflib import (
    GLTF2, Accessor, Asset, Attributes, Buffer, BufferView, Material, Mesh,
    Node, PbrMetallicRoughness, Primitive, Scene, Skin,
    ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER, FLOAT, UNSIGNED_BYTE, UNSIGNED_INT,
    SCALAR, VEC3, VEC4, MAT4, TRIANGLES,
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def pad4(blob: bytearray) -> None:
    blob.extend(b"\0" * ((-len(blob)) % 4))


def chain_weights(y: float, chain: list[tuple[int, float]]) -> list[tuple[int, float]]:
    descending = chain[0][1] > chain[-1][1]
    for (a, ya), (b, yb) in zip(chain, chain[1:]):
        within = yb <= y <= ya if descending else ya <= y <= yb
        if within:
            span = max(abs(ya - yb), 1e-8)
            toward_b = abs(y - ya) / span
            return [(a, 1.0 - toward_b), (b, toward_b)]
    return [(chain[0][0], 1.0)] if (y > chain[0][1]) == descending else [(chain[-1][0], 1.0)]


parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--receipt", type=Path, required=True)
args = parser.parse_args()

source_scene = trimesh.load(args.source, force="scene", process=False)
source_mesh = trimesh.util.concatenate(tuple(source_scene.geometry.values()))
source_mesh.remove_unreferenced_vertices()
source_mesh.fix_normals()
positions = np.asarray(source_mesh.vertices, dtype=np.float32)
normals = np.asarray(source_mesh.vertex_normals, dtype=np.float32)
indices = np.asarray(source_mesh.faces.reshape(-1), dtype=np.uint32)
minimum, maximum = positions.min(axis=0), positions.max(axis=0)

joint_specs = [
    ("Root", None, (0.0, float(minimum[1]), 0.0)),
    ("Hips", "Root", (0.0, 0.04, 0.0)),
    ("Spine", "Hips", (0.0, 0.25, 0.0)),
    ("Chest", "Spine", (0.0, 0.49, 0.0)),
    ("Neck", "Chest", (0.0, 0.69, 0.0)),
    ("Head", "Neck", (0.0, 0.84, 0.0)),
    ("Jaw", "Head", (0.0, 0.735, 0.115)),
    ("Shoulder.L", "Chest", (-0.235, 0.55, 0.0)),
    ("Elbow.L", "Shoulder.L", (-0.305, 0.27, 0.0)),
    ("Wrist.L", "Elbow.L", (-0.335, -0.015, 0.0)),
    ("Shoulder.R", "Chest", (0.235, 0.55, 0.0)),
    ("Elbow.R", "Shoulder.R", (0.305, 0.27, 0.0)),
    ("Wrist.R", "Elbow.R", (0.335, -0.015, 0.0)),
    ("Thigh.L", "Hips", (-0.135, 0.02, 0.0)),
    ("Knee.L", "Thigh.L", (-0.135, -0.44, 0.0)),
    ("Ankle.L", "Knee.L", (-0.135, -0.86, 0.0)),
    ("Foot.L", "Ankle.L", (-0.135, -0.97, 0.08)),
    ("Thigh.R", "Hips", (0.135, 0.02, 0.0)),
    ("Knee.R", "Thigh.R", (0.135, -0.44, 0.0)),
    ("Ankle.R", "Knee.R", (0.135, -0.86, 0.0)),
    ("Foot.R", "Ankle.R", (0.135, -0.97, 0.08)),
]
joint_index = {name: index for index, (name, _, _) in enumerate(joint_specs)}
global_positions = {name: np.asarray(position, dtype=np.float64) for name, _, position in joint_specs}

joints = np.zeros((len(positions), 4), dtype=np.uint8)
weights = np.zeros((len(positions), 4), dtype=np.float32)

def segment_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    axis = end - start
    denominator = float(np.dot(axis, axis))
    if denominator < 1e-12:
        return float(np.linalg.norm(point - start))
    position = float(np.clip(np.dot(point - start, axis) / denominator, 0.0, 1.0))
    return float(np.linalg.norm(point - (start + axis * position)))


def influence(name: str, start: str, end, radius: float):
    endpoint = global_positions[end] if isinstance(end, str) else np.asarray(end, dtype=np.float64)
    return (joint_index[name], global_positions[start], endpoint, radius)


torso_fields = [
    influence("Hips", "Hips", "Spine", .18), influence("Spine", "Spine", "Chest", .17),
    influence("Chest", "Chest", "Neck", .19), influence("Neck", "Neck", "Head", .13),
    influence("Head", "Head", (0.0, .96, 0.0), .20),
]
arm_fields = {
    -1: [influence("Shoulder.L", "Shoulder.L", "Elbow.L", .105), influence("Elbow.L", "Elbow.L", "Wrist.L", .095), influence("Wrist.L", "Wrist.L", (-.335, -.18, 0.0), .10)],
    1: [influence("Shoulder.R", "Shoulder.R", "Elbow.R", .105), influence("Elbow.R", "Elbow.R", "Wrist.R", .095), influence("Wrist.R", "Wrist.R", (.335, -.18, 0.0), .10)],
}
leg_fields = {
    -1: [influence("Thigh.L", "Thigh.L", "Knee.L", .15), influence("Knee.L", "Knee.L", "Ankle.L", .135), influence("Ankle.L", "Ankle.L", "Foot.L", .13), influence("Foot.L", "Foot.L", (-.135, -1.0, .20), .14)],
    1: [influence("Thigh.R", "Thigh.R", "Knee.R", .15), influence("Knee.R", "Knee.R", "Ankle.R", .135), influence("Ankle.R", "Ankle.R", "Foot.R", .13), influence("Foot.R", "Foot.R", (.135, -1.0, .20), .14)],
}

for vertex_index, raw_point in enumerate(positions):
    point = raw_point.astype(np.float64); x, y, z = point
    long_hair = .12 < y < .72 and z < -.105 and abs(x) < .32
    lower_face = .70 < y < .80 and z > .105 and abs(x) < .13
    if lower_face:
        assignments = [(joint_index["Jaw"], .82), (joint_index["Head"], .18)]
    elif long_hair:
        head_share = float(np.clip((y - .12) / .56, .18, .92))
        assignments = [(joint_index["Head"], head_share), (joint_index["Chest"], (1-head_share)*.68), (joint_index["Spine"], (1-head_share)*.32)]
    else:
        side = -1 if x < 0 else 1
        arm_zone = abs(x) > .19 and y > -.22
        if -.12 < y < .10 and not arm_zone:
            vertical = float(np.clip((.02-y)/.14, 0.0, 1.0))
            lateral = float(np.clip((abs(x)-.035)/.13, 0.0, 1.0))
            thigh_share = vertical*(.25+.75*lateral)
            thigh_name = "Thigh.L" if side < 0 else "Thigh.R"
            assignments = [(joint_index["Hips"], 1.0-thigh_share), (joint_index[thigh_name], thigh_share)]
        elif y < .10 and not arm_zone:
            fields = leg_fields[side] + [torso_fields[0]]
        else:
            fields = torso_fields + arm_fields[side]
        scored = []
        for bone, start, end, radius in fields:
            distance = segment_distance(point, start, end)
            score = float(np.exp(-.5 * (distance / radius) ** 2)) + 1e-12
            scored.append((bone, score))
        assignments = sorted(scored, key=lambda item: item[1], reverse=True)[:4]
    total = sum(float(weight) for _, weight in assignments)
    for slot, (bone, weight) in enumerate(assignments[:4]):
        joints[vertex_index, slot] = bone
        weights[vertex_index, slot] = float(weight) / total

# Reference-driven vertex palette: silver hair, Asian skin, white/blue hoodie,
# navy pants and white shoes. It adds appearance without modifying geometry.
colors = np.tile(np.array([238, 241, 246, 255], dtype=np.uint8), (len(positions), 1))
for i, (x, y, z) in enumerate(positions):
    if y < .055:
        colors[i] = [29, 54, 105, 255]
    if y < -.84:
        colors[i] = [230, 236, 246, 255]
        if -.96 < y < -.90:
            colors[i] = [31, 101, 214, 255]
    hand = abs(x) > .255 and -.19 < y < -.025
    face = y > .675 and z > .025 and abs(x) < .18
    neck = .61 < y < .72 and z > .015 and abs(x) < .115
    if hand or face or neck:
        colors[i] = [232, 177, 151, 255]
    elif y > .60 or (y > .12 and z < -.08 and abs(x) < .33):
        colors[i] = [221, 224, 238, 255]
    elif .03 < y < .12 and abs(x) < .34:
        colors[i] = [36, 104, 218, 255]

global_matrices = []
inverse_bind = []
for name, _, position in joint_specs:
    matrix = np.eye(4, dtype=np.float32)
    matrix[:3, 3] = np.asarray(position, dtype=np.float32)
    global_matrices.append(matrix)
    inverse_bind.append(np.linalg.inv(matrix).astype(np.float32))
global_matrices = np.asarray(global_matrices)
inverse_bind = np.asarray(inverse_bind)

blob = bytearray()
buffer_views, accessors = [], []

def append_accessor(data, component_type, accessor_type, target=None, normalized=False, include_bounds=False):
    pad4(blob); offset=len(blob); raw=np.ascontiguousarray(data).tobytes(); blob.extend(raw)
    view_index=len(buffer_views); buffer_views.append(BufferView(buffer=0,byteOffset=offset,byteLength=len(raw),target=target))
    kwargs={"bufferView":view_index,"byteOffset":0,"componentType":component_type,"count":len(data),"type":accessor_type,"normalized":normalized}
    if include_bounds:
        kwargs["min"]=np.min(data,axis=0).astype(float).tolist(); kwargs["max"]=np.max(data,axis=0).astype(float).tolist()
    accessor_index=len(accessors); accessors.append(Accessor(**kwargs)); return accessor_index

position_accessor=append_accessor(positions,FLOAT,VEC3,ARRAY_BUFFER,include_bounds=True)
normal_accessor=append_accessor(normals,FLOAT,VEC3,ARRAY_BUFFER)
color_accessor=append_accessor(colors,UNSIGNED_BYTE,VEC4,ARRAY_BUFFER,normalized=True)
joints_accessor=append_accessor(joints,UNSIGNED_BYTE,VEC4,ARRAY_BUFFER)
weights_accessor=append_accessor(weights,FLOAT,VEC4,ARRAY_BUFFER)
indices_accessor=append_accessor(indices,UNSIGNED_INT,SCALAR,ELEMENT_ARRAY_BUFFER,include_bounds=True)
ibm_accessor=append_accessor(np.asarray([m.T.reshape(-1) for m in inverse_bind],dtype=np.float32),FLOAT,MAT4)
pad4(blob)

nodes=[Node(name="XiaoJ_CleanHumanoid",mesh=0,skin=0)]
node_for_joint={name:index+1 for index,(name,_,_) in enumerate(joint_specs)}
for name,parent,position in joint_specs:
    if parent is None:
        local=np.asarray(position,dtype=float)
    else:
        local=np.asarray(position,dtype=float)-global_positions[parent]
    nodes.append(Node(name=name,translation=local.tolist()))
for name,parent,_ in joint_specs:
    children=[node_for_joint[child] for child,child_parent,_ in joint_specs if child_parent==name]
    nodes[node_for_joint[name]].children=children or None

primitive=Primitive(attributes=Attributes(POSITION=position_accessor,NORMAL=normal_accessor,COLOR_0=color_accessor,JOINTS_0=joints_accessor,WEIGHTS_0=weights_accessor),indices=indices_accessor,material=0,mode=TRIANGLES)
gltf=GLTF2(
    asset=Asset(version="2.0",generator="W7TP XiaoJ clean rig builder v1"),
    scene=0,
    scenes=[Scene(nodes=[0,node_for_joint["Root"]])],
    nodes=nodes,
    meshes=[Mesh(name="XiaoJ_CleanHumanoid_Mesh",primitives=[primitive])],
    skins=[Skin(name="XiaoJ_Humanoid_Skin",inverseBindMatrices=ibm_accessor,skeleton=node_for_joint["Root"],joints=[node_for_joint[name] for name,_,_ in joint_specs])],
    materials=[Material(name="XiaoJ_Reference_Vertex_Palette",doubleSided=False,pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=[1,1,1,1],metallicFactor=0.0,roughnessFactor=.78))],
    buffers=[Buffer(byteLength=len(blob))],bufferViews=buffer_views,accessors=accessors,
)
gltf.set_binary_blob(bytes(blob)); args.output.parent.mkdir(parents=True,exist_ok=True); gltf.save_binary(args.output)

weight_sums=weights.sum(axis=1)
bind_identity_error=max(float(np.max(np.abs(global_matrices[i]@inverse_bind[i]-np.eye(4)))) for i in range(len(joint_specs)))
sample_ids=np.linspace(0,len(positions)-1,min(5000,len(positions)),dtype=int)
rest_error=0.0
for vertex_id in sample_ids:
    point=np.append(positions[vertex_id],[1.0])
    skinned=np.zeros(4)
    for slot in range(4):
        weight=float(weights[vertex_id,slot])
        if weight: skinned += weight*(global_matrices[int(joints[vertex_id,slot])]@inverse_bind[int(joints[vertex_id,slot])]@point)
    rest_error=max(rest_error,float(np.linalg.norm(skinned[:3]-point[:3])))

receipt={
    "schema":"w7tp.local-3d.rig-build-receipt.v1",
    "source":{"path":str(args.source),"sha256":digest(args.source)},
    "output":{"path":str(args.output),"sha256":digest(args.output),"bytes":args.output.stat().st_size},
    "mesh":{"vertices":len(positions),"triangles":len(indices)//3,"bounds":[minimum.astype(float).tolist(),maximum.astype(float).tolist()]},
    "skin":{"joint_count":len(joint_specs),"joint_names":[name for name,_,_ in joint_specs],"joint_index_min":int(joints.min()),"joint_index_max":int(joints.max()),"weight_sum_min":float(weight_sums.min()),"weight_sum_max":float(weight_sums.max()),"nonfinite_weights":int((~np.isfinite(weights)).sum()),"inverse_bind_identity_max_error":bind_identity_error,"sampled_rest_pose_max_position_error":rest_error},
    "coordinate_space":"glTF right-handed, +Y up, mesh and bind globals in model space; IBM stored column-major",
    "pass":bool(joints.max()<len(joint_specs) and np.allclose(weight_sums,1,atol=1e-6) and bind_identity_error<1e-6 and rest_error<1e-6),
}
args.receipt.parent.mkdir(parents=True,exist_ok=True);args.receipt.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt,ensure_ascii=False,indent=2))
if not receipt["pass"]: raise SystemExit(1)
