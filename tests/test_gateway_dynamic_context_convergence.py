from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from services.gateway import main
from services.gateway import openai_compat


class _Request:
    async def json(self):
        return {"messages": [{"role": "user", "content": "system work"}]}


class GatewayDynamicContextConvergenceTests(unittest.TestCase):
    def test_legacy_execute_routes_to_governed_nl_control(self) -> None:
        with patch.object(
            main,
            "governed_execute",
            return_value={"state": "GOAL_RUN_STARTED"},
        ) as call:
            result = main.execute({"prompt": "inspect system", "dry_run": False})
        self.assertEqual(result["state"], "GOAL_RUN_STARTED")
        req = call.call_args.args[0]
        self.assertEqual(req.intent, "inspect system")
        self.assertTrue(req.goal_mode)

    def test_legacy_voice_routes_to_governed_nl_control(self) -> None:
        with patch.object(
            main,
            "governed_execute",
            return_value={"state": "GOAL_RUN_STARTED"},
        ) as call:
            main.voice({"utterance": "inspect by voice"})
        self.assertEqual(call.call_args.args[0].intent, "inspect by voice")

    def test_openai_compat_direct_model_call_is_blocked(self) -> None:
        with self.assertRaises(HTTPException) as held:
            asyncio.run(openai_compat.chat_completions(_Request()))
        self.assertEqual(held.exception.status_code, 409)
        self.assertEqual(
            held.exception.detail["context_delivery_mode"],
            "TOTAL_FIELD_POINTER_FIRST_DYNAMIC_CONTEXT_PULL",
        )
        self.assertEqual(held.exception.detail["direct_model_call"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
