from __future__ import annotations

import unittest

from tools.total_field.on_demand_vision_wall import (
    REMOTE_HOST,
    STREAM_SECONDARY,
    build_plan,
    choose_layout,
    parse_channels,
)


class OnDemandVisionWallTest(unittest.TestCase):
    def test_natural_language_all_channels(self) -> None:
        self.assertEqual(parse_channels("開全部監視器"), list(range(8)))

    def test_natural_language_ranges(self) -> None:
        self.assertEqual(parse_channels("看一到四號"), [0, 1, 2, 3])
        self.assertEqual(parse_channels("看5-8號"), [4, 5, 6, 7])

    def test_layout_selection(self) -> None:
        self.assertEqual(choose_layout(1), "1x1")
        self.assertEqual(choose_layout(4), "2x2")
        self.assertEqual(choose_layout(8), "3x3")

    def test_default_plan_is_remote_on_demand_without_plaintext_credentials(self) -> None:
        plan = build_plan("開全部監視器")
        self.assertEqual(plan.host, REMOTE_HOST)
        self.assertEqual(plan.route, "REMOTE_DDNS")
        self.assertEqual(plan.stream, STREAM_SECONDARY)
        self.assertFalse(plan.persistent_stream)
        self.assertEqual(plan.layout, "3x3")
        self.assertEqual(len(plan.urls), 8)
        self.assertTrue(all("@" not in url for url in plan.urls))
        self.assertEqual(plan.credential_policy, "EXTERNAL_LOCAL_SECRET_STORE_ONLY")


if __name__ == "__main__":
    unittest.main()
