{
    "name": "WuChang Association Member Trust",
    "version": "18.0.1.1.1",
    "category": "Governance",
    "summary": "Association-domain member data trust, merchant tenant governance, consent scope and AI audit integration.",
    "author": "WuChang / Liaoguo Cafe",
    "license": "LGPL-3",
    "depends": [
        "base",
        "contacts",
        "wuchang_cafe_ai_gateway"
    ],
    "data": [
        "security/association_groups.xml",
        "security/association_record_rules.xml",
        "security/ir.model.access.csv",
        "views/member_trust_views.xml"
    ],
    "installable": True,
    "application": False
}
