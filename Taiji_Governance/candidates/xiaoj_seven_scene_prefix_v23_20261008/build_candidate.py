"""Build an isolated seven-prefix presentation from the EXISTING XiaoJ product.

No live API, Odoo DB change, member data, sign-in impersonation or authority grant.
This extends only the existing product *candidate* homepage in an isolated copy.
"""
from __future__ import annotations
import difflib
import hashlib
import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/taiji_admin/Taiji_Hub")
HERE = ROOT / "Taiji_Governance/candidates/xiaoj_seven_scene_prefix_v23_20261008"
SOURCE = ROOT / "products/wuchang_xiaoj_community"
DEST = HERE / "product_preview"
DATA = json.loads((HERE / "SCENE_PREFIX_VIEW_CANDIDATE.json").read_text(encoding="utf-8"))
assert DATA["schema_version"] == "W7TP_XIAOJ_V23_SEVEN_SCENE_VIEW_CANDIDATE/1"
assert DATA["one_natural_person_one_identity_packet"] is True
assert DATA["identity_canonical_ref"] == "canonical_ref:W7TP_8D_IDENTITY_PACKET"
assert DATA["scene_prefixes_are_authority"] is False
assert DATA["runtime_read_grants"] == DATA["runtime_write_grants"] == []
assert DATA["immutable_identity_prefix_ref"] is None
assert DATA["total_field_d8_action_approval_ref"] is None
services = DATA["scene_profiles"]
assert len(services) == 7
assert len({s["key"] for s in services}) == 7
assert not DEST.exists(), "candidate preview would overwrite existing files"
assert SOURCE.is_dir()

shutil.copytree(
    SOURCE, DEST,
    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
)
index_path = DEST / "index.html"
old_index = (SOURCE / "index.html").read_text(encoding="utf-8")
new_index = old_index
css_link = '    <link rel="stylesheet" href="./assets/styles.css">'
assert old_index.count(css_link) == 1
new_index = new_index.replace(
    css_link, css_link + '\n    <link rel="stylesheet" href="./scene-pages/scene-prefix.css">',
    1,
)
add_at = '        <div class="hero-shell"'
assert new_index.count(add_at) == 1

esc = lambda v: html.escape(str(v), quote=True)
homepage = [
    '        <section class="section seven-prefix-section" id="xiaoj-seven-scenes" aria-labelledby="seven-prefix-title">',
    '          <p class="section-kicker">一個小J・七個場景</p>',
    '          <h2 id="seven-prefix-title">小J想幫你完成什麼？</h2>',
    '          <p>同一自然人身分原胞封包、同一小J核心。每個場景都有介紹與管理總頁面；可用技能、可讀資料、可修改範圍及限制，正式以當前總場驗證封包為準。</p>',
    '          <p class="prefix-tag warn">隔離候選：目前不會因切換場景而取得權限或修改資料。</p>',
    '          <div class="seven-prefix-grid" aria-label="七種小J場景">'
]
for s in services:
    homepage += [
       '            <a class="seven-prefix-card" href="./scene-pages/' + esc(s["key"]) + '.html">',
       '              <span class="seven-prefix-letter" aria-hidden="true">' + esc(s["symbol"]) + '</span>',
       '              <strong>' + esc(s["name"]) + '</strong>',
       '              <small>' + esc(s["mini"]) + '</small>',
       '              <span>介紹與管理 →</span>',
       '            </a>',
    ]
homepage += [
    '          </div>',
    '        </section>',
    ''
]
new_index = new_index.replace(add_at, "\n".join(homepage) + "\n" + add_at, 1)
index_path.write_text(new_index, encoding="utf-8")
pages_dir = DEST / "scene-pages"
pages_dir.mkdir()
shutil.copy2(HERE / "PREFIX_SCENE_STYLE.css", pages_dir / "scene-prefix.css")

def li(values, tip=None):
    rows = ['<ul class="prefix-list">']
    for value in values:
        rows.append('  <li>' + esc(value) + (('<small>' + esc(tip) + '</small>') if tip else '') + '</li>')
    rows.append('</ul>')
    return "\n".join(rows)

def nav(selected):
    rows = ['<nav class="prefix-switch" aria-label="切換小J場景">']
    for svc in services:
        key = svc["key"]
        flag = ' aria-current="page"' if key == selected else ""
        rows.append('  <a href="./' + esc(key) + '.html"' + flag + '>' + esc(svc["name"]) + '</a>')
    rows.append('</nav>')
    return "\n".join(rows)

common_notice = (
 "這裡是隔離設計候選。系統尚未取得可核驗的本人身分前綴及動作級 D8 收據，"
 "因此所有技能、資料閱讀及寫入範圍目前均顯示為待授權；切換場景不會授權。"
)
for i,s in enumerate(services,1):
    page = [
        '<!doctype html>',
        '<html lang="zh-Hant">',
        '<head>',
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width,initial-scale=1">',
        '  <meta name="robots" content="noindex,nofollow">',
        '  <meta name="referrer" content="strict-origin-when-cross-origin">',
        '  <meta http-equiv="Content-Security-Policy" content="default-src \'self\'; img-src \'self\'; style-src \'self\'; script-src \'none\'; connect-src \'none\'; object-src \'none\'; base-uri \'self\'; form-action \'none\'">',
        '  <meta name="description" content="' + esc(s["mini"]) + '">',
        '  <title>' + esc(s["name"]) + '｜介紹與管理｜小J</title>',
        '  <link rel="stylesheet" href="./scene-prefix.css">',
        '</head>',
        '<body>',
        '<a class="skip" href="#main">跳到主要內容</a>',
        '<header class="prefix-top"><div class="prefix-top-content">',
        '  <a class="prefix-brand" href="../index.html#home" aria-label="小J共同服務首頁">',
        '    <span class="prefix-logo" aria-hidden="true">J</span>',
        '    <span>小J合一服務<small>同一模型 · 同一核心 · 同一身分原胞</small></span>',
        '  </a>',
        '  <a class="prefix-home-link" href="../index.html#home">返回小J首頁</a>',
        '</div></header>',
        '<main id="main" class="prefix-shell">',
        '<div class="prefix-crumb"><a href="../index.html#home">首頁</a> / ' + esc(s["name"]) + ' / 管理總頁面</div>',
        '<section class="prefix-hero" aria-labelledby="scene-title">',
        '<div>',
        '<div class="prefix-eyebrow">場景 ' + str(i).zfill(2) + ' / 07 · SINGLE XIAOJ SERVICE</div>',
        '<h1 id="scene-title">' + esc(s["name"]) + '</h1>',
        '<p class="prefix-lead">' + esc(s["intro"]) + '</p>',
        '<div class="prefix-hero-tags">',
        '<span class="prefix-tag">共用身分原胞</span>',
        '<span class="prefix-tag">場景前綴：' + esc(s["prefix"]) + '</span>',
        '<span class="prefix-tag warn">權限待核對</span>',
        '</div>',
        '</div>',
        '<img src="../assets/xiaoj-white-haired-service-worker.png" alt="小J共用服務形象（非獨立模型）">',
        '</section>',
        nav(s["key"]),
        '<section class="prefix-section" aria-labelledby="management">',
        '<h2 id="management">我的場景管理</h2>',
        '<p class="prefix-muted">同一身分根下的場景能力呈現；沒有獨立會員、獨立記憶或可自行修改的權威。</p>',
        '<div class="prefix-grid">',
        '<article class="prefix-panel"><h3>身分與服務狀態 <span class="badge">待驗證</span></h3>',
        '<p>自然人身分根：尚未綁定正式引用。<br>登入來源：待驗證。<br>總場 D8 動作授權：未核定。</p></article>',
        '<article class="prefix-panel"><h3>可讀資料 <span class="badge">待核對</span></h3>',
        li(s["read"]), '</article>',
        '<article class="prefix-panel"><h3>可修改動作 <span class="badge">尚未開通</span></h3>',
        li(s["write"]), '</article>',
        '</div>',
        '<p class="prefix-notice"><strong>目前不執行資料修改。</strong> ' + esc(common_notice) + '</p>',
        '</section>',
        '<section class="prefix-section" aria-labelledby="about-scene">',
        '<h2 id="about-scene">這個小J能協助什麼？</h2>',
        '<p class="prefix-muted">' + esc(s["mini"]) + '。能力來源仍須由總場及對應服務器官核驗。</p>',
        '<div class="prefix-grid">',
    ]
    for skill in s["skills"]:
        page += [
            '<article class="prefix-panel"><h3>' + esc(skill) + '</h3>',
            '<small>候選技能 · 正式能力未登錄／未授權，不代表目前可呼叫</small>',
            '</article>'
        ]
    page += [
        '</div>',
        '<h3>你可以這樣問</h3>',
        '<p class="prefix-example">「' + esc(s["help"].removeprefix("例如：").removesuffix("。")) + '」</p>',
        '</section>',
        '<section class="prefix-section" aria-labelledby="bounds">',
        '<h2 id="bounds">邊際限制及權限治理</h2>',
        '<p class="prefix-muted">實際上限必須讀取當次封包、有效期限、依賴及授權收據；未知時停止相關動作。</p>',
        '<details class="prefix-details" open><summary>本場景的限制</summary>',
        li(s["limits"]), '</details>',
        '<details class="prefix-details"><summary>如何調整技能與權限？</summary>',
        '<p>由本人或合法授權者提出申請，經現行身分封包、服務器官與總場 D8 確認後生效。'
        '若缺少可核對的能力登錄、授權、額度、期限或風險證據，這個場景只保留介紹及候選規劃，不自行新增權限。</p>',
        '</details>',
        '<details class="prefix-details"><summary>如何確認讀取與修改紀錄？</summary>',
        '<p>正式版本應顯示每次動作的用途、授權來源、作用對象、時間、效果、稽核收據與可撤回條件。'
        '目前無可信執行紀錄可展示，不能以空白紀錄宣稱沒有事件。</p>',
        '</details>',
        '</section>',
        '<div class="prefix-links">',
        '<a class="prefix-link" href="../index.html#home">切換其他小J</a>',
        '<a class="prefix-link alt" href="../index.html#xiaoj">共用小J對話候選</a>',
        '</div>',
        '<footer class="prefix-footer">',
        '<strong>本頁只展示場景候選。</strong>不讀會員明文、不送出申請、不變更 Odoo 或 Open WebUI、不建立新的身分根；'
        '連結至共用對話僅展示原產品候選，尚未攜帶已核准的場景前綴。',
        '</footer>',
        '</main>',
        '</body>',
        '</html>',
    ]
    (pages_dir / (s["key"] + ".html")).write_text("\n".join(page) + "\n", encoding="utf-8")

# Open WebUI native 7 suggestion cards are only draft UI text, NOT trusted capability.
suggestions = [
    {
        "title": [s["name"], s["mini"]],
        "content": "我目前選擇「" + s["name"] + "」服務場景。先說明相關服務與需要的權限；尚未核驗自然人身分原胞、D8 授權與實際技能時，不執行讀取或修改。"
    }
    for s in services
]
(HERE / "OPEN_WEBUI_PROMPT_SUGGESTIONS_CANDIDATE.json").write_text(
    json.dumps({"candidate_only":True, "native_config_key":"ui.prompt_suggestions","suggestions":suggestions},ensure_ascii=False,indent=2)+"\n",
    encoding="utf-8",
)
# Preserve cross-compatibility without claiming Odoo routes already exist.
(HERE / "ODOO_MEMBER_ENTRY_LINKS_CANDIDATE.json").write_text(
    json.dumps({
      "candidate_only":True,
      "entry_responsibility":"existing Odoo member organ after original Total Field identity verification",
      "existing_oauth_routes":["/google/member/login","/line/login"],
      "shared_scene_service_home":"XIAOJ_PRODUCT_CANDIDATE_ENTRY_NOT_DEPLOYED",
      "same_member_packet_required":True,
      "links":[{"scene_key":s["key"],"target":"scene-pages/"+s["key"]+".html","launch_gate":"HOLD_TOTAL_FIELD"} for s in services],
    },ensure_ascii=False,indent=2)+"\n",
    encoding="utf-8",
)
diffs = "".join(difflib.unified_diff(
    old_index.splitlines(keepends=True),
    new_index.splitlines(keepends=True),
    fromfile="a/products/wuchang_xiaoj_community/index.html",
    tofile="b/products/wuchang_xiaoj_community/index.html",
    n=4,
))
(HERE / "EXISTING_PRODUCT_HOME_PATCH_CANDIDATE.diff").write_text(diffs, encoding="utf-8")
manifest = {
  "schema":"W7TP_XIAOJ_SEVEN_SCENE_UI_BUILD_CANDIDATE_V1",
  "time_utc":datetime.now(timezone.utc).isoformat(),
  "existing_product_source":"products/wuchang_xiaoj_community",
  "existing_product_index_sha256":hashlib.sha256(old_index.encode("utf-8")).hexdigest(),
  "isolated_product_index_sha256":hashlib.sha256(new_index.encode("utf-8")).hexdigest(),
  "scene_ids":[s["key"] for s in services],
  "same_shared_model_runtime":True,
  "same_identity_packet_required":True,
  "all_live_capability_grants_unverified":True,
  "each_scene_has_own_management_page":True,
  "production_file_changes":False,
  "identity_root_created":False,
  "live_deployment":False,
  "openwebui_runtime_config_changed":False,
  "odoo_db_changed":False,
  "frontend_executions_enabled":False,
  "source_candidate_only":True,
  "legacy_shell_metadata_is_not_v23_authority":True,
}
(HERE / "BUILD_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("BUILD_STATE=CANDIDATE_UI_GENERATED")
print("SCENES",len(services))
print("HOME_HTML",index_path)
print("SCENE_PAGES",len(list(pages_dir.glob("*.html"))))
print("CSS",pages_dir/"scene-prefix.css")
print("SOURCE_HOME_SHA256",manifest["existing_product_index_sha256"])
print("CANDIDATE_HOME_SHA256",manifest["isolated_product_index_sha256"])
print("LIVE_UNMODIFIED",hashlib.sha256((SOURCE/"index.html").read_bytes()).hexdigest()==manifest["existing_product_index_sha256"])
