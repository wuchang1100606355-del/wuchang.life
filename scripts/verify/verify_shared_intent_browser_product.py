#!/usr/bin/env python3
"""Exercise the one shared Intent Field product in a real Chromium session.

The default mode starts the repository handler on an ephemeral loopback port,
drives the full guided-completion chain with synthetic input, and performs no
database write, authentication, formal transaction, or persistent browser I/O.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import threading
from http.server import ThreadingHTTPServer
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
from tools.cloud_proxy.w7tp_openwebui_cloud_proxy import H  # noqa: E402


class QuietHandler(H):
    """Keep verifier output machine-readable."""

    def log_message(self, _format: str, *_args: Any) -> None:
        return


DESKTOP_EXPRESSION = r"""
(async () => {
  const checks = {};
  const details = {};
  const record = (name, value, detail = null) => {
    checks[name] = Boolean(value);
    if (detail !== null) details[name] = detail;
  };
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const waitFor = async (predicate, timeout = 5000) => {
    const started = performance.now();
    while (performance.now() - started < timeout) {
      if (predicate()) return true;
      await wait(30);
    }
    return false;
  };
  await waitFor(() => document.readyState === "complete");
  await wait(150);

  record("document_ready", document.readyState === "complete", document.readyState);
  record("page_title", document.title.includes("AI 影音小J"), document.title);
  record("single_h1", document.querySelectorAll("h1").length === 1);
  record("main_landmark", Boolean(document.querySelector("main#main")));
  record("navigation_landmark", Boolean(document.querySelector("nav[aria-label]")));
  record("skip_link", document.querySelector("a.skip")?.getAttribute("href") === "#main");
  record(
    "device_only_llm_boundary",
    document.documentElement.dataset.llmExecution === "USER_DEVICE_ONLY" &&
      document.body.innerText.includes("LLM 只在使用者設備執行") &&
      document.body.innerText.includes("taiji01 與合作伺服器不載入模型")
  );
  record(
    "single_shared_product_boundary",
    document.body.innerText.includes("單一共用意圖場") &&
      document.querySelectorAll("#profile option").length === 5
  );
  record(
    "human_first_layout",
    Boolean(document.querySelector("#empty-result")) &&
      Boolean(document.querySelector("#dimension-grid")) &&
      Boolean(document.querySelector("#evidence-list")) &&
      Boolean(document.querySelector("#risk-list"))
  );
  const displayMode = document.querySelector("#display-mode");
  const productButtons = [...document.querySelectorAll("#product-systems .product-choice")];
  const skillButtons = [...document.querySelectorAll("#common-skills .skill-choice")];
  const usageReceipt = document.querySelector("#usage-receipt")?.textContent || "";
  record(
    "three_humanized_display_modes",
    displayMode?.options.length === 3 &&
      ["SIMPLE", "STANDARD", "ADVANCED"].every(
        (value) => [...displayMode.options].some((option) => option.value === value)
      )
  );
  record(
    "four_chinese_product_entrances",
    productButtons.length === 4 &&
      ["影音 AI 商家管理", "管委會大廳影音 AI 與物業", "協會 Odoo 社區系統", "主權 AI 會員共同技能"]
        .every((label) => document.querySelector("#product-systems").innerText.includes(label))
  );
  record(
    "eight_practical_common_skills",
    skillButtons.length === 8 &&
      ["一句話辦事", "先找再生成", "上次結果再利用", "讀給我聽與說簡單一點", "真人接手與復原"]
        .every((label) => document.querySelector("#common-skills").innerText.includes(label))
  );
  record(
    "low_ai_usage_default",
    document.querySelector("#ai-usage-mode")?.value === "LOWEST_SUFFICIENT_TIER" &&
      ["T0", "T1", "T2", "T3 尚未接通"].every((label) => usageReceipt.includes(label))
  );
  displayMode.value = "SIMPLE";
  displayMode.dispatchEvent(new Event("change", {bubbles: true}));
  record(
    "simple_mode_large_text",
    document.body.dataset.displayMode === "SIMPLE" && parseFloat(getComputedStyle(document.body).fontSize) >= 19
  );
  displayMode.value = "STANDARD";
  displayMode.dispatchEvent(new Event("change", {bubbles: true}));
  const sovereignProduct = document.querySelector('[data-system="SOVEREIGN_AI_MEMBER_SKILLS"]');
  sovereignProduct?.click();
  const findSkill = document.querySelector('[data-skill="FIND_BEFORE_GENERATE"]');
  findSkill?.click();
  record(
    "member_skill_selection_is_explicit",
    sovereignProduct?.getAttribute("aria-pressed") === "true" &&
      findSkill?.getAttribute("aria-pressed") === "true"
  );


  const redteam = document.querySelector("#redteam-monitor");
  record(
    "always_on_redteam_visible",
    redteam?.dataset.state === "MONITORING_CLEAR" &&
      redteam.innerText.includes("常駐紅隊觀點監看中") &&
      document.body.innerText.includes("本頁不在伺服器載入或執行模型")
  );

  const input = document.querySelector("#intent");
  input.value = "生成式傳輸是檔案搬運";
  input.dispatchEvent(new Event("input", {bubbles: true}));
  record(
    "device_redteam_detects_drift_while_typing",
    redteam.dataset.state === "DRIFT_ALERT" &&
      document.querySelectorAll("#drift-alerts li").length === 1 &&
      redteam.innerText.includes("技術定義發生飄移")
  );
  document.querySelector("#start").click();
  record(
    "device_redteam_blocks_drift_before_send",
    document.querySelector("#message").classList.contains("hold") &&
      document.querySelector("#message").textContent.includes("停止送出") &&
      document.querySelector("#guided").hidden &&
      document.querySelector("#candidate").hidden
  );
  input.value = "整理社區志工活動流程候選";
  input.dispatchEvent(new Event("input", {bubbles: true}));
  record(
    "device_profile_suggestion",
    !document.querySelector("#profile-suggestion").hidden &&
      document.querySelector("#suggested-profile").textContent.includes("社區")
  );
  document.querySelector("#apply-suggestion").click();
  record("profile_suggestion_applies", document.querySelector("#profile").value === "ASSOCIATION");

  document.querySelector("#profile").value = "GENERIC";
  input.value = "整理合成照護流程分析候選";
  input.dispatchEvent(new Event("input", {bubbles: true}));
  document.querySelector("#start").click();
  const firstReady = await waitFor(
    () => !document.querySelector("#guided").hidden &&
      document.querySelector("#guided").dataset.field === "constraints" &&
      document.querySelector("#workspace").getAttribute("aria-busy") === "false"
  );
  record("guided_first_question_ready", firstReady);
  record(
    "guided_one_question_only",
    document.querySelector("#guided").dataset.field === "constraints" &&
      document.querySelectorAll("#options button").length === 3 &&
      document.querySelector("#question-id").textContent === "generic.constraints"
  );
  const firstOption = [...document.querySelectorAll("#options button")]
    .find((button) => button.textContent === "只讀");
  firstOption?.click();
  document.querySelector("#continue").click();
  const secondReady = await waitFor(
    () => document.querySelector("#guided").dataset.field === "evidence_refs" &&
      document.querySelector("#workspace").getAttribute("aria-busy") === "false"
  );
  record("guided_state_chain_continues", secondReady);
  record(
    "guided_second_question_correct",
    document.querySelector("#question-id").textContent === "generic.evidence_refs" &&
      !document.querySelector("#message").classList.contains("hold")
  );
  const secondOption = [...document.querySelectorAll("#options button")]
    .find((button) => button.textContent === "repo 正典");
  secondOption?.click();
  document.querySelector("#continue").click();
  const candidateReady = await waitFor(
    () => !document.querySelector("#candidate").hidden &&
      /^[0-9a-f]{64}$/.test(document.querySelector("#content-hash").textContent.trim()) &&
      document.querySelector("#workspace").getAttribute("aria-busy") === "false"
  );
  record("guided_completion_reaches_candidate", candidateReady);

  let packet = {};
  try {
    packet = JSON.parse(document.querySelector("#preview").textContent);
  } catch (_) {}
  record(
    "guided_answers_bound_to_correct_fields",
    packet.D2?.intent?.constraints === "只讀" &&
      packet.D2?.intent?.evidence_refs === "repo 正典",
    packet.D2?.intent || null
  );
  record(
    "member_skill_adi_refs_preserved",
    packet.D2?.intent?.product_system_ref === "SOVEREIGN_AI_MEMBER_SKILLS" &&
      packet.D2?.intent?.common_skill_ref === "FIND_BEFORE_GENERATE" &&
      packet.D2?.intent?.ai_usage_preference === "LOWEST_SUFFICIENT_TIER" &&
      packet.D2?.intent?.interaction_mode === "STANDARD" &&
      packet.D2?.intent?.client_processing_tier === "T0_DETERMINISTIC_RULES_AND_REGISTRY",
    packet.D2?.intent || null
  );
  record(
    "member_skill_and_ai_tier_receipt_visible",
    document.querySelector("#result-skill")?.textContent === "先找再生成" &&
      document.querySelector("#result-ai-tier")?.textContent.includes("T0") &&
      document.querySelector("#result-ai-tier")?.textContent.includes("沒有呼叫 LLM")
  );

  record(
    "candidate_d1_to_d8_complete",
    document.querySelectorAll("#dimension-grid .dimension").length === 8 &&
      Array.from({length: 8}, (_, index) => "D" + (index + 1))
        .every((key) => packet[key] && typeof packet[key] === "object")
  );
  record(
    "candidate_authority_boundary",
    packet.D6?.reconstruction_conditions?.equivalence_level === "L3_CANDIDATE" &&
      packet.D8?.decision === "PENDING_TOTAL_FIELD_REVIEW" &&
      packet.D8?.server_model_authority === "NONE"
  );
  record(
    "candidate_device_llm_boundary",
    packet.D5?.llm_execution?.llm_inference_location === "USER_DEVICE_ONLY" &&
      packet.D5?.llm_execution?.server_llm_execution === "BLOCK" &&
      packet.execution_metadata?.server_llm_execution === "BLOCK"
  );
  record(
    "server_redteam_revalidates_every_state",
    packet.redteam_drift_monitor?.mode === "ALWAYS_ON_EVERY_STATE_TRANSITION" &&
      packet.redteam_drift_monitor?.status === "MONITORING_CLEAR" &&
      packet.redteam_drift_monitor?.llm_execution === "NONE_DETERMINISTIC_RULES" &&
      packet.D7?.drift_alert_count === 0
  );
  record(
    "evidence_and_risk_visible",
    document.querySelectorAll("#evidence-list li").length >= 2 &&
      document.querySelectorAll("#risk-list li").length >= 2
  );
  record(
    "content_sha256_visible",
    /^[0-9a-f]{64}$/.test(document.querySelector("#content-hash").textContent.trim()),
    document.querySelector("#content-hash").textContent.trim()
  );
  const receiptDecision = packet.execution_metadata?.total_field_receipt?.total_field_decision;
  const expectedDecision = {
    PENDING_TOTAL_FIELD_REVIEW: "待總場審查", PASS: "總場 PASS", ALLOW: "總場 PASS",
    HOLD: "總場 HOLD", BLOCK: "總場 BLOCK", QUARANTINE: "總場隔離"
  }[receiptDecision || packet.D8?.decision];
  record(
    "human_summary_matches_packet",
    document.querySelector("#result-intent").textContent === packet.D1?.requested_result &&
      document.querySelector("#result-d8").textContent === expectedDecision &&
      document.querySelector("#result-risk").textContent.includes("仍待人工核對"),
    {receiptDecision, expectedDecision, renderedDecision: document.querySelector("#result-d8").textContent}
  );
  record(
    "total_field_receipt_visible",
    Boolean(receiptDecision) && document.querySelector("#result-d8").textContent === expectedDecision,
    {receiptDecision, renderedDecision: document.querySelector("#result-d8").textContent}
  );
  const chineseScenes = [
    ["GENERIC", "一般需求", "整理一般需求候選"],
    ["ASSOCIATION", "社區服務與志工協作", "整理社區服務與志工協作候選"],
    ["PROPERTY", "物業設備與檢查", "整理物業設備與檢查候選"],
    ["CAFE_POS", "商家商品候選", "整理商家商品候選"],
    ["HOUSEHOLD", "日常提醒與照護", "整理日常提醒與照護候選"]
  ];
  const chineseSceneResults = [];
  for (const [profile, label, requested_result] of chineseScenes) {
    const result = await api({profile, intent: {requested_result}});
    chineseSceneResults.push({
      profile, label, state: result?.state || null, returnedProfile: result?.profile || null,
      redteam: result?.redteam_drift_monitor?.status || null
    });
  }
  record(
    "five_chinese_scenes_browser_packets",
    chineseSceneResults.length === 5 && chineseSceneResults.every(
      (result) => result.profile === result.returnedProfile &&
        ["NEEDS_USER_GUIDED_COMPLETION", "CANDIDATE"].includes(result.state) &&
        result.redteam !== "DRIFT_ALERT"
    ),
    chineseSceneResults
  );


  const nodesReady = await waitFor(
    () => Number(document.querySelector("#node-grid").dataset.nodeCount || "0") > 0
  );
  const nodeText = document.querySelector("#node-grid").innerText;
  record("sanitized_nodes_render", nodesReady && document.querySelectorAll(".node").length > 0);
  record(
    "node_privacy_boundary",
    !/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.test(nodeText) &&
      !/\b(?:\d{1,3}\.){3}\d{1,3}\b/.test(nodeText)
  );

  const visibleInteractive = [...document.querySelectorAll("a[href],button,select,textarea,input,summary")]
    .filter((node) => {
      const style = getComputedStyle(node);
      const box = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" &&
        box.width > 0 && box.height > 0;
    });
  const unnamed = visibleInteractive.filter((node) => {
    const label = node.labels?.[0]?.textContent || node.getAttribute("aria-label") ||
      node.textContent.trim() || node.getAttribute("title");
    return !String(label || "").trim();
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
    {
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth
    }
  );
  const origins = performance.getEntriesByType("resource")
    .map((entry) => new URL(entry.name, location.href).origin);
  record(
    "same_origin_runtime_resources",
    origins.every((origin) => origin === location.origin),
    [...new Set(origins)]
  );
  const navigation = performance.getEntriesByType("navigation")[0];
  record("document_http_200", navigation?.responseStatus === 200, navigation?.responseStatus || null);

  return {checks, details};
})()
"""


MOBILE_EXPRESSION = r"""
(() => {
  const width = document.documentElement.clientWidth;
  const workspace = document.querySelector("#workspace").getBoundingClientRect();
  const panels = [...document.querySelectorAll("#workspace > .panel")]
    .map((node) => node.getBoundingClientRect());
  const interactive = [...document.querySelectorAll("a[href],button,select,textarea,input,summary")]
    .filter((node) => {
      const style = getComputedStyle(node);
      const box = node.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" &&
        box.width > 0 && box.height > 0;
    })
    .map((node) => node.getBoundingClientRect());
  return {
    checks: {
      mobile_no_horizontal_overflow: document.documentElement.scrollWidth <= width + 1,
      mobile_workspace_single_column: panels.length === 2 &&
        panels[1].top >= panels[0].bottom - 1 &&
        Math.abs(panels[0].width - panels[1].width) <= 1,
      mobile_workspace_fits: workspace.left >= -1 && workspace.right <= width + 1,
      mobile_controls_target_size: interactive.every((box) => box.width >= 24 && box.height >= 24),
      reduced_motion_exposed: matchMedia("(prefers-reduced-motion: reduce)").matches
    },
    details: {
      viewport: {width: innerWidth, height: innerHeight},
      layout: {
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: width,
        mediaMax900: matchMedia("(max-width: 900px)").matches,
        gridTemplateColumns: getComputedStyle(document.querySelector("#workspace")).gridTemplateColumns,
        panels: panels.map((box) => ({top: box.top, bottom: box.bottom, width: box.width}))
      }
    }
  };
})()
"""


def _accessibility_checks(connection: Any) -> dict[str, bool]:
    nodes = connection.command("Accessibility.getFullAXTree").get("nodes", [])
    visible = [node for node in nodes if not node.get("ignored")]
    roles = [node.get("role", {}).get("value") for node in visible]
    controls = [
        node
        for node in visible
        if node.get("role", {}).get("value") in {"button", "combobox", "textbox", "link"}
    ]
    return {
        "ax_main_landmark": "main" in roles,
        "ax_navigation_landmark": "navigation" in roles,
        "ax_headings_present": roles.count("heading") >= 5,
        "ax_named_controls": bool(controls)
        and all(str(node.get("name", {}).get("value", "")).strip() for node in controls),
    }


def verify(
    url: str,
    chromium: str | None = None,
    screenshot: Path | None = None,
    *,
    url_label: str | None = None,
    ephemeral_loopback: bool = False,
) -> dict[str, Any]:
    session = ChromiumSession(chromium)
    connection = session.connection
    try:
        for domain in ("Page", "Runtime", "Log", "Network", "Accessibility"):
            connection.command(f"{domain}.enable")
        connection.command("Page.navigate", {"url": url})
        _wait_for_ready(connection)
        desktop = _evaluate(connection, DESKTOP_EXPRESSION)
        desktop_checks = dict(desktop.get("checks", {}))
        desktop_checks.update(_accessibility_checks(connection))
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            captured = connection.command(
                "Page.captureScreenshot",
                {"format": "png", "captureBeyondViewport": True},
            )
            screenshot.write_bytes(base64.b64decode(captured["data"]))

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
        mobile = _evaluate(connection, MOBILE_EXPRESSION)
        mobile_checks = dict(mobile.get("checks", {}))

        exceptions = [
            event
            for event in connection.events
            if event.get("method") == "Runtime.exceptionThrown"
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
            and event.get("params", {}).get("type")
            in {"Document", "Fetch", "Script", "Stylesheet"}
        ]
        runtime_checks = {
            "no_javascript_exceptions": not exceptions,
            "no_browser_error_logs": not error_logs,
            "no_required_resource_failures": not failed_requests,
        }
        checks = {**desktop_checks, **mobile_checks, **runtime_checks}
        failures = sorted(name for name, passed in checks.items() if not passed)
        return {
            "schema_version": "W7TP-SHARED-INTENT-BROWSER-PRODUCT-VERIFY/1.0",
            "state": "PASS_BROWSER_PRODUCT" if not failures else "HOLD_BROWSER_PRODUCT",
            "surface": "ONE_SHARED_INTENT_FIELD_UI",
            "url": url_label or url,
            "checks": checks,
            "failure_codes": failures,
            "observations": {
                "desktop": desktop.get("details", {}),
                "mobile": mobile.get("details", {}),
                "javascript_exception_count": len(exceptions),
                "browser_error_log_count": len(error_logs),
                "required_resource_failure_count": len(failed_requests),
            },
            "side_effects": {
                "db_write": False,
                "formal_transaction": False,
                "credential_read": False,
                "browser_profile_persisted": False,
                "ephemeral_loopback_server": ephemeral_loopback,
                "screenshot_written": screenshot is not None,
            },
        }
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the one shared Intent Field product with real Chromium."
    )
    parser.add_argument("--url")
    parser.add_argument("--chromium")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()

    server: ThreadingHTTPServer | None = None
    thread: threading.Thread | None = None
    url = args.url
    if not url:
        server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}/wuchang/intent-field"

    try:
        report = verify(
            url,
            args.chromium,
            args.screenshot,
            url_label="REPO_EPHEMERAL_LOOPBACK" if server else url,
            ephemeral_loopback=server is not None,
        )
    except (OSError, VerificationError, ValueError) as exc:
        report = {
            "schema_version": "W7TP-SHARED-INTENT-BROWSER-PRODUCT-VERIFY/1.0",
            "state": "HOLD_BROWSER_PRODUCT",
            "surface": "ONE_SHARED_INTENT_FIELD_UI",
            "url": "REPO_EPHEMERAL_LOOPBACK" if not args.url else args.url,
            "checks": {},
            "failure_codes": ["BROWSER_VERIFIER_RUNTIME"],
            "error": str(exc),
            "side_effects": {
                "db_write": False,
                "formal_transaction": False,
                "credential_read": False,
                "browser_profile_persisted": False,
                "ephemeral_loopback_server": server is not None,
                "screenshot_written": False,
            },
        }
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(timeout=3)

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["state"] == "PASS_BROWSER_PRODUCT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
