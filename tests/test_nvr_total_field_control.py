import unittest
from fastapi import HTTPException

from services.gateway.nvr_control import (
    NvrReadPlanRequest,
    NvrReceiptRequest,
    build_nvr_read_plan,
    validate_nvr_receipt,
)


class NvrTotalFieldControlTests(unittest.TestCase):
    def test_snapshot_plan_is_read_only_and_pointer_bound(self):
        req = NvrReadPlanRequest(
            task_id="T-024",
            camera_ref="CAM01",
            operation="SNAPSHOT",
            context_ref="context:task-state:T-024:test",
            origin_packet_ref="packet:task-state:T-024:test",
        )
        out = build_nvr_read_plan(req)
        field = out["joint_state_field"]
        self.assertEqual(out["state"], "READY_NVR_READ_COMPATIBILITY_TRANSPORT")
        self.assertEqual(field["D5"]["mode"], "READ_ONLY")
        self.assertFalse(field["D5"]["external_effect_gate"]["mutation"])
        self.assertFalse(field["D5"]["external_effect_gate"]["effect_authority"])
        self.assertEqual(field["D6"]["context_ref"], req.context_ref)
        self.assertTrue(field["D6"]["raw_frame_is_not_gst_payload"])
        self.assertFalse(field["D8"]["read_creates_effect_authority"])
        self.assertEqual(
            out["dispatch"]["service_ref"], "service:msi:nvr-read-adapter"
        )
        self.assertEqual(out["dispatch"]["input"]["channel_index"], 0)

    def test_current_reachability_receipt_is_accepted_without_authority(self):
        receipt = {
            "state": "PASS_NVR_READ_ADAPTER_REACHABLE",
            "device_ref": "device:nvr:ah55b08:wuchang",
            "service_ref": "service:msi:nvr-read-adapter",
            "node_ref": "node:MSI",
            "rtsp": {"reachable": True, "status": 401, "auth_required": True},
            "credentials_output": False,
            "mutation_performed": False,
        }
        out = validate_nvr_receipt(
            NvrReceiptRequest(
                task_id="T-024",
                context_ref="context:task-state:T-024:test",
                receipt=receipt,
            )
        )
        self.assertEqual(
            out["state"], "PASS_CURRENT_NVR_REACHABILITY_RECEIPT_ACCEPTED"
        )
        self.assertFalse(out["effect_authority_created"])
        self.assertFalse(out["mutation_accepted"])

    def test_real_snapshot_receipt_requires_exact_camera_coordinate_and_hash(self):
        receipt = {
            "state": "PASS_NVR_SNAPSHOT_ACQUIRED",
            "device_ref": "device:nvr:ah55b08:wuchang",
            "service_ref": "service:msi:nvr-read-adapter",
            "node_ref": "node:MSI",
            "camera_ref": "CAM01",
            "channel_index": 0,
            "sha256": "a" * 64,
            "bytes": 12345,
            "credentials_output": False,
            "mutation_performed": False,
        }
        out = validate_nvr_receipt(
            NvrReceiptRequest(
                task_id="T-024",
                context_ref="context:task-state:T-024:test",
                receipt=receipt,
            )
        )
        self.assertEqual(out["state"], "PASS_REAL_JPEG_RECEIPT_ACCEPTED")

    def test_mutating_receipt_is_rejected(self):
        receipt = {
            "state": "PASS_NVR_READ_ADAPTER_REACHABLE",
            "device_ref": "device:nvr:ah55b08:wuchang",
            "service_ref": "service:msi:nvr-read-adapter",
            "node_ref": "node:MSI",
            "rtsp": {"reachable": True},
            "credentials_output": False,
            "mutation_performed": True,
        }
        with self.assertRaises(HTTPException):
            validate_nvr_receipt(
                NvrReceiptRequest(
                    task_id="T-024",
                    context_ref="context:task-state:T-024:test",
                    receipt=receipt,
                )
            )


if __name__ == "__main__":
    unittest.main()
