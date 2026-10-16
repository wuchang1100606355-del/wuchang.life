#!/usr/bin/env python3
"""Proof of R1 creator-labeled smile channels in true 3D; candidate-only.

Reuses existing W7TP GLB/skin/camera primitives. Semantic source is the actual
asset's morphTargetNames, not guessed mouth vertices or projected pixel gaps.
"""
from __future__ import annotations
import hashlib,json,math,tempfile,zipfile
from pathlib import Path
import gltf_spatiotemporal_field as field

R1_ARCHIVE_SHA256="12a84759315263f1d39c6dec0fb1e0debf0ee34cb90277fdd21090aadc0b70b9"
R1_ASSET_SHA256="98986d8e96a9822494172043c463cda35268289fb3e0b97b7656bb94076c7ca2"
R1_MEMBER="XiaoJ_AV_R1/assets/xiaoj_chatavatar_uniform_r1.glb"
def require(condition,reason):
    if not condition:raise field.Hold(reason)

def evaluate_r1(archive_path):
    p=Path(archive_path)
    require(hashlib.sha256(p.read_bytes()).hexdigest()==R1_ARCHIVE_SHA256,
            "HOLD_R1_DELIVERY_IDENTITY_CHANGED")
    with zipfile.ZipFile(p) as z, tempfile.TemporaryDirectory(prefix="w7tp_r1_smile_") as folder:
        require(R1_MEMBER in z.namelist(),"HOLD_R1_ASSET_MISSING")
        raw=z.read(R1_MEMBER)
        require(hashlib.sha256(raw).hexdigest()==R1_ASSET_SHA256,
                "HOLD_R1_ASSET_SHA_MISMATCH")
        temp=Path(folder)/"R1_HAPPY_INSPECT_ONLY.glb";temp.write_bytes(raw)
        doc,blob,sha=field.load_glb(temp)
    skins=doc.get("skins",[])
    require(len(skins)==1 and len(skins[0].get("joints",[]))==57,
            "HOLD_R1_SKIN_JOINT_COUNT_CHANGED")
    meshid=next((i for i,m in enumerate(doc.get("meshes",[]))
                 if "mouthSmileLeft" in (m.get("extras") or {}).get("targetNames",[])
                 and "mouthSmileRight" in (m.get("extras") or {}).get("targetNames",[])),None)
    require(meshid is not None,"HOLD_R1_SMILE_SEMANTIC_TARGET_MISSING")
    nodeid=next((i for i,n in enumerate(doc["nodes"])
                 if n.get("mesh")==meshid and n.get("skin")==0),None)
    require(nodeid is not None,"HOLD_R1_FACE_NODE_SKIN_MISSING")
    mesh=doc["meshes"][meshid]
    primid=next((i for i,pr in enumerate(mesh.get("primitives",[]))
                 if doc["materials"][pr.get("material",0)].get("name")=="M_Face"),None)
    require(primid is not None,"HOLD_R1_M_FACE_PRIMITIVE_MISSING")
    pr=mesh["primitives"][primid]
    names=mesh["extras"]["targetNames"]
    lid,rid=names.index("mouthSmileLeft"),names.index("mouthSmileRight")
    require(lid!=rid,"HOLD_SEMANTIC_TARGET_ALIAS")
    base=field.accessor(doc,blob,pr["attributes"]["POSITION"])
    ld=field.accessor(doc,blob,pr["targets"][lid]["POSITION"])
    rd=field.accessor(doc,blob,pr["targets"][rid]["POSITION"])
    used={int(e[0]) for e in field.accessor(doc,blob,pr["indices"])}
    require(used and len(base)==len(ld)==len(rd),"HOLD_R1_FACE_MORPH_VERTEX_COUNT")
    def magnitude(x):return field.dist(x,(0,0,0))
    dominant_l=max(used,key=lambda k:magnitude(ld[k]))
    dominant_r=max(used,key=lambda k:magnitude(rd[k]))
    require(dominant_l!=dominant_r,"HOLD_R1_ANCHOR_PAIR_COLLISION")
    require(magnitude(ld[dominant_l])>0.005 and magnitude(rd[dominant_r])>0.005,
            "HOLD_R1_SMILE_MORPH_NO_MOVEMENT")
    # Verify left/right shape channels are distinct and side-dominant in this
    # exact asset; never infer a generic anatomical mouth-corner certificate.
    require(magnitude(ld[dominant_l])>4*magnitude(rd[dominant_l]) and
            magnitude(rd[dominant_r])>4*magnitude(ld[dominant_r]),
            "HOLD_R1_SMILE_CHANNELS_NOT_SEPARABLE")

    joints=skins[0]["joints"]
    inv=field.accessor(doc,blob,skins[0]["inverseBindMatrices"])
    require(len(inv)==len(joints),"HOLD_R1_INVERSE_BIND_COUNT")
    J=field.accessor(doc,blob,pr["attributes"]["JOINTS_0"])
    W=field.accessor(doc,blob,pr["attributes"]["WEIGHTS_0"])
    pose,_,_=field.skeleton_pose(doc)
    def skinned(i,weight_l,weight_r):
        p=field.add(base[i],field.add(field.mul(ld[i],weight_l),field.mul(rd[i],weight_r)))
        output=(0.,0.,0.);weight_sum=0.
        for joint_index,weight in zip(J[i],W[i]):
            if weight<=0:continue
            require(int(joint_index)<len(joints),"HOLD_R1_SKIN_JOINT_INDEX")
            T=field.matmul(pose[joints[int(joint_index)]],inv[int(joint_index)])
            output=field.add(output,field.mul(field.apply(T,p),weight))
            weight_sum+=weight
        require(weight_sum>0,"HOLD_R1_UNSKINNED_SMILE_VERTEX")
        return field.mul(output,1/weight_sum)
    bind_error=max(field.dist(skinned(k,0,0),base[k])
                   for k in (dominant_l,dominant_r))
    require(bind_error<1e-4,"HOLD_R1_FACE_BIND_POSE_MISMATCH")
    timeline=[]
    cameras=(("front",(0.,1.42,2.4)),("side",(2.4,1.42,0.)),
             ("oblique",(1.7,2.,1.7)))
    for time_ms in (0,163,325,487,650):
        weight=field.ease(time_ms/650)
        A=skinned(dominant_l,weight,weight)
        B=skinned(dominant_r,weight,weight)
        gap=field.dist(A,B)
        target=field.mul(field.add(A,B),0.5)
        views=[]
        for label,camera in cameras:
            left=field.camera_project(A,camera,target)
            right=field.camera_project(B,camera,target)
            gap_cam=field.dist(left["camera_xyz"],right["camera_xyz"])
            error=max(left["roundtrip_error_world"],right["roundtrip_error_world"])
            require(abs(gap_cam-gap)<1e-9 and error<1e-9,
                    "HOLD_R1_3D_MULTIVIEW_INCONSISTENCY")
            views.append({"camera":label,"pixel_gap_diagnostic_only":
                          math.dist(left["pixels"],right["pixels"]),
                          "true_camera_3d_distance":gap_cam,"reprojection_error":error})
        entry={"time_ms":time_ms,"weight":weight,
               "left_representative_vertex_xyz":A,
               "right_representative_vertex_xyz":B,
               "absolute_distance_3d":gap,"views":views}
        if timeline:
            prev=timeline[-1]
            entry["distance_change_speed_model_units_per_s"]=1000*(gap-prev["absolute_distance_3d"])/(time_ms-prev["time_ms"])
        timeline.append(entry)
    require(timeline[-1]["absolute_distance_3d"]>timeline[0]["absolute_distance_3d"],
            "HOLD_R1_SMILE_GEOMETRY_NOT_WIDENED")
    return {
      "schema":"W7TP_3D_SEMANTIC_MORPH_PROBE/1.0-CANDIDATE",
      "asset":"XiaoJ_AV_R1/xiaoj_chatavatar_uniform_r1.glb",
      "asset_sha256":sha,"archive_sha256":R1_ARCHIVE_SHA256,
      "mesh":mesh.get("name"),"face_material":"M_Face",
      "rig_joint_count":len(joints),"existing_animation_clips":len(doc.get("animations",[])),
      "source_semantic_controls":{"mouthSmileLeft":lid,"mouthSmileRight":rid},
      "dominant_morph_response_point_ids":{"mouthSmileLeft":dominant_l,
                                           "mouthSmileRight":dominant_r},
      "dominant_response_points_are_verified_anatomical_mouth_corners":False,
      "semantic_target_names_verified_from_asset":True,
      "model_units_not_claimed_as_physical_cm":True,
      "world_rest_pose_skinning_error_max":bind_error,
      "timeline":timeline,
      "source_authority":"MODEL_CREATOR_NAMED_MORPH_CHANNELS",
      "authority":"CANDIDATE_ONLY_NO_D8",
      "real_runtime_playback_verified":False,
      "source_asset_modified":False
    }

if __name__=="__main__":
    import sys
    print(json.dumps(evaluate_r1(sys.argv[1]),ensure_ascii=False,sort_keys=True))
