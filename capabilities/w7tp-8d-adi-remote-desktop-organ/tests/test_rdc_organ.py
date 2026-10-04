from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("rdc_organ",ROOT/"rdc_organ.py")
mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod)

class RemoteDesktopOrganTests(unittest.TestCase):
    def test_read_file_is_read_only(self):
        r=mod.resolve_effect("read_file",{"path":"/tmp/a"})
        self.assertEqual(r["effect_class"],"READ_ONLY")
        self.assertFalse(r["d8_required"])

    def test_write_file_requires_d8(self):
        r=mod.resolve_effect("write_file",{"path":"/tmp/a","content":"x"})
        self.assertEqual(r["effect_class"],"MUTATION")
        self.assertTrue(r["d8_required"])
        with self.assertRaisesRegex(mod.RemoteDesktopOrganError,"D8_AUTHORITY_REF_REQUIRED"):
            mod.build_effect_envelope(source_tool="write_file",task_ref="task:T",device_ref="device:X",target_ref="path:/tmp/a",input_payload={"path":"/tmp/a","content":"x"},authority_ref=None,idempotency_key="idem:1",return_coordinate="total-field:return")

    def test_safe_posix_process_can_be_read_only(self):
        r=mod.resolve_effect("start_process",{"command":"git status --short"})
        self.assertEqual(r["effect_class"],"READ_ONLY")
        self.assertFalse(r["d8_required"])

    def test_mutating_process_requires_d8(self):
        r=mod.resolve_effect("start_process",{"command":"rm -f /tmp/x"})
        self.assertEqual(r["effect_class"],"MUTATION")
        self.assertTrue(r["d8_required"])

    def test_destructive_process_class(self):
        r=mod.resolve_effect("start_process",{"command":"shutdown -h now"})
        self.assertEqual(r["effect_class"],"DESTRUCTIVE_CONTROL")
        self.assertTrue(r["d8_required"])

    def test_read_only_powershell(self):
        cmd="Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name | Format-Table"
        r=mod.resolve_effect("start_process",{"command":cmd})
        self.assertEqual(r["effect_class"],"READ_ONLY")
        self.assertFalse(r["d8_required"])

    def test_powershell_mutation_fails_closed(self):
        cmd="Get-NetAdapter | Disable-NetAdapter -Confirm:$false"
        r=mod.resolve_effect("start_process",{"command":cmd})
        self.assertTrue(r["d8_required"])
        self.assertEqual(r["effect_class"],"MUTATION")

    def test_direct_ip_service_identity_forbidden(self):
        with self.assertRaisesRegex(mod.RemoteDesktopOrganError,"DIRECT_IP_PORT_SERVICE_ID_FORBIDDEN"):
            mod.validate_service_ref("http://192.168.50.82:9002")
        mod.validate_service_ref("service:member.odoo")
        mod.validate_service_ref("https://pos.liaoguo.wuchang.life")

    def test_cloud_completion_cannot_create_authority(self):
        c=mod.validate_cloud_completion({"missing_relation_candidate":"x"})
        self.assertTrue(c["candidate_only"])
        self.assertFalse(c["authority_created"])
        with self.assertRaisesRegex(mod.RemoteDesktopOrganError,"CLOUD_COMPLETION_FORBIDDEN_FIELD"):
            mod.validate_cloud_completion({"d8_authority":"ALLOW"})

    def test_read_envelope_does_not_require_authority(self):
        e=mod.build_effect_envelope(source_tool="read_file",task_ref="task:T",device_ref="device:X",target_ref="path:/tmp/a",input_payload={"path":"/tmp/a"},authority_ref=None,idempotency_key="idem:2",return_coordinate="total-field:return")
        self.assertEqual(e["effect_class"],"READ_ONLY")
        self.assertEqual(len(e["envelope_sha256"]),64)

    def test_origin_projection_is_candidate_not_authority(self):
        p=mod.build_origin_state_projection(task_ref="task:T",device_ref="device:X",command_id="rdc.file.read",state_refs=["state:a"],evidence_refs=["evidence:a"],version_ref="version:1")
        self.assertFalse(p["plaintext_expansion"])
        self.assertFalse(p["authority_created"])

    def test_compatibility_dispatch_preserves_source_tool(self):
        e=mod.build_effect_envelope(source_tool="read_file",task_ref="task:T",device_ref="device:X",target_ref="path:/tmp/a",input_payload={"path":"/tmp/a"},authority_ref=None,idempotency_key="idem:3",return_coordinate="total-field:return")
        plan=mod.build_dispatch_plan(e,mode="compatibility_rdc")
        self.assertEqual(plan["mode"],"COMPATIBILITY_RDC")
        self.assertEqual(plan["source_tool"],"read_file")
        self.assertTrue(plan["source_runtime_dependency"])

    def test_native_dispatch_uses_service_ref_not_ip(self):
        e=mod.build_effect_envelope(source_tool="read_file",task_ref="task:T",device_ref="device:X",target_ref="path:/tmp/a",input_payload={"path":"/tmp/a"},authority_ref=None,idempotency_key="idem:4",return_coordinate="total-field:return")
        plan=mod.build_dispatch_plan(e,mode="native_claw",executor_service_ref="service:node.taiji01.native-claw")
        self.assertEqual(plan["mode"],"NATIVE_CLAW")
        self.assertEqual(plan["native_action_ref"],"node.file.read")
        self.assertFalse(plan["source_runtime_dependency"])
        with self.assertRaisesRegex(mod.RemoteDesktopOrganError,"DIRECT_IP_PORT_SERVICE_ID_FORBIDDEN"):
            mod.build_dispatch_plan(e,mode="native_claw",executor_service_ref="http://192.168.50.249:9004")

    def test_native_mutation_retains_authority_and_idempotency(self):
        e=mod.build_effect_envelope(source_tool="write_file",task_ref="task:T",device_ref="device:X",target_ref="path:/tmp/a",input_payload={"path":"/tmp/a","content":"x"},authority_ref="authority:test:1",idempotency_key="idem:5",return_coordinate="total-field:return")
        plan=mod.build_dispatch_plan(e,mode="native_claw",executor_service_ref="service:node.taiji01.native-claw")
        self.assertEqual(plan["authority_ref"],"authority:test:1")
        self.assertEqual(plan["idempotency_key"],"idem:5")

if __name__=="__main__": unittest.main()
