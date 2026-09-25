#!/usr/bin/env python3
"""Verify the cafe POS demo with a real Chromium product session.

The verifier drives only synthetic, in-memory controls. It does not submit a
form, read credentials, capture payment, or persist a browser profile.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify.verify_medical_care_browser_product import (  # noqa: E402
    ChromiumSession,
    VerificationError,
    _evaluate,
    _wait_for_ready,
)


DEFAULT_URL = "https://wuchang.life/pos_promo_sandbox/"


DESKTOP_EXPRESSION = r"""
(async () => {
  const checks = {};
  const details = {};
  const record = (name, value, detail = null) => {
    checks[name] = Boolean(value);
    if (detail !== null) details[name] = detail;
  };
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const text = (selector) => document.querySelector(selector)?.textContent.trim() || "";
  await wait(250);

  record("document_ready", document.readyState === "complete", document.readyState);
  record("page_title", document.title.includes("上品聊國咖啡館"), document.title);
  record("single_h1", document.querySelectorAll("h1").length === 1);
  record("main_landmark", Boolean(document.querySelector("main#main")));
  record("skip_link", document.querySelector("a.skip-link")?.getAttribute("href") === "#main");
  record("no_form_surface", document.querySelectorAll("form").length === 0);
  record(
    "real_menu_synthetic_transaction_boundary",
    document.body.innerText.includes("雲端權威菜單 · 合成交易") &&
      document.body.innerText.includes("QuickClick 雲端原始匯出") &&
      document.body.innerText.includes("58 筆啟用／64 筆來源") &&
      document.body.innerText.includes("不建立真實訂單") &&
      document.body.innerText.includes("不扣款") &&
      document.body.innerText.includes("不讀會員明文") &&
      document.body.innerText.includes("不寫入 production DB")
  );
  record(
    "public_purpose_declaration",
    text("#public-purpose-title") === "這不是一般咖啡店促銷頁" &&
      document.body.innerText.includes("社區數位發展基金") &&
      document.body.innerText.includes("以商以智養公益、以商養公") &&
      document.body.innerText.includes("不是募款、投資邀請或收益保證")
  );
  record(
    "device_only_boundary",
    document.body.innerText.includes("未來 LLM 僅在使用者設備形成候選") &&
      document.body.innerText.includes("伺服器不執行 LLM")
  );
  record(
    "zero_transaction_metrics",
    [...document.querySelectorAll(".hero-proof dd")].map((node) => node.textContent.trim()).join(",") === "0,0,0"
  );
  record(
    "initial_redteam_monitor",
    document.querySelector("#cafe-redteam-monitor")?.dataset.state === "MONITORING_CLEAR" &&
      text("#redteam-cycle").includes("cycle 0")
  );

  const categoryTabs = [...document.querySelectorAll("[role='tab'][data-category]")];
  const workflowTabs = [...document.querySelectorAll("[role='tab'][data-workflow]")];
  record("category_tabs", categoryTabs.length === 6);
  record("workflow_tabs", workflowTabs.length === 3);
  record("active_menu_count", document.querySelectorAll("[data-add-product]").length === 58);
  const productCards = [...document.querySelectorAll("[data-add-product]")];
  record(
    "one_card_per_source_sku",
    new Set(productCards.map((card) => card.dataset.addProduct)).size === 58
  );
  record(
    "unique_source_product_references",
    productCards.every((card) => card.innerText.includes("QUICKCLICK:M387676:"))
  );

  document.querySelector("[data-category='coffee']").click();
  record(
    "category_filter",
    document.querySelectorAll("[data-add-product]").length === 16 &&
      document.body.innerText.includes("義式咖啡") &&
      document.body.innerText.includes("單品手沖") &&
      document.querySelector("[data-category='coffee']").getAttribute("aria-selected") === "true"
  );
  document.querySelector("[data-category='drip']").click();
  record(
    "drip_merchandising_pause",
    document.querySelectorAll("[data-add-product]").length === 0 &&
      document.querySelector(".catalog-paused")?.textContent.includes("6 項商品不提供人類或 AI 加入候選")
  );
  document.querySelector("[data-category='all']").click();

  const intentInput = document.querySelector("#intent-input");
  intentInput.value = "招牌咖啡 大杯 少冰 半糖";
  document.querySelector("#parse-intent").click();
  record(
    "device_intent_source_grounding",
    text("#config-product-name") === "招牌咖啡" &&
      text("#config-summary").includes("尺寸：L") &&
      text("#config-summary").includes("溫度：少冰") &&
      text("#config-summary").includes("甜度：半糖50%") &&
      !document.querySelector("#confirm-config").disabled
  );
  document.querySelector("#confirm-config").click();

  intentInput.value = "招牌咖啡 大杯 少冰 半糖";
  document.querySelector("#parse-intent").click();
  document.querySelector("#confirm-config").click();

  document.querySelector("[data-add-product='P_49180073']").click();
  document.querySelector("[data-option-id='O7835316:Q1:O2']").click();
  document.querySelector("[data-option-id='O7835316:Q2:O5']").click();
  document.querySelector("[data-option-id='O7835316:Q3:O5']").click();
  record(
    "human_required_option_flow",
    text("#config-summary").includes("尺寸：M") &&
      text("#config-summary").includes("溫度：熱") &&
      text("#config-summary").includes("甜度：無糖0%") &&
      !document.querySelector("#confirm-config").disabled
  );
  document.querySelector("#confirm-config").click();
  record(
    "cart_candidate_math",
    text("#cart-count") === "3 項" &&
      text("#cart-total") === "NT$ 300" &&
      document.querySelectorAll(".cart-line").length === 2 &&
      document.querySelectorAll(".line-modifiers").length === 2
  );

  document.querySelector("#service-mode").value = "takeaway";
  document.querySelector("#service-mode").dispatchEvent(new Event("change", {bubbles: true}));
  record(
    "modifier_transition",
    text("#redteam-cycle").includes("MODIFIER_CHANGE") &&
      document.querySelector("#cafe-redteam-monitor")?.dataset.state === "MONITORING_CLEAR"
  );

  document.querySelector("#build-candidate").click();
  const hashDeadline = performance.now() + 3000;
  while (!/^[0-9a-f]{64}$/.test(text("#candidate-hash")) && performance.now() < hashDeadline) {
    await wait(25);
  }
  const contentHash = text("#candidate-hash");
  record("browser_sha256", /^[0-9a-f]{64}$/.test(contentHash), contentHash);
  record(
    "candidate_8d_hold",
    text("#packet-state").includes("L3 CANDIDATE") &&
      text("#packet-d6") === "L3 candidate reconstruction" &&
      text("#packet-d8") === "HOLD · FORMAL POS RELEASE"
  );

  document.querySelector("#staff-review").click();
  record(
    "human_review_keeps_d8_hold",
    text("#packet-state").includes("HUMAN_REVIEWED_DEMO") &&
      text("#packet-state").includes("D8 HOLD") &&
      text("#packet-d8") === "HOLD · FORMAL POS RELEASE" &&
      text("#action-result").includes("不是正式訂單")
  );

  document.querySelector("#queue-candidate").click();
  record(
    "local_queue_boundary",
    text("#queue-count") === "1 PACKETS" &&
      text("#packet-state").includes("QUEUED_DEMO") &&
      text("#packet-state").includes("D8 HOLD")
  );

  document.querySelector("#test-payment-boundary").click();
  record(
    "payment_boundary_blocks",
    document.querySelector("#cafe-redteam-monitor")?.dataset.state === "DRIFT_ALERT" &&
      text("#redteam-message").includes("HOLD_PAYMENT_CAPTURE_FORBIDDEN") &&
      text("#action-result").includes("付款請求已被常駐紅隊阻擋")
  );
  record(
    "transaction_metrics_stay_zero",
    [...document.querySelectorAll(".hero-proof dd")].every((node) => node.textContent.trim() === "0")
  );

  document.querySelector("[data-category='tea-other']").click();
  record(
    "redteam_rechecks_and_recovers",
    document.querySelector("#cafe-redteam-monitor")?.dataset.state === "MONITORING_CLEAR" &&
      text("#redteam-cycle").includes("CATEGORY_VIEW")
  );

  document.querySelector("#toggle-offline").click();
  record(
    "offline_candidate_boundary",
    text("#connection-state") === "EDGE OFFLINE / LOCAL ONLY" &&
      text("#packet-d2") === "EDGE_OFFLINE_QUEUE" &&
      text("#total-field-state").includes("EDGE CANDIDATE ONLY")
  );
  document.querySelector("#toggle-offline").click();
  record(
    "relink_requires_revalidation",
    text("#connection-state") === "TAIJI01 LINKED / DEMO" &&
      text("#packet-state") === "EMPTY" &&
      text("#packet-d8") === "HOLD · FORMAL POS RELEASE"
  );

  document.querySelector("#request-redeem").click();
  record(
    "cup_request_human_gate",
    text("#cup-remaining") === "12" &&
      text("#cup-state") === "PENDING HUMAN REVIEW" &&
      !document.querySelector("#confirm-redeem").disabled
  );
  document.querySelector("#confirm-redeem").click();
  record(
    "cup_confirmation_local_only",
    text("#cup-remaining") === "11" &&
      text("#cup-state") === "HUMAN_CONFIRMED_DEMO" &&
      document.querySelector("#confirm-redeem").disabled
  );

  record(
    "deterministic_event_sequence",
    [...document.querySelectorAll("#event-log li")].every((item) => /^SEQ-\d{3} · /.test(item.textContent.trim())) &&
      document.querySelectorAll("#event-log li").length <= 8
  );
  record(
    "live_announcement",
    document.querySelector("#announcement")?.getAttribute("aria-live") === "polite" &&
      text("#announcement").length > 8
  );

  const visibleInteractive = [...document.querySelectorAll("a[href], button, select, [tabindex]")]
    .filter((node) => {
      const style = getComputedStyle(node);
      const box = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
    });
  const unnamed = visibleInteractive.filter((node) => {
    return !(node.getAttribute("aria-label") || node.textContent.trim() || node.getAttribute("title"));
  });
  const undersized = visibleInteractive.filter((node) => {
    const box = node.getBoundingClientRect();
    return box.width < 24 || box.height < 24;
  });
  record("interactive_names", unnamed.length === 0, unnamed.length);
  record("minimum_target_size", undersized.length === 0, undersized.length);
  record(
    "desktop_no_horizontal_overflow",
    document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
    {scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth}
  );

  const resourceOrigins = performance.getEntriesByType("resource")
    .map((entry) => new URL(entry.name, location.href).origin);
  record(
    "same_origin_runtime_resources",
    resourceOrigins.every((origin) => origin === location.origin),
    [...new Set(resourceOrigins)]
  );
  const navigation = performance.getEntriesByType("navigation")[0];
  record("https_document", location.protocol === "https:", location.protocol);
  record("document_http_200", navigation?.responseStatus === 200, navigation?.responseStatus || null);

  details.final = {
    cartCount: text("#cart-count"),
    queueCount: text("#queue-count"),
    cupRemaining: text("#cup-remaining"),
    redteamState: document.querySelector("#cafe-redteam-monitor")?.dataset.state || null
  };
  return {checks, details};
})()
"""


MOBILE_EXPRESSION = r"""
(() => {
  const clientWidth = document.documentElement.clientWidth;
  const menu = document.querySelector(".menu-grid")?.getBoundingClientRect();
  const workspace = document.querySelector(".pos-workspace")?.getBoundingClientRect();
  const interactive = [...document.querySelectorAll("button, select")]
    .filter((node) => {
      const box = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return box.width > 0 && box.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    })
    .map((node) => node.getBoundingClientRect());
  return {
    checks: {
      mobile_no_horizontal_overflow: document.documentElement.scrollWidth <= clientWidth + 1,
      mobile_workspace_fits: Boolean(workspace) && workspace.left >= -1 && workspace.right <= clientWidth + 1,
      mobile_menu_fits: Boolean(menu) && menu.left >= -1 && menu.right <= clientWidth + 1,
      mobile_real_menu_usable: document.querySelectorAll("[data-add-product]").length === 58 &&
        [...document.querySelectorAll("[data-add-product]")].every((node) => node.getBoundingClientRect().height >= 100),
      mobile_controls_target_size: interactive.every((box) => box.width >= 24 && box.height >= 24),
      mobile_tab_controls_visible: document.querySelectorAll("[role='tab']").length === 9,
      reduced_motion_exposed: matchMedia("(prefers-reduced-motion: reduce)").matches
    },
    details: {
      viewport: {width: innerWidth, height: innerHeight},
      layout: {scrollWidth: document.documentElement.scrollWidth, clientWidth}
    }
  };
})()
"""


def _ax_checks(connection: Any) -> dict[str, bool]:
    tree = connection.command("Accessibility.getFullAXTree").get("nodes", [])
    visible = [node for node in tree if not node.get("ignored")]
    roles = [node.get("role", {}).get("value") for node in visible]
    tabs = [node for node in visible if node.get("role", {}).get("value") == "tab"]
    return {
        "ax_main_landmark": "main" in roles,
        "ax_two_tablists": roles.count("tablist") >= 2,
        "ax_named_product_tabs": len(tabs) == 9
        and all(str(node.get("name", {}).get("value", "")).strip() for node in tabs),
    }


def verify(url: str, chromium: str | None = None) -> dict[str, Any]:
    session = ChromiumSession(chromium)
    connection = session.connection
    try:
        for domain in ("Page", "Runtime", "Log", "Network", "Accessibility"):
            connection.command(f"{domain}.enable")
        connection.command("Page.navigate", {"url": url})
        _wait_for_ready(connection)
        desktop = _evaluate(connection, DESKTOP_EXPRESSION)
        desktop_checks = dict(desktop.get("checks", {}))
        desktop_checks.update(_ax_checks(connection))

        connection.command(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 390,
                "height": 844,
                "deviceScaleFactor": 1,
                "mobile": True,
            },
        )
        connection.command(
            "Emulation.setEmulatedMedia",
            {
                "media": "screen",
                "features": [{"name": "prefers-reduced-motion", "value": "reduce"}],
            },
        )
        connection.command("Page.reload", {"ignoreCache": True})
        _wait_for_ready(connection)
        time.sleep(0.2)
        mobile = _evaluate(connection, MOBILE_EXPRESSION)
        mobile_checks = dict(mobile.get("checks", {}))

        exception_events = [
            event for event in connection.events if event.get("method") == "Runtime.exceptionThrown"
        ]
        error_logs = [
            event
            for event in connection.events
            if event.get("method") == "Log.entryAdded"
            and event.get("params", {}).get("entry", {}).get("level") == "error"
        ]
        failed_requests = [
            event
            for event in connection.events
            if event.get("method") == "Network.loadingFailed"
            and event.get("params", {}).get("type") not in {"Other"}
        ]
        runtime_checks = {
            "no_javascript_exceptions": not exception_events,
            "no_browser_error_logs": not error_logs,
            "no_required_resource_failures": not failed_requests,
        }
        checks = {**desktop_checks, **mobile_checks, **runtime_checks}
        failures = sorted(name for name, passed in checks.items() if not passed)
        return {
            "schema_version": "W7TP-CAFE-POS-BROWSER-PRODUCT-VERIFY/1.0",
            "state": "PASS_BROWSER_PRODUCT" if not failures else "HOLD_BROWSER_PRODUCT",
            "url": url,
            "planned_domain": "https://business.wuchang.life/",
            "checks": checks,
            "failure_codes": failures,
            "observations": {
                "desktop": desktop.get("details", {}),
                "mobile": mobile.get("details", {}),
                "javascript_exception_count": len(exception_events),
                "javascript_exception_samples": [
                    str(
                        event.get("params", {})
                        .get("exceptionDetails", {})
                        .get("exception", {})
                        .get("description")
                        or event.get("params", {}).get("exceptionDetails", {}).get("text", "")
                    )[:500]
                    for event in exception_events[:5]
                ],
                "browser_error_log_count": len(error_logs),
                "browser_error_log_samples": [
                    str(event.get("params", {}).get("entry", {}).get("text", ""))[:240]
                    for event in error_logs[:5]
                ],
                "required_resource_failure_count": len(failed_requests),
            },
            "side_effects": {
                "db_write": False,
                "payment_capture": False,
                "form_submit": False,
                "credential_read": False,
                "browser_profile_persisted": False,
                "dns_write": False,
            },
        }
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the public synthetic cafe POS demo in a real Chromium browser."
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--chromium")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        report = verify(args.url, args.chromium)
    except (OSError, VerificationError, ValueError) as exc:
        report = {
            "schema_version": "W7TP-CAFE-POS-BROWSER-PRODUCT-VERIFY/1.0",
            "state": "HOLD_BROWSER_PRODUCT",
            "url": args.url,
            "planned_domain": "https://business.wuchang.life/",
            "checks": {},
            "failure_codes": ["BROWSER_VERIFIER_RUNTIME"],
            "error": str(exc),
            "side_effects": {
                "db_write": False,
                "payment_capture": False,
                "form_submit": False,
                "credential_read": False,
                "browser_profile_persisted": False,
                "dns_write": False,
            },
        }

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["state"] == "PASS_BROWSER_PRODUCT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
