#!/usr/bin/env python3
"""Bounded, side-effect-free tests. Real J.vrm tests require W7TP_XIAOJ_JVRM_PATH."""
import importlib.util
import hashlib
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

SRC=Path(__file__).resolve().parent/"gltf_spatiotemporal_field.py"
spec=importlib.util.spec_from_file_location("gltf_spatiotemporal_field",SRC)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REAL=Path(os.environ["W7TP_XIAOJ_JVRM_PATH"]) if os.environ.get("W7TP_XIAOJ_JVRM_PATH") else None

class PureThreeDimensionalGeometry(unittest.TestCase):
    def test_z_not_discarded(self): self.assertEqual(m.dist((0,0,0),(0,0,3)),3.0)
    def test_invalid_3d_rejected(self):
        for bad in ((0,0),(0,0,math.nan),(0,0,math.inf)):
            with self.subTest(bad=bad),self.assertRaises(m.Hold):
                m.dist((0,0,0),bad)
    def test_quaternion_rotation_preserves_true_distance(self):
        q=(0,math.sin(math.pi/4),0,math.cos(math.pi/4))
        M=m.transform(q)
        a,b=(1.,2.,3.),(4.,0.,-5.)
        self.assertAlmostEqual(m.dist(a,b),m.dist(m.apply(M,a),m.apply(M,b)),places=10)
    def test_relative_axis_and_velocity_have_distinct_dimensions(self):
        self.assertEqual(m.dist((0,0,0),(1,2,2)),3)
        self.assertEqual(m.dist((0,0,0),(0,0,2)),2)
    def test_camera_depth_and_projection(self):
        target=(0,0,0);pt=(0.2,0.3,0.4)
        for origin in ((0,0,3),(3,0,0),(3,3,3)):
            v=m.camera_project(pt,origin,target)
            self.assertLess(v["roundtrip_error_world"],1e-10)
    def test_bad_camera_behind_hold(self):
        with self.assertRaisesRegex(m.Hold,"HOLD_POINT_BEHIND_CAMERA"):
            m.camera_project((0,0,3),(0,0,2),(0,0,0))
    def test_smoothstep_endpoints_and_monotonicity(self):
        xs=[m.ease(x/100) for x in range(101)]
        self.assertEqual(xs[0],0);self.assertEqual(xs[-1],1)
        self.assertTrue(all(a<=b for a,b in zip(xs,xs[1:])))
    def test_glb_invalid_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"bad.glb";p.write_bytes(b"garbage")
            with self.assertRaisesRegex(m.Hold,"HOLD_GLB_TRUNCATED"):
                m.load_glb(p)
    def test_no_second_authority_or_eightfield_redefinition(self):
        self.assertIn("CANDIDATE",m.SCHEMA)
        self.assertFalse(hasattr(m,"grant_d8"))
    def test_matrix_identity_and_multiplication(self):
        M=m.transform((0,0,0,1),(2,3,4))
        self.assertEqual(m.apply(M,(1,2,3)),(3,5,7))
        self.assertEqual(m.apply(m.matmul(m.I,M),(1,2,3)),(3,5,7))

@unittest.skipIf(REAL is None, "Real VRM path not mounted on this node")
class RealModelAcceptances(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.out=m.measure(REAL)
    def test_real_170_bone_scan(self):
        o=self.out
        self.assertEqual(o["skeleton_joint_count"],170)
        self.assertEqual(len(o["skeleton_bind_positions"]),170)
        self.assertEqual(o["identity_sha256"],m.IDENTITY_SHA256)
        self.assertLess(o["bind_pose_skinning_error_max"],0.0001)
    def test_mouth_material_is_source_anchored_not_false_certified(self):
        o=self.out
        self.assertIn("FaceMouth",o["material"])
        self.assertIn("CANDIDATE",o["semantic_vertex_pair_type"])
        self.assertEqual(o["hold_landmark"],"HOLD_ANATOMICAL_MOUTH_CORNERS_NOT_INDEPENDENTLY_VERIFIED")
    def test_smile_true_absolute_3d(self):
        o=self.out;obs=o["observations"]
        self.assertEqual(len(obs),5)
        self.assertGreater(obs[-1]["group_relative_distance_3d"],obs[0]["group_relative_distance_3d"])
        for p in obs:
            self.assertAlmostEqual(m.dist(p["point_left_world"],p["point_right_world"]),p["group_relative_distance_3d"],places=10)
            self.assertEqual(len(p["point_left_world"]),3)
    def test_all_three_views_consistent_across_all_frames(self):
        for f in self.out["observations"]:
            cams=f["view_reprojection_checks"]
            self.assertEqual({c["camera"] for c in cams},{"front","side","oblique"})
            for c in cams:
                self.assertLess(abs(c["camera_distance_3d"]-f["group_relative_distance_3d"]),1e-9)
                self.assertLess(c["roundtrip_error_max"],1e-9)
            self.assertGreater(max(c["pixel_gap"] for c in cams)-min(c["pixel_gap"] for c in cams),0.1)
    def test_speed_and_time_axis(self):
        frames=self.out["observations"]
        self.assertEqual(frames[0]["time_ms"],0)
        self.assertEqual(frames[-1]["time_ms"],650)
        self.assertTrue(all(a["time_ms"]<b["time_ms"] for a,b in zip(frames,frames[1:])))
        self.assertTrue(any(f.get("velocity_3d_model_units_per_s",{}).get("left",0)>0 for f in frames[1:]))
    def test_3d_joint_actuation_not_static_turntable(self):
        frames=self.out["observations"]
        self.assertEqual(frames[0]["head_yaw_deg"],0)
        self.assertEqual(frames[-1]["head_yaw_deg"],12)
        self.assertGreater(m.dist(frames[0]["point_left_world"],frames[-1]["point_left_world"]),0.0001)
    def test_eight_application_indexes_not_canonical_eight_d(self):
        o=self.out
        self.assertEqual(len(o["application_8_index"]),8)
        self.assertFalse(o["canonical_8d_override"])
        self.assertFalse(o["runtime_activated"])
        self.assertFalse(o["formal_d8_authority"])
    def test_negative_wrong_source_digest(self):
        current=m.IDENTITY_SHA256
        try:
            m.IDENTITY_SHA256="0"*64
            with self.assertRaisesRegex(m.Hold,"HOLD_SOURCE_MODEL_IDENTITY_MISMATCH"):
                m.measure(REAL)
        finally:m.IDENTITY_SHA256=current
    def test_same_inputs_reconstruct_same_evidence_hash(self):
        a=self.out;b=m.measure(REAL)
        canonical=lambda d:json.dumps(d,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
        self.assertEqual(hashlib.sha256(canonical(a)).hexdigest(),hashlib.sha256(canonical(b)).hexdigest())
    def test_generic_skeleton_scan_keeps_source_truth(self):
        scan=m.scan_gltf_skeletons(REAL)
        self.assertEqual(scan["source_sha256"],m.IDENTITY_SHA256)
        self.assertEqual(scan["scan_state"],"PASS_RIG_SOURCE_SCAN")
        self.assertEqual([s["joint_count"] for s in scan["skins"]],[170,170,170])
        self.assertFalse(scan["gesture_validated"])
        self.assertFalse(scan["formal_d8_authority"])

    def test_source_scan_does_not_promote_unverified_semantics(self):
        scan=m.scan_gltf_skeletons(REAL)
        self.assertFalse(scan["anatomical_landmarks_verified"])
        self.assertFalse(scan["runtime_activated"])

    def test_pose_quaternion_still_engine_data(self):
        o=self.out
        self.assertTrue(any(item["name"]=="J_Bip_C_Head" for item in o["skeleton_bind_positions"]))
        self.assertEqual(o["coordinate_basis"],"WORLD_SPACE_GLTF_DEFAULT_POSE_HEAD_YAW_TESTED")

if __name__=="__main__":unittest.main(verbosity=2)
