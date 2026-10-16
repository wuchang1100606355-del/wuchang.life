#!/usr/bin/env python3
"""W7TP candidate: VRM/glTF 3D bone/face spatial behavior, no render or live write.

D3 application projection axes: up/down, left/right, front/back, centre
absolute distance, group relative distance, speed, time, human semantics.
These are NOT replacements for W7TP's coupled D1-D8 Total Field.
"""
from __future__ import annotations
import hashlib
import json
import math
import struct
from pathlib import Path

SCHEMA = "W7TP_XIAOJ_3D_SPATIOTEMPORAL_BEHAVIOR/1.0-CANDIDATE"
IDENTITY_SHA256 = "615f5ab25daab0fa326bfcf1c0e49d09c8f23dc8c9217d3876962937455cc205"

class Hold(ValueError): pass

def dist(a,b):
    if len(a)!=3 or len(b)!=3 or not all(math.isfinite(v) for v in (*a,*b)):
        raise Hold("HOLD_INVALID_ABSOLUTE_3D_COORDINATE")
    return math.dist(a,b)

def vdot(a,b): return sum(x*y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def add(a,b): return tuple(x+y for x,y in zip(a,b))
def mul(a,s): return tuple(x*s for x in a)
def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a):
    n=math.sqrt(vdot(a,a))
    if n < 1e-10: raise Hold("HOLD_ZERO_CAMERA_AXIS")
    return mul(a,1/n)
def ease(t):
    if not 0<=t<=1: raise Hold("HOLD_ANIMATION_TIME_RANGE")
    return t*t*(3-2*t)

def quatmul(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y,
            w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W,
            w*W-x*X-y*Y-z*Z)

def transform(q, tr=(0,0,0), scale=(1,1,1)):
    x,y,z,w=q
    size=math.sqrt(sum(a*a for a in q))
    if size<1e-12: raise Hold("HOLD_INVALID_BONE_QUATERNION")
    x,y,z,w=(v/size for v in (x,y,z,w))
    xx,yy,zz=x*x,y*y,z*z
    xy,xz,yz=x*y,x*z,y*z
    wx,wy,wz=w*x,w*y,w*z
    sx,sy,sz=scale
    return (
        (1-2*(yy+zz))*sx, 2*(xy+wz)*sx, 2*(xz-wy)*sx,0,
        2*(xy-wz)*sy,(1-2*(xx+zz))*sy,2*(yz+wx)*sy,0,
        2*(xz+wy)*sz,2*(yz-wx)*sz,(1-2*(xx+yy))*sz,0,
        tr[0],tr[1],tr[2],1
    )
I=(1.,0.,0.,0., 0.,1.,0.,0., 0.,0.,1.,0., 0.,0.,0.,1.)
def matmul(a,b):
    return tuple(sum(a[k*4+r]*b[c*4+k] for k in range(4)) for c in range(4) for r in range(4))
def apply(m,p):
    x,y,z=p
    w=m[3]*x+m[7]*y+m[11]*z+m[15]
    if abs(w)<1e-12: raise Hold("HOLD_NONAFFINE_3D_TRANSFORM")
    return ((m[0]*x+m[4]*y+m[8]*z+m[12])/w,
            (m[1]*x+m[5]*y+m[9]*z+m[13])/w,
            (m[2]*x+m[6]*y+m[10]*z+m[14])/w)

def load_glb(path):
    data=Path(path).read_bytes()
    if len(data)<20: raise Hold("HOLD_GLB_TRUNCATED")
    magic,ver,length=struct.unpack_from("<4sII",data,0)
    if (magic,ver,length)!=(b"glTF",2,len(data)): raise Hold("HOLD_GLB_HEADER")
    off=12; doc=None; blob=None
    while off+8<=len(data):
        n,k=struct.unpack_from("<I4s",data,off)
        if off+8+n>len(data): raise Hold("HOLD_GLB_CHUNK_BOUNDS")
        segment=data[off+8:off+8+n]
        if k==b"JSON":doc=json.loads(segment.decode("utf-8").rstrip(" \x00"))
        if k==b"BIN\x00":blob=segment
        off+=8+n
    if doc is None or blob is None: raise Hold("HOLD_GLB_MISSING_CHUNKS")
    return doc,blob,hashlib.sha256(data).hexdigest()

def accessor(doc, blob, idx):
    """Read bounded glTF 2.0 accessors, including sparse morph target values.

    The sparse path is necessary for the existing R1 model. Never silently use
    another mesh when the declared buffer, stride or sparse indices are invalid.
    """
    a=doc["accessors"][idx]
    fmt={5126:"f",5125:"I",5123:"H",5121:"B",5122:"h",5120:"b"}.get(a["componentType"])
    n={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}.get(a["type"])
    if fmt is None or n is None: raise Hold("HOLD_UNSUPPORTED_ACCESSOR")
    count=a.get("count")
    if not isinstance(count,int) or isinstance(count,bool) or count<0 or count>5000000:
        raise Hold("HOLD_ACCESSOR_COUNT_INVALID")
    frmt="<"+fmt*n; size=struct.calcsize(frmt)

    def extract(view_id, relative_offset, item_count, item_fmt, item_size, stride=None):
        try:
            view=doc["bufferViews"][view_id]
            vstart=view.get("byteOffset",0); vsize=view["byteLength"]
            if view.get("buffer",0)!=0: raise Hold("HOLD_EXTERNAL_BUFFER_NOT_LOADED")
            if not all(isinstance(x,int) and x>=0 for x in (vstart,vsize,relative_offset,item_count)):
                raise Hold("HOLD_ACCESSOR_BOUNDS")
            if stride is None:stride=item_size
            if not isinstance(stride,int) or stride<item_size:raise Hold("HOLD_ACCESSOR_STRIDE")
            off=vstart+relative_offset
            end=off+(item_count-1)*stride+item_size if item_count else off
            if off<vstart or end>vstart+vsize or end>len(blob):
                raise Hold("HOLD_ACCESSOR_BOUNDS")
            return [struct.unpack_from(item_fmt,blob,off+i*stride) for i in range(item_count)]
        except (KeyError,IndexError,TypeError,struct.error) as exc:
            raise Hold("HOLD_ACCESSOR_MALFORMED") from exc

    if "bufferView" in a:
        v=doc["bufferViews"][a["bufferView"]]
        arr=extract(a["bufferView"],a.get("byteOffset",0),count,frmt,size,v.get("byteStride",size))
    elif "sparse" in a:
        if a.get("byteOffset",0)!=0:raise Hold("HOLD_SPARSE_BASE_OFFSET_INVALID")
        arr=[tuple(0 for _ in range(n)) for _ in range(count)]
    else:
        raise Hold("HOLD_ACCESSOR_BUFFER_MISSING")

    sparse=a.get("sparse")
    if sparse is not None:
        sc=sparse.get("count")
        if not isinstance(sc,int) or isinstance(sc,bool) or sc<0 or sc>count:
            raise Hold("HOLD_SPARSE_COUNT_INVALID")
        i=sparse.get("indices",{});v=sparse.get("values",{})
        code={5121:"B",5123:"H",5125:"I"}.get(i.get("componentType"))
        if code is None:raise Hold("HOLD_SPARSE_INDEX_COMPONENT_INVALID")
        index_fmt="<"+code
        ids=[r[0] for r in extract(i["bufferView"],i.get("byteOffset",0),sc,index_fmt,struct.calcsize(index_fmt))]
        if any(k<0 or k>=count for k in ids) or any(x>=y for x,y in zip(ids,ids[1:])):
            raise Hold("HOLD_SPARSE_INDICES_UNSORTED_OR_INVALID")
        values=extract(v["bufferView"],v.get("byteOffset",0),sc,frmt,size)
        for k,value in zip(ids,values):
            arr[k]=value

    if a.get("normalized") and a["componentType"]!=5126:
        bits={5125:32,5123:16,5121:8,5122:16,5120:8}[a["componentType"]]
        signed=a["componentType"] in (5122,5120)
        maximum=(2**(bits-1)-1) if signed else (2**bits-1)
        arr=[tuple(max(-1.0,t/maximum) if signed else t/maximum for t in row) for row in arr]
    if a["componentType"]==5126 and any(not math.isfinite(c) for row in arr for c in row):
        raise Hold("HOLD_NONFINITE_GEOMETRY")
    return arr

def skeleton_pose(doc, *, joint_name=None, yaw_deg=0):
    nodes=doc["nodes"];parent={}
    for i,n in enumerate(nodes):
        for child in n.get("children",[]):
            if child in parent: raise Hold("HOLD_NON_TREE_SKELETON")
            parent[child]=i
    worlds={}; visiting=set()
    target=next((i for i,n in enumerate(nodes) if n.get("name")==joint_name),None) if joint_name else None
    if joint_name and target is None: raise Hold("HOLD_HEAD_BONE_MISSING")
    def walk(i):
        if i in worlds:return worlds[i]
        if i in visiting:raise Hold("HOLD_BONE_CYCLE")
        visiting.add(i);n=nodes[i]
        if i==target and yaw_deg:
            if "matrix" in n: raise Hold("HOLD_BONE_MATRIX_OVERRIDE_UNSUPPORTED")
            q=tuple(n.get("rotation",(0,0,0,1)))
            rad=math.radians(yaw_deg)
            q=quatmul(q,(0,math.sin(rad/2),0,math.cos(rad/2)))
            local=transform(q,n.get("translation",(0,0,0)),n.get("scale",(1,1,1)))
        elif "matrix" in n:
            local=tuple(n["matrix"])
        else:
            local=transform(n.get("rotation",(0,0,0,1)),n.get("translation",(0,0,0)),n.get("scale",(1,1,1)))
        worlds[i]=matmul(walk(parent[i]),local) if i in parent else local
        visiting.remove(i)
        return worlds[i]
    for i in range(len(nodes)):walk(i)
    return worlds,target,parent

def camera_project(point,camera,target,fx=800.0):
    forward=unit(sub(target,camera));right=unit(cross(forward,(0,1,0)));up=cross(right,forward)
    diff=sub(point,camera)
    x,y,z=vdot(diff,right),vdot(diff,up),vdot(diff,forward)
    if z<=0: raise Hold("HOLD_POINT_BEHIND_CAMERA")
    pixels=(fx*x/z,fx*y/z)
    recovered=add(camera,add(mul(right,pixels[0]*z/fx),add(mul(up,pixels[1]*z/fx),mul(forward,z))))
    return {"pixels":list(pixels),"depth":z,"backprojected_world_xyz":list(recovered),
            "roundtrip_error_world":dist(point,recovered),"camera_xyz":[x,y,z]}

def scan_gltf_skeletons(source):
    """Format-bounded static rig scan; no model identity assumption or runtime effect.

    The full 8-index motion evaluator is presently verified only for the
    identified MSI J.vrm. Generic glTF skins are source facts, not motion PASS.
    """
    doc,blob,sha=load_glb(source)
    pose,_,parent=skeleton_pose(doc)
    skins=[]
    for index,skin in enumerate(doc.get("skins",[])):
        bones=[]
        for jid in skin.get("joints",[]):
            bone=doc["nodes"][jid]
            p=apply(pose[jid],(0,0,0))
            bones.append({"node":jid,"name":bone.get("name"),"parent":parent.get(jid),
                          "world_bind_xyz":list(p),"source_local_quaternion":bone.get("rotation",(0,0,0,1))})
        digest=hashlib.sha256(json.dumps(bones,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        skins.append({"skin":index,"joint_count":len(bones),"joint_bind_positions":bones,"sha256":digest})
    return {"schema":SCHEMA,"source_sha256":sha,"format":"GLB_GLTF_2_0",
            "scan_state":"PASS_RIG_SOURCE_SCAN" if skins else "NO_SKELETON_PRESENT",
            "skins":skins,"has_mesh_geometry":bool(doc.get("meshes")),
            "rendered":False,"gesture_validated":False,"anatomical_landmarks_verified":False,
            "runtime_activated":False,"formal_d8_authority":False}

def measure(source,*,times_ms=(0,163,325,487,650),head_yaw_max_deg=12):
    doc,blob,sha=load_glb(source)
    if sha!=IDENTITY_SHA256: raise Hold("HOLD_SOURCE_MODEL_IDENTITY_MISMATCH")
    mesh_id=next((i for i,m in enumerate(doc["meshes"]) if m["name"].startswith("Face (")),None)
    if mesh_id is None:raise Hold("HOLD_FACE_MESH_UNVERIFIED")
    node_id=next((i for i,n in enumerate(doc["nodes"]) if n.get("mesh")==mesh_id and n.get("skin") is not None),None)
    if node_id is None:raise Hold("HOLD_FACE_SKIN_MISSING")
    skin=doc["skins"][doc["nodes"][node_id]["skin"]]
    joints=skin.get("joints",[]);inverse_bind=accessor(doc,blob,skin["inverseBindMatrices"])
    if len(joints)!=len(inverse_bind):raise Hold("HOLD_INVERSE_BIND_COUNT_MISMATCH")
    preset=doc["extensions"]["VRMC_vrm"]["expressions"]["preset"]["happy"]
    bind=preset["morphTargetBinds"]
    if len(bind)!=1 or bind[0]["node"]!=node_id or not 0<=bind[0]["weight"]<=1:
        raise Hold("HOLD_HAPPY_MORPH_BINDING_UNVERIFIED")
    expression_index=bind[0]["index"]
    mouth_id=next((i for i,p in enumerate(doc["meshes"][mesh_id]["primitives"])
        if "FaceMouth" in doc["materials"][p["material"]]["name"]),None)
    if mouth_id is None:raise Hold("HOLD_FACE_MOUTH_MATERIAL_NOT_FOUND")
    prim=doc["meshes"][mesh_id]["primitives"][mouth_id]
    positions=accessor(doc,blob,prim["attributes"]["POSITION"])
    deltas=accessor(doc,blob,prim["targets"][expression_index]["POSITION"])
    joins=accessor(doc,blob,prim["attributes"]["JOINTS_0"])
    weights=accessor(doc,blob,prim["attributes"]["WEIGHTS_0"])
    used={int(q[0]) for q in accessor(doc,blob,prim["indices"])}
    if not used or not len(positions)==len(deltas)==len(joins)==len(weights):
        raise Hold("HOLD_MOUTH_GEOMETRY_INVALID")
    left=min(used,key=lambda i:positions[i][0])
    right=max(used,key=lambda i:positions[i][0])
    head=next((i for i,n in enumerate(doc["nodes"]) if n.get("name")=="J_Bip_C_Head"),None)
    if head is None or head not in joints:raise Hold("HOLD_HEAD_JOINT_UNAVAILABLE")
    reference_pose,_,parent=skeleton_pose(doc)
    skeleton=[{"joint_node":node,"name":doc["nodes"][node].get("name"),"world_bind_xyz":list(apply(reference_pose[node],(0,0,0))),
               "parent_node":parent.get(node)} for node in joints]
    baseline_pair=dist(positions[left],positions[right])
    def skin_vertex(i, w, pose):
        local=add(positions[i],mul(deltas[i],w))
        total=(0.,0.,0.);tw=0.
        for joint,weight in zip(joins[i],weights[i]):
            if weight<=0:continue
            if not (0<=int(joint)<len(joints)):raise Hold("HOLD_BONE_JOINT_OUT_OF_RANGE")
            world=matmul(pose[joints[int(joint)]],inverse_bind[int(joint)])
            total=add(total,mul(apply(world,local),weight));tw+=weight
        if tw<=0:raise Hold("HOLD_UNSKINNED_MOUTH_VERTEX")
        return mul(total,1/tw)
    pose0=reference_pose
    bind_rest_errors=[dist(positions[i],skin_vertex(i,0,pose0)) for i in (left,right)]
    if max(bind_rest_errors)>1e-4:raise Hold("HOLD_SKIN_BIND_POSE_MISMATCH")
    camera_refs=[
        ("front",(0.,1.39,2.4)),("side",(2.4,1.39,0.)),("oblique",(1.7,2.1,1.7))]
    frames=[]
    baseline_center=apply(reference_pose[head],(0,0,0))
    prior=None
    for t in times_ms:
        if not isinstance(t,int) or t<0 or t>times_ms[-1]:
            raise Hold("HOLD_INVALID_FRAME_TIME")
        if prior and t<=prior["time_ms"]:raise Hold("HOLD_NONMONOTONIC_TIMELINE")
        fraction=ease(t/times_ms[-1]);yaw=head_yaw_max_deg*fraction
        pose,_,_=skeleton_pose(doc,joint_name="J_Bip_C_Head",yaw_deg=yaw)
        left_xyz=skin_vertex(left,bind[0]["weight"]*fraction,pose)
        right_xyz=skin_vertex(right,bind[0]["weight"]*fraction,pose)
        center=apply(pose[head],(0,0,0))
        measured=dist(left_xyz,right_xyz)
        views=[]
        target=mul(add(left_xyz,right_xyz),0.5)
        for name,camera in camera_refs:
            L=camera_project(left_xyz,camera,target);R=camera_project(right_xyz,camera,target)
            view_distance=dist(L["camera_xyz"],R["camera_xyz"])
            if abs(view_distance-measured)>1e-9 or max(L["roundtrip_error_world"],R["roundtrip_error_world"])>1e-9:
                raise Hold("HOLD_CAMERA_3D_CONSISTENCY_FAILED")
            views.append({"camera":name,"left_pixels":L["pixels"],"right_pixels":R["pixels"],
                          "pixel_gap":math.dist(L["pixels"],R["pixels"]),
                          "camera_distance_3d":view_distance,
                          "roundtrip_error_max":max(L["roundtrip_error_world"],R["roundtrip_error_world"])})
        frame={
          "time_ms":t,"human_semantic_ref":"VRM1:expression:happy",
          "x_left_right":[left_xyz[0],right_xyz[0]],
          "y_up_down":[left_xyz[1],right_xyz[1]],
          "z_front_back":[left_xyz[2],right_xyz[2]],
          "head_center_world_xyz":list(center),
          "center_absolute_distance_3d":[dist(center,left_xyz),dist(center,right_xyz)],
          "group_relative_distance_3d":measured,
          "morph_weight":bind[0]["weight"]*fraction,
          "head_yaw_deg":yaw,
          "head_center_to_baseline_center":dist(center,baseline_center),
          "view_reprojection_checks":views
        }
        if prior:
            delta=t-prior["time_ms"]
            L_old=tuple(prior["point_left_world"]);R_old=tuple(prior["point_right_world"])
            frame["velocity_3d_model_units_per_s"]={
                "left":dist(left_xyz,L_old)*1000/delta,
                "right":dist(right_xyz,R_old)*1000/delta,
                "distance_change":(measured-prior["group_relative_distance_3d"])*1000/delta
            }
        frame["point_left_world"]=list(left_xyz);frame["point_right_world"]=list(right_xyz)
        frames.append(frame);prior=frame
    return {
       "schema":SCHEMA,"state":"PASS_CANDIDATE_GEOMETRY_MATH_WITH_SEMANTIC_HOLD",
       "identity_sha256":sha,"model":Path(source).name,"input_mesh":"Face (merged)",
       "primitive":mouth_id,"material":doc["materials"][prim["material"]]["name"],
       "semantic_vertex_pair_type":"MOUTH_MATERIAL_X_EXTREMA_CANDIDATE_NOT_VERIFIED_ANATOMICAL_CORNERS",
       "left_vertex_id":left,"right_vertex_id":right,"baseline_mesh_local_gap":baseline_pair,
       "skeleton_joint_count":len(joints),"skeleton_geometry_sha256":hashlib.sha256(json.dumps(skeleton,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
       "skeleton_bind_positions":skeleton,
       "head_node_id":head,"bind_pose_skinning_error_max":max(bind_rest_errors),
       "original_gltf_mesh_normalization":"NO_UNPROVEN_UNIT_CONVERSION",
       "coordinate_basis":"WORLD_SPACE_GLTF_DEFAULT_POSE_HEAD_YAW_TESTED",
       "coordinate_unit":"SOURCE_GLTF_MODEL_COORDINATE_UNITS",
       "time_axis":"MONOTONIC_MS","semantic_ref":"VRM1:happy",
       "application_8_index":["y_up_down","x_left_right","z_front_back","center_absolute_distance_3d",
                              "group_relative_distance_3d","velocity_3d_model_units_per_s","time_ms","human_semantic_ref"],
       "canonical_8d_override":False,"observations":frames,
       "hold_landmark":"HOLD_ANATOMICAL_MOUTH_CORNERS_NOT_INDEPENDENTLY_VERIFIED",
       "source_write":False,"runtime_activated":False,"formal_d8_authority":False,
       "raw_model_bytes_in_result":False
    }

if __name__=="__main__":
    import sys
    print(json.dumps(measure(sys.argv[1]),ensure_ascii=False,sort_keys=True))
