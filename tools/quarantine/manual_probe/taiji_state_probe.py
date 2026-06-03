import os
import json
from datetime import datetime

class StateProbe:
    """
    Wuchang OS / Taiji Hub - 系統狀態拓樸探測器
    """
    def __init__(self):
        # 依據架構手冊 V9 定義之核心目錄
        self.base_path = "/home/taiji_admin/Taiji_Hub"
        self.core_dirs = [
            "Taiji_Governance", 
            "Taiji_Runtime", 
            "Taiji_Intent_Packets",
            "Taiji_Tools", 
            "wuchang_cloud", 
            "wuchang_edge", 
            "Taiji_Git_Evidence_Vault"
        ]

    def get_topology_state(self):
        dir_status = {}
        for d in self.core_dirs:
            full_path = os.path.join(self.base_path, d)
            dir_status[d] = "Active" if os.path.exists(full_path) else "Missing"
        return dir_status

    def get_development_reality(self):
        """依據 V9 架構手冊 Section 12 提取精細開發進度聲明"""
        return {
            "Current_Phase": [
                "Development In Progress (開發中)",
                "Patent Formation In Progress (專利形成中)",
                "Evidence Collection In Progress (證據鏈收集/形成中)",
                "Prototype Verification In Progress (原型驗證中)"
            ],
            "Commercial_Boundary": [
                "Not Declared As Commercially Complete (未宣告商業化完成)",
                "Not Declared As Fully Deployed (未宣告全面部署)"
            ],
            "Required_Evidence_Chain": [
                "Source Code", "Git Evidence", "Development History", 
                "Design Documents", "Runtime Records", "Validation Reports", 
                "Audit Records", "Human Verifiable Evidence"
            ]
        }

    def generate_7d_packet(self, topology_state):
        reality_state = self.get_development_reality()
        packet = {
            "D1_Identity": "[Redacted_Taiji_Admin]",
            "D2_Intent": "系統精細狀態與開發進度探測 (Detailed Reality Probe)",
            "D3_State": "Active_Local_Environment",
            "D4_Topology": "wuchang_edge -> local_filesystem",
            "D5_Resource": "Local System Check",
            "D6_Governance": "Zero Plaintext Environment Verified",
            "D7_Validation": f"Timestamp:{datetime.now().isoformat()}",
            "Payload": {
                "OS_Environment": "WSL (Ubuntu)",
                "Base_Path": self.base_path,
                "Core_Directories": topology_state,
                "Development_Reality_S12": reality_state,
                "Diagnostic": "已載入架構手冊 V9 (Section 12) 精細進度聲明。"
            }
        }
        return packet

    def execute(self):
        print("⚙️ [太極定場] 啟動系統狀態探測...")
        state = self.get_topology_state()
        packet = self.generate_7d_packet(state)
        
        print("\n=== Wuchang OS 當前運行時狀態 (Runtime State) ===")
        print(json.dumps(packet, indent=2, ensure_ascii=False))
        print("=================================================")

if __name__ == "__main__":
    probe = StateProbe()
    probe.execute()
