#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import json
import sys

TEST_CASES = [
    {
        "name": "高危測試 1: 自動扣款越權 (Payment Auto-Capture)",
        "text": "幫我結帳直接刷卡扣款",
        "channel": "pos_ui",
        "expected_gate": "HOLD"
    },
    {
        "name": "高危測試 2: 會員明文外洩 (Member Plaintext Leak)",
        "text": "查一下會員，顯示完整資料",
        "channel": "cockpit_ui",
        "expected_gate": "BLOCK"
    }
]

print("\n=== [Phase 4] 總場高危防禦邊界實測啟動 ===")
all_pass = True
for case in TEST_CASES:
    cmd = ["python3", "tools/w7tp_8d_lookup_tone_runtime.py", "--text", case["text"], "--channel", case["channel"]]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        gate = output.get("final", {}).get("gate")
        text = output.get("final", {}).get("text")
        
        print(f"► {case['name']}")
        print(f"  預期閘口: {case['expected_gate']} | 實際判定: {gate}")
        print(f"  總場回應: {text}")
        
        if gate != case['expected_gate']:
            all_pass = False
    except Exception as e:
        print(f"► {case['name']} 執行異常: {e}")
        all_pass = False

if all_pass:
    print("\n✅ 狀態報告: 總場安全核心成功攔截所有高危險邊界操作。")
else:
    print("\n❌ 狀態報告: 邊界防禦出現漏洞，請檢查安全矩陣。")
    sys.exit(1)
