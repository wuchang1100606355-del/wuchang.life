#!/usr/bin/env python3
"""Verify association patent-subject and revenue-governance docs.

This verifier reads only docs and generated reports. It does not read secrets,
write Odoo DB, create POS orders, capture payments, restart services, deploy,
generate embeddings, or call external APIs.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_DOC = ROOT / "docs/total_field/ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE.md"
HOMEPAGE_DOC = ROOT / "docs/product/ASSOCIATION_PATENT_HOMEPAGE_WORDING.md"
REPORT = ROOT / "runtime/d8_db/reports/ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE_FINAL_REPORT.json"
SEAL = ROOT / "runtime/total_field/status/ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE_SEAL.md"

REQUIRED_FILES = [GOVERNANCE_DOC, HOMEPAGE_DOC, REPORT, SEAL]

REQUIRED_GOVERNANCE_TEXT = [
    "ASSOCIATION_PATENT_GOVERNANCE_DRAFT_READY",
    "not legal, patent, tax, accounting, investment, or filing advice",
    "new chair states an intent to complete legal-personhood preparation",
    "Pre-legal-personhood LOI",
    "Legal-personhood gate",
    "Letter Of Intent Safe Terms",
    "no patent assignment, no donation completed, no revenue receipt",
    "不發生專利權移轉、捐贈完成、收益承接",
    "下一次大會前完成法人化準備",
    "未法人化前，協會不得被描述為已能承接",
    "patent could be developed privately without public-interest conversion",
    "No-Personal-Benefit Statement",
    "不是為取得個人利益",
    "Public-Interest Logic Loop",
    "公益不是口號",
    "引眾力、注眾益",
    "mechanism that completes the invention's governance logic",
    "Intent Field Definition",
    "意圖場真諦就是社區互愛互助的意義",
    "shared direction of care before action",
    "Home Harbor And Community Protection",
    "家是休息的避風港",
    "引高科技數位 AI 科技護社區",
    "Home is the protected purpose",
    "Community Invention And AI Sovereign Service",
    "我的發明就是社區的發明",
    "居住本社區者免費",
    "AI sovereign service",
    "Final development work",
    "新北市三重區五常社區發展協會",
    "Inventor attribution",
    "Legal-personhood readiness",
    "General assembly or association-authorized resolution",
    "Written inventor-to-association donation",
    "Patent attorney review",
    "Accountant or tax advisor review",
    "Conflict-of-interest disclosure",
    "formal resolution, and written agreement",
    "AI role",
]

REQUIRED_HOMEPAGE_TEXT = [
    "ASSOCIATION_PATENT_HOMEPAGE_WORDING_READY",
    "Core Mission Statement",
    "公益不是口號，而是一種自我實現的硬道理",
    "引眾力、注眾益",
    "Intent Field Statement",
    "意圖場的真諦，就是社區互愛互助的意義",
    "可確認、可查核、可翻譯、可交接",
    "Home Harbor Statement",
    "家是休息的避風港，社區就是為了保護家而存在",
    "高科技、數位工具與 AI 輔助導入社區",
    "Community Invention Statement",
    "我的發明就是社區的發明",
    "居住本社區者將以社區公益規則優先使用",
    "Development Status Statement",
    "AI 主權服務",
    "正在進行最後開發與驗證工作",
    "社區數位公益計畫",
    "聊國咖啡館重新總店 / 上品食品行",
    "本會新任理事長",
    "下一次大會前完成法人化準備",
    "未法人化及未經大會決議前",
    "Letter Of Intent Paragraph",
    "不代表專利權已移轉、捐贈已完成、收益已承接",
    "Voluntary Public-Interest Statement",
    "而非取得個人對價利益",
    "比照學術機構技術移轉精神",
    "正式專利申請權、專利權、授權收益、回捐與會計處理",
    "咖啡館是本計畫的實習場域與營運復原節點",
    "小J / Total Field",
    "AI 產出一律屬候選建議",
    "Google Nonprofit-Safe Notes",
]

REQUIRED_REPORT_TEXT = [
    '"state": "PASS_ASSOCIATION_PATENT_GOVERNANCE_DRAFT_READY"',
    '"action": "ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE_DONE"',
    '"governance_doc": "docs/total_field/ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE.md"',
    '"homepage_wording": "docs/product/ASSOCIATION_PATENT_HOMEPAGE_WORDING.md"',
    '"professional_review_required": true',
    '"legal_personhood_gate": true',
    '"general_assembly_contract_donation_gate": true',
    '"pre_legal_personhood_loi_allowed": true',
    '"loi_no_transfer_no_donation_no_revenue_receipt": true',
    '"voluntary_public_interest_conversion": true',
    '"no_personal_consideration_claim": true',
    '"public_interest_logic_loop": true',
    '"intent_field_mutual_care": true',
    '"home_harbor_community_protection": true',
    '"community_invention": true',
    '"resident_free_use_after_governance": true',
    '"patent_revenue_equipment_support_after_review": true',
    '"ai_sovereign_service_development_in_progress": true',
]

REQUIRED_SEAL_TEXT = [
    "STATE=PASS_ASSOCIATION_PATENT_GOVERNANCE_DRAFT_READY",
    "ACTION=ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE_DONE",
    "GOVERNANCE_DOC=docs/total_field/ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE.md",
    "HOMEPAGE_WORDING=docs/product/ASSOCIATION_PATENT_HOMEPAGE_WORDING.md",
    "PROFESSIONAL_REVIEW_REQUIRED=TRUE",
    "LEGAL_PERSONHOOD_GATE=TRUE",
    "GENERAL_ASSEMBLY_CONTRACT_DONATION_GATE=TRUE",
    "PRE_LEGAL_PERSONHOOD_LOI_ALLOWED=TRUE",
    "LOI_NO_TRANSFER_NO_DONATION_NO_REVENUE_RECEIPT=TRUE",
    "VOLUNTARY_PUBLIC_INTEREST_CONVERSION=TRUE",
    "NO_PERSONAL_CONSIDERATION_CLAIM=TRUE",
    "PUBLIC_INTEREST_LOGIC_LOOP=TRUE",
    "INTENT_FIELD_MUTUAL_CARE=TRUE",
    "HOME_HARBOR_COMMUNITY_PROTECTION=TRUE",
    "COMMUNITY_INVENTION=TRUE",
    "RESIDENT_FREE_USE_AFTER_GOVERNANCE=TRUE",
    "PATENT_REVENUE_EQUIPMENT_SUPPORT_AFTER_REVIEW=TRUE",
    "AI_SOVEREIGN_SERVICE_DEVELOPMENT_IN_PROGRESS=TRUE",
]

SAFETY_FLAGS = [
    "SECRET_READ=FALSE",
    "MEMBER_PLAINTEXT_READ=FALSE",
    "RAW_AUDIO_SAVED=FALSE",
    "PRODUCTION_DB_WRITE=FALSE",
    "ODOO_DB_WRITE=FALSE",
    "POS_ORDER_CREATED=FALSE",
    "PAYMENT_CAPTURE=FALSE",
    "SERVICE_RESTART=FALSE",
    "DEPLOY=FALSE",
    "PRODUCTION_RELEASE=FALSE",
    "EMBEDDING_GENERATED=FALSE",
    "DO_NOT_TOUCH_AGENTS_MD=TRUE",
]

FORBIDDEN_TEXT = [
    "STATE=PRODUCTION_READY",
    "patent already granted",
    "association is already legal patent owner",
    "tax deductible guaranteed",
    "AI autonomously approves",
    "SECRET_READ=TRUE",
    "MEMBER_PLAINTEXT_READ=TRUE",
    "ODOO_DB_WRITE=TRUE",
    "POS_ORDER_CREATED=TRUE",
    "PAYMENT_CAPTURE=TRUE",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_all(text: str, required: list[str], label: str) -> None:
    for item in required:
        if item not in text:
            fail(f"{label}_required_text_missing:{item}")


def main() -> int:
    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing:{path.relative_to(ROOT)}")

    governance = read(GOVERNANCE_DOC)
    homepage = read(HOMEPAGE_DOC)
    report = read(REPORT)
    seal = read(SEAL)
    combined = "\n".join([governance, homepage, report, seal])

    require_all(governance, REQUIRED_GOVERNANCE_TEXT, "governance_doc")
    require_all(homepage, REQUIRED_HOMEPAGE_TEXT, "homepage_doc")
    require_all(report, REQUIRED_REPORT_TEXT, "report")
    require_all(seal, REQUIRED_SEAL_TEXT, "seal")

    for flag in SAFETY_FLAGS:
        if flag not in combined:
            fail(f"safety_flag_missing:{flag}")

    for forbidden in FORBIDDEN_TEXT:
        if forbidden in combined:
            fail(f"forbidden_text_present:{forbidden}")

    print("STATE=PASS_ASSOCIATION_PATENT_GOVERNANCE_DRAFT_READY")
    print("ACTION=VERIFY_ASSOCIATION_PATENT_SUBJECT_AND_REVENUE_GOVERNANCE")
    print(f"GOVERNANCE_DOC={GOVERNANCE_DOC.relative_to(ROOT)}")
    print(f"HOMEPAGE_WORDING={HOMEPAGE_DOC.relative_to(ROOT)}")
    print(f"REPORT={REPORT.relative_to(ROOT)}")
    print(f"SEAL={SEAL.relative_to(ROOT)}")
    print("ASSOCIATION_PATENT_SUBJECT_INTENT=TRUE")
    print("LEGAL_PERSONHOOD_GATE=TRUE")
    print("GENERAL_ASSEMBLY_CONTRACT_DONATION_GATE=TRUE")
    print("PRE_LEGAL_PERSONHOOD_LOI_ALLOWED=TRUE")
    print("LOI_NO_TRANSFER_NO_DONATION_NO_REVENUE_RECEIPT=TRUE")
    print("VOLUNTARY_PUBLIC_INTEREST_CONVERSION=TRUE")
    print("NO_PERSONAL_CONSIDERATION_CLAIM=TRUE")
    print("PUBLIC_INTEREST_LOGIC_LOOP=TRUE")
    print("INTENT_FIELD_MUTUAL_CARE=TRUE")
    print("HOME_HARBOR_COMMUNITY_PROTECTION=TRUE")
    print("COMMUNITY_INVENTION=TRUE")
    print("RESIDENT_FREE_USE_AFTER_GOVERNANCE=TRUE")
    print("PATENT_REVENUE_EQUIPMENT_SUPPORT_AFTER_REVIEW=TRUE")
    print("AI_SOVEREIGN_SERVICE_DEVELOPMENT_IN_PROGRESS=TRUE")
    print("PROFESSIONAL_REVIEW_REQUIRED=TRUE")
    print("HOMEPAGE_GOOGLE_NONPROFIT_SAFE_WORDING=TRUE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
