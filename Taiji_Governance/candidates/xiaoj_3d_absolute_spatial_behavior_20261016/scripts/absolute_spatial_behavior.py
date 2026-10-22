#!/usr/bin/env python3
"""Read-only 3D geometry sampler for existing W7TP avatar skills. Candidate only.
Uses exact model-space xyz distances and existing VRM morph targets. It does not
identify mouth landmarks without externally verified vertex-ID evidence.
"""
from __future__ import annotations
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Sequence

SCHEMA = "W7TP_3D_ABSOLUTE_SPATIAL_BEHAVIOR_CANDIDATE_V1"

class SpatialHold(ValueError):
    pass

def point3(value: Sequence[float]) -> tuple[float, float, float]:
    if not isinstance(value, (tuple,list)) or len(value) != 3:
        raise SpatialHold("HOLD_3D_POINT_REQUIRED")
    result = tuple(float(n) for n in value)
    if not all(math.isfinite(n) for n in result):
        raise SpatialHold("HOLD_NONFINITE_3D_POINT")
    return result

def distance3(a: Sequence[float], b: Sequence[float]) -> float:
    x,y = point3(a), point3(b)
    return math.sqrt(sum((x[i] - y[i]) ** 2 for i in range(3)))

def deform3(base: Sequence[float], delta: Sequence[float], weight: float) -> tuple[float,float,float]:
    base, delta = point3(base),point3(delta)
    if not isinstance(weight, (int,float)) or not math.isfinite(weight) or not 0 <= weight <= 1:
        raise SpatialHold("HOLD_MORPH_WEIGHT_INVALID")
    return tuple(base[i] + weight * delta[i] for i in range(3))

def smoothstep(t: float) -> float:
    if not math.isfinite(t) or not 0 <= t <= 1:
        raise SpatialHold("HOLD_TIMELINE_RANGE_INVALID")
    return t*t*(3 - 2*t)

def sample_pair(base_a, base_b, delta_a, delta_b, *, time_ms: int, duration_ms: int, intensity: float = 1):
    if not isinstance(duration_ms,int) or duration_ms <= 0 or not isinstance(time_ms,int) or not 0 <= time_ms <= duration_ms:
        raise SpatialHold("HOLD_TIMELINE_INVALID")
    if not isinstance(intensity,(float,int)) or not math.isfinite(intensity) or not 0 <= intensity <= 1:
        raise SpatialHold("HOLD_INTENSITY_INVALID")
    w = smoothstep(time_ms/duration_ms)*intensity
    a,b=deform3(base_a,delta_a,w),deform3(base_b,delta_b,w)
    return {"time_ms":time_ms,"weight":round(w,8),
            "xyz_a":list(a),"xyz_b":list(b),
            "absolute_distance_3d":distance3(a,b)}

def read_glb(path: str|Path):
    data=Path(path).read_bytes()
    if len(data)<28:
        raise SpatialHold("HOLD_GLB_TRUNCATED")
    magic,version,declared=struct.unpack_from("<4sII",data,0)
    if magic!=b"glTF" or version!=2 or declared!=len(data):
        raise SpatialHold("HOLD_GLB_CONTAINER_INVALID")
    cursor=12
    json_doc=None; bin_chunk=None
    while cursor+8<=len(data):
        n,kind=struct.unpack_from("<I4s",data,cursor)
        if cursor+8+n>len(data):
            raise SpatialHold("HOLD_GLB_CHUNK_BOUNDS")
        chunk=data[cursor+8:cursor+8+n]
        if kind==b"JSON":json_doc=json.loads(chunk.decode("utf-8").rstrip(" \x00"))
        elif kind==b"BIN\x00":bin_chunk=chunk
        cursor+=8+n
    if not isinstance(json_doc,dict) or bin_chunk is None:
        raise SpatialHold("HOLD_GLB_REQUIRED_CHUNKS")
    return json_doc,bin_chunk,hashlib.sha256(data).hexdigest()

def accessor_vec3(doc, raw:bytes, idx:int):
    acc=doc["accessors"][idx]
    if acc.get("componentType")!=5126 or acc.get("type")!="VEC3" or "sparse" in acc or "bufferView" not in acc:
        raise SpatialHold("HOLD_UNSUPPORTED_3D_ACCESSOR")
    view=doc["bufferViews"][acc["bufferView"]]
    if view.get("buffer",0)!=0:
        raise SpatialHold("HOLD_EXTERNAL_BUFFER_REQUIRED")
    stride=view.get("byteStride",12)
    if stride<12:
        raise SpatialHold("HOLD_VERTEX_STRIDE_INVALID")
    start=view.get("byteOffset",0)+acc.get("byteOffset",0)
    result=[]
    for i in range(acc["count"]):
        off=start+i*stride
        if off+12>len(raw):
            raise SpatialHold("HOLD_ACCESSOR_OUT_OF_BOUNDS")
        result.append(point3(struct.unpack_from("<fff",raw,off)))
    return result

def sample_vrm_absolute_3d(path, *, expression:str, primitive:int,
                           vertex_a:int,vertex_b:int,duration_ms:int=650,
                           times_ms=(0,325,650), semantic_binding=None):
    doc,raw,sha=read_glb(path)
    # Expression bindings and mesh identifiers are source facts, not guesses.
    vrm=doc.get("extensions",{}).get("VRMC_vrm",{})
    bind=vrm.get("expressions",{}).get("preset",{}).get(expression,{}).get("morphTargetBinds",[])
    if len(bind)!=1:
        raise SpatialHold("HOLD_EXPRESSION_BINDING_UNRESOLVED")
    binding=bind[0]; node_id=binding["node"]; mesh_id=doc["nodes"][node_id].get("mesh")
    if mesh_id is None:
        raise SpatialHold("HOLD_EXPRESSION_MESH_UNRESOLVED")
    mesh=doc["meshes"][mesh_id]
    if not isinstance(primitive,int) or not 0<=primitive<len(mesh["primitives"]):
        raise SpatialHold("HOLD_MESH_PRIMITIVE_INVALID")
    prim=mesh["primitives"][primitive]
    target_id=binding["index"]
    if target_id>=len(prim.get("targets",[])) or "POSITION" not in prim["targets"][target_id]:
        raise SpatialHold("HOLD_MORPH_POSITION_UNAVAILABLE")
    points=accessor_vec3(doc,raw,prim["attributes"]["POSITION"])
    deltas=accessor_vec3(doc,raw,prim["targets"][target_id]["POSITION"])
    if len(points)!=len(deltas) or vertex_a==vertex_b or any(not isinstance(i,int) or not 0<=i<len(points) for i in (vertex_a,vertex_b)):
        raise SpatialHold("HOLD_VERTEX_PAIR_INVALID")
    # A caller-supplied evidence string is not verified semantic provenance.
    # Semantic mouth landmarks require an independent, governed binding verifier.
    if semantic_binding is not None:
        raise SpatialHold("HOLD_SEMANTIC_CONTROL_POINT_INDEPENDENT_PROOF_REQUIRED")
    frames=[sample_pair(points[vertex_a],points[vertex_b],deltas[vertex_a],deltas[vertex_b],
                        time_ms=t,duration_ms=duration_ms,intensity=float(binding.get("weight",1.0))) for t in times_ms]
    for prior,current in zip(frames,frames[1:]):
        if current["time_ms"]<=prior["time_ms"]:
            raise SpatialHold("HOLD_NONMONOTONIC_TIMELINE")
        current["distance_change_rate_per_second"]=(current["absolute_distance_3d"]-prior["absolute_distance_3d"])*1000/(current["time_ms"]-prior["time_ms"])
    return {
      "schema":SCHEMA,"state":"CANDIDATE_GEOMETRY_MEASURED",
      "source_sha256":sha,"source_file":Path(path).name,"node_id":node_id,"mesh_id":mesh_id,"primitive_id":primitive,
      "target_index":target_id,"expression":expression,"vertex_ids":[vertex_a,vertex_b],
      "semantic_label":"UNVERIFIED_VERTEX_PAIR",
      "semantic_control_points_verified":False,
      "coordinate_basis":"GLTF_MESH_BIND_SPACE_XYZ","distance_unit":"MODEL_COORDINATE_UNIT_UNCALIBRATED",
      "posed_world_coordinate_status":"HOLD_SKINNING_POSE_NOT_EVALUATED" if "skin" in doc["nodes"][node_id] else "STATIC_MESH_SPACE_ONLY",
      "projection_used":False,"distance_formula":"EUCLIDEAN_XYZ",
      "timeline":frames,"authority":"CANDIDATE_ONLY","source_write":False,"runtime_write":False,"rendered":False,
    }
