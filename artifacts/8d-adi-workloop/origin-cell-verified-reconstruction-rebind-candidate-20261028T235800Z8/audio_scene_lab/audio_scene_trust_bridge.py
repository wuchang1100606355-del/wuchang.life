#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
CANDIDATE_ROOT=HERE.parent
sys.path.insert(0,str(CANDIDATE_ROOT/"candidate"))
import origin_cell_verified_reconstruction as vr

EVIDENCE_PATH=HERE/"MSI_ZERO_DISK_EVIDENCE.json"
SEAL_PATH=HERE/"AUDIO_SCENE_TRUST_SEAL_CANDIDATE.json"
FAST_PATH_PATH=HERE/"AUDIO_SCENE_FAST_PATH_RESULT.json"
BINDING_SCHEMA="W7TP_AUDIO_SCENE_DETERMINISTIC_RECONSTRUCTION_BINDING_CANDIDATE_V1"

def hex64(v):
    if not isinstance(v,str) or len(v)!=64 or any(c not in "0123456789abcdef" for c in v):
        raise vr.ReconstructionHold("HOLD_AUDIO_DIGEST_INVALID")
    return v

def load_evidence():
    ev=json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if ev.get("schema")!="W7TP_AUDIO_ZERO_DISK_ORIGIN_CELL_EVIDENCE_V1":
        raise vr.ReconstructionHold("HOLD_AUDIO_EVIDENCE_SCHEMA")
    if ev.get("state")!="PASS_CANDIDATE":
        raise vr.ReconstructionHold("HOLD_AUDIO_EVIDENCE_NOT_PASS")
    z=ev.get("zero_disk_io") or {}
    if z.get("wav_outputs_written")!=0 or z.get("hash_computed_from_ram") is not True:
        raise vr.ReconstructionHold("HOLD_AUDIO_ZERO_DISK_NOT_PROVEN")
    rec=ev.get("reconstruction") or {}
    if rec.get("byte_exact_same_cell") is not True:
        raise vr.ReconstructionHold("HOLD_AUDIO_TWO_RENDER_MISMATCH")
    if hex64(rec.get("r1_sha256",""))!=hex64(rec.get("r2_sha256","")):
        raise vr.ReconstructionHold("HOLD_AUDIO_TWO_RENDER_DIGEST_MISMATCH")
    return ev

def build_binding(ev):
    body={
      "schema":BINDING_SCHEMA,
      "source_state_sha256":hex64(ev["scene_cell"]["sha256"]),
      "source_size_bytes":int(ev["scene_cell"]["serialized_bytes"]),
      "packet_sha256":hex64(ev["scene_cell"]["sha256"]),
      "packet_bytes":int(ev["scene_cell"]["serialized_bytes"]),
      "executor_ref":"audio_scene_lab/run_emotion_lut.py",
      "executor_sha256":hex64(ev["base_descriptor"]["renderer_sha256"]),
      "base_cache_sha256":hex64(ev["base_cache_sha256"]),
      "lut_sha256":hex64(ev["lut"]["sha256"]),
      "namespace":"w7tp:audio-scene:v2.3-candidate",
      "reconstruction_contract":"ZERO_DISK_RAM_BYTE_EXACT_AUDIO_SCENE_V1",
      "route_ref":"route_ref:audio-scene-origin-cell",
      "target_output_bytes":int(ev["reconstruction"]["output_bytes"]),
      "dynamic_observation_envelope_in_identity":False,
      "current_d8_authority_in_identity":False
    }
    body["reconstruction_key"]=vr.canonical_hash(body)
    return body

def issue_seal(ev,binding):
    target=hex64(ev["reconstruction"]["r1_sha256"])
    channels={"1":target}
    target_state_digest=vr.canonical_hash(channels)
    verified_identity=vr.canonical_hash({
      "reconstruction_key":binding["reconstruction_key"],
      "target_state_digest":target_state_digest,
      "channel_digests":channels
    })
    seal={
      "schema":vr.TRUST_SEAL_SCHEMA,
      "state":"CANDIDATE_RECONSTRUCTION_TRUST_SEAL_VERIFIED",
      "seal_role":"D4_REUSABLE_EVIDENCE_CANDIDATE_NOT_D8_AUTHORITY",
      "reconstruction_key":binding["reconstruction_key"],
      "verified_reconstruction_identity":verified_identity,
      "binding":binding,
      "target_state_digest":target_state_digest,
      "channel_digests":channels,
      "verification":{
        "method":"MSI_ZERO_DISK_TWO_RENDER_BYTE_EXACT_SHA256",
        "result":"PASS",
        "evidence_ref":"audio_scene_lab/MSI_ZERO_DISK_EVIDENCE.json",
        "two_render_byte_exact":True,
        "output_wav_written":False
      },
      "wire_measurement":{
        "origin_cell_packet_bytes":int(ev["scene_cell"]["serialized_bytes"]),
        "zlib_reference_bytes":int(ev["scene_cell"]["zlib_bytes"]),
        "seal_bytes_are_control_evidence_not_origin_cell_payload":True
      },
      "effect_authorization":False,
      "current_d8_required_for_effect":True,
      "reconstructed_equals_executed":False,
      "executed_equals_effect_verified":False
    }
    seal["trust_seal_sha256"]=vr.canonical_hash(seal)
    vr.verify_trust_seal_record(seal)
    return seal

def fast_path(ev,seal):
    idx=vr.build_trust_index([seal])
    binding=build_binding(ev)
    rec=idx.get(binding["reconstruction_key"])
    if rec is None:
        return {"state":"HOLD_FULL_VERIFICATION_REQUIRED","effect_authorization":False}
    vr.verify_trust_seal_record(rec)
    if rec["binding"]!=binding:
        raise vr.ReconstructionHold("HOLD_AUDIO_FASTPATH_BINDING_DRIFT")
    second=hex64(ev["reconstruction"]["r2_sha256"])
    if second!=rec["channel_digests"]["1"]:
        raise vr.ReconstructionHold("HOLD_AUDIO_FASTPATH_TARGET_DIGEST_MISMATCH")
    return {
      "state":"PASS_TRUST_SEAL_FAST_RECONSTRUCTION",
      "reconstruction_key":binding["reconstruction_key"],
      "trust_seal_sha256":rec["trust_seal_sha256"],
      "target_sha256":second,
      "origin_cell_packet_bytes":binding["packet_bytes"],
      "effect_authorization":False,
      "current_d8_required_for_effect":True,
      "fast_path_basis":"SAME_RECONSTRUCTION_KEY_PLUS_SECOND_RAM_RENDER_DIGEST_MATCH"
    }

def main():
    ev=load_evidence(); binding=build_binding(ev)
    seal=issue_seal(ev,binding); result=fast_path(ev,seal)
    SEAL_PATH.write_text(json.dumps(seal,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    FAST_PATH_PATH.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps({"seal":seal,"fast_path":result},ensure_ascii=False,indent=2,sort_keys=True))
if __name__=="__main__": main()
