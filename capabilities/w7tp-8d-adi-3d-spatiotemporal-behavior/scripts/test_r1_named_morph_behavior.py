#!/usr/bin/env python3
"""Sparse glTF red-team cases and real R1 source-labeled morph acceptance."""
from __future__ import annotations
import hashlib, json, math, os, struct, unittest, zipfile
from pathlib import Path
import gltf_spatiotemporal_field as field
import r1_named_morph_behavior as r1

ARCHIVE=Path(os.environ["W7TP_XIAOJ_R1_ZIP"]) if os.environ.get("W7TP_XIAOJ_R1_ZIP") else None

def synthetic_sparse(values=(1.,2.,3.), sparse_indices=(1,), count=3):
    idx_blob=bytes(sparse_indices)
    val_blob=struct.pack("<"+"f"*len(values),*values)
    doc={
     "accessors":[{"componentType":5126,"type":"VEC3","count":count,
                   "sparse":{"count":len(sparse_indices),"indices":{"bufferView":0,"componentType":5121},
                             "values":{"bufferView":1}}}],
     "bufferViews":[{"buffer":0,"byteLength":len(idx_blob),"byteOffset":0},
                    {"buffer":0,"byteLength":len(val_blob),"byteOffset":len(idx_blob)}]
    }
    return doc,idx_blob+val_blob

class SparseAccessorIndependentTests(unittest.TestCase):
    def test_sparse_missing_base_view_materializes_zero(self):
        doc,raw=synthetic_sparse()
        self.assertEqual(field.accessor(doc,raw,0),[(0,0,0),(1.,2.,3.),(0,0,0)])
    def test_sparse_sorted_two_distinct_indices(self):
        doc,raw=synthetic_sparse((1.,2.,3.,4.,5.,6.),(0,2))
        self.assertEqual(field.accessor(doc,raw,0),[(1.,2.,3.),(0,0,0),(4.,5.,6.)])
    def test_sparse_duplicate_hold(self):
        doc,raw=synthetic_sparse((1.,2.,3.,4.,5.,6.),(1,1))
        with self.assertRaisesRegex(field.Hold,"HOLD_SPARSE_INDICES_UNSORTED_OR_INVALID"):
            field.accessor(doc,raw,0)
    def test_sparse_out_of_bounds_hold(self):
        doc,raw=synthetic_sparse((1.,2.,3.),(3,))
        with self.assertRaisesRegex(field.Hold,"HOLD_SPARSE_INDICES_UNSORTED_OR_INVALID"):
            field.accessor(doc,raw,0)
    def test_sparse_unsupported_index_code_hold(self):
        doc,raw=synthetic_sparse()
        doc["accessors"][0]["sparse"]["indices"]["componentType"]=5126
        with self.assertRaisesRegex(field.Hold,"HOLD_SPARSE_INDEX_COMPONENT_INVALID"):
            field.accessor(doc,raw,0)
    def test_sparse_malformed_count_hold(self):
        doc,raw=synthetic_sparse()
        doc["accessors"][0]["sparse"]["count"]=5
        with self.assertRaisesRegex(field.Hold,"HOLD_SPARSE_COUNT_INVALID"):
            field.accessor(doc,raw,0)
    def test_sparse_truncated_value_hold(self):
        doc,raw=synthetic_sparse()
        doc["bufferViews"][1]["byteLength"]=8
        with self.assertRaisesRegex(field.Hold,"HOLD_ACCESSOR_BOUNDS"):
            field.accessor(doc,raw,0)
    def test_dense_accessor_same_as_before(self):
        data=struct.pack("<ffffff",0.,0.,1.,1.,2.,3.)
        doc={"accessors":[{"componentType":5126,"type":"VEC3","count":2,"bufferView":0}],
             "bufferViews":[{"buffer":0,"byteLength":len(data)}]}
        self.assertEqual(field.accessor(doc,data,0),[(0.,0.,1.),(1.,2.,3.)])

@unittest.skipIf(ARCHIVE is None,"R1 archive not present on this node")
class RealR1MorphAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=r1.evaluate_r1(ARCHIVE)
    def test_source_fingerprint(self):
        self.assertEqual(self.data["asset_sha256"],r1.R1_ASSET_SHA256)
        self.assertEqual(self.data["archive_sha256"],r1.R1_ARCHIVE_SHA256)
    def test_two_distinct_model_labeled_morph_channels(self):
        self.assertEqual(self.data["source_semantic_controls"],{"mouthSmileLeft":43,"mouthSmileRight":44})
        self.assertTrue(self.data["semantic_target_names_verified_from_asset"])
        self.assertNotEqual(*self.data["dominant_morph_response_point_ids"].values())
    def test_real_skin_rest_error_and_57_bones(self):
        self.assertEqual(self.data["rig_joint_count"],57)
        self.assertLess(self.data["world_rest_pose_skinning_error_max"],0.0001)
        self.assertEqual(self.data["existing_animation_clips"],7)
    def test_smile_growth_real_model_xyz(self):
        t=self.data["timeline"]
        self.assertEqual([f["time_ms"] for f in t],[0,163,325,487,650])
        self.assertGreater(t[-1]["absolute_distance_3d"],t[0]["absolute_distance_3d"])
        for frame in t:
            self.assertAlmostEqual(
                field.dist(frame["left_representative_vertex_xyz"],
                           frame["right_representative_vertex_xyz"]),
                frame["absolute_distance_3d"],places=10)
    def test_three_camera_world_invariance(self):
        for frame in self.data["timeline"]:
            self.assertEqual({a["camera"] for a in frame["views"]},{"front","side","oblique"})
            for camera in frame["views"]:
                self.assertLess(abs(camera["true_camera_3d_distance"]-frame["absolute_distance_3d"]),1e-9)
                self.assertLess(camera["reprojection_error"],1e-9)
    def test_no_anatomical_landmark_false_claim(self):
        self.assertFalse(self.data["dominant_response_points_are_verified_anatomical_mouth_corners"])
        self.assertFalse(self.data["real_runtime_playback_verified"])
        self.assertEqual(self.data["authority"],"CANDIDATE_ONLY_NO_D8")
    def test_real_R1_sparse_morph_accessor_decoded(self):
        with zipfile.ZipFile(ARCHIVE) as archive:
            raw=archive.read(r1.R1_MEMBER)
        offset=12; doc=None; blob=None
        while offset+8<=len(raw):
            n,kind=struct.unpack_from("<I4s",raw,offset)
            if kind==b"JSON":doc=json.loads(raw[offset+8:offset+8+n].decode().rstrip(" \x00"))
            elif kind==b"BIN\x00":blob=raw[offset+8:offset+8+n]
            offset+=8+n
        self.assertIsNotNone(doc)
        self.assertIsNotNone(blob)
        accessor_index=doc["meshes"][0]["primitives"][0]["targets"][43]["POSITION"]
        self.assertIn("sparse",doc["accessors"][accessor_index])
        decoded=field.accessor(doc,blob,accessor_index)
        self.assertEqual(len(decoded),doc["accessors"][accessor_index]["count"])
        self.assertTrue(all(math.isfinite(coord) for v in decoded for coord in v))

    def test_wrong_source_manifest_hold(self):
        original=r1.R1_ARCHIVE_SHA256
        try:
            r1.R1_ARCHIVE_SHA256="0"*64
            with self.assertRaisesRegex(field.Hold,"HOLD_R1_DELIVERY_IDENTITY_CHANGED"):
                r1.evaluate_r1(ARCHIVE)
        finally:r1.R1_ARCHIVE_SHA256=original
    def test_deterministic_replay(self):
        again=r1.evaluate_r1(ARCHIVE)
        stringify=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
        self.assertEqual(hashlib.sha256(stringify(again)).hexdigest(),
                         hashlib.sha256(stringify(self.data)).hexdigest())

if __name__=="__main__":unittest.main(verbosity=2)
