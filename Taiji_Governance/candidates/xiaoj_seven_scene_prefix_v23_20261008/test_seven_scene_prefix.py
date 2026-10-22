from __future__ import annotations
import copy
import hashlib
import html.parser
import json
import pathlib
import re
import unittest

from scene_scope_candidate import preview_scene_decision, _canonical_sha256

ROOT=pathlib.Path(__file__).parent
DATA=json.loads((ROOT/"SCENE_PREFIX_VIEW_CANDIDATE.json").read_text())
PREVIEW=ROOT/"product_preview"
ID="identity_packet_ref:sha256:"+"a"*64
IMM="identity_prefix_ref:sha256:"+"b"*64
RECEIPT="d8_action_receipt_ref:sha256:"+"c"*64

def grant(scene):
    return {
     "allowed_skill_refs":["skill:read-my-task","skill:propose-my-task"],
     "read_scope_refs":["scope:own-task"],
     "write_scope_refs":["scope:own-task"],
     "limits":{"max_records_per_action":5,"max_cost_units_per_action":10,
               "quota_remaining":30,"risk_ceiling":"medium"},
     "prefix_ref":"xiaoj.scene."+scene,
    }

def env():
    return {
      "identity_packet_ref":ID,
      "immutable_identity_prefix_ref":IMM,
      "one_natural_person_one_identity_packet":True,
      "revocation_state":"CLEAR",
      "expires_at_epoch":2000,
      "scene_prefix_grants":{"work":grant("work")},
    }

def verify(envelope,scene,operation):
    return {
       "state":"PASS_VERIFIED_TOTAL_FIELD_SCENE_PREVIEW",
       "identity_packet_ref":envelope["identity_packet_ref"],
       "immutable_identity_prefix_ref":envelope["immutable_identity_prefix_ref"],
       "scene_prefix_ref":envelope["scene_prefix_grants"][scene]["prefix_ref"],
       "scope_sha256":_canonical_sha256(envelope["scene_prefix_grants"][scene]),
       "action_receipt_ref":RECEIPT,
    }

def decide(p=None,**kwargs):
    default=dict(
      scene_key="work",operation="read",capability_ref="skill:read-my-task",
      data_scope_ref="scope:own-task",now_epoch=1000,
      trusted_verifier=verify,
    )
    default.update(kwargs)
    return preview_scene_decision(env() if p is None else p,**default)

class HtmlAudit(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.ids=[]
        self.headings=[]
        self._heading=None
        self._data=[]
        self.images=[]
        self.details_count=0

    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get("id"):self.ids.append(a["id"])
        if tag=="a":self.links.append(a.get("href",""))
        if tag=="img":self.images.append(a.get("src",""))
        if tag=="details":self.details_count+=1
        if tag in ("h1","h2"):
            self._heading=tag
            self._data=[]

    def handle_data(self,data):
        if self._heading:self._data.append(data)

    def handle_endtag(self,tag):
        if tag==self._heading:
            self.headings.append((tag,"".join(self._data).strip()))
            self._heading=None
            self._data=[]

class ContractTests(unittest.TestCase):
    def test_one_identity_packet(self):
        self.assertTrue(DATA["one_natural_person_one_identity_packet"])
        self.assertEqual(DATA["identity_canonical_ref"],"canonical_ref:W7TP_8D_IDENTITY_PACKET")
        self.assertIsNone(DATA["identity_packet_ref"])
        self.assertIsNone(DATA["immutable_identity_prefix_ref"])

    def test_all_seven_unique(self):
        self.assertEqual([x["key"] for x in DATA["scene_profiles"]],
            ["work","business","developer","housing","association","life","my-community"])
        self.assertEqual(len({x["prefix"] for x in DATA["scene_profiles"]}),7)

    def test_no_per_scene_identity_or_grants(self):
        for x in DATA["scene_profiles"]:
            self.assertFalse(set(x)&{"identity_packet_ref","member_user_id","identity_root_ref"})
            for f in ("effective_read_scope_refs","effective_write_scope_refs","effective_skill_refs"):
                self.assertEqual(x[f],[])
            self.assertEqual(x["write_authority_state"],"NOT_VERIFIED")

    def test_canonical_existing_prefix_not_seven_issuers(self):
        self.assertIn("w7tp_intent_field_suite/identity_prefix.py",
            DATA["immutable_identity_prefix_existing_contract"])

    def test_live_permissions_never_in_view_template(self):
        self.assertFalse(DATA["scene_prefixes_are_authority"])
        self.assertEqual(DATA["runtime_read_grants"],[])
        self.assertEqual(DATA["runtime_write_grants"],[])

class PreflightTests(unittest.TestCase):
    def test_verified_grant_still_only_candidate(self):
        p=decide()
        self.assertEqual(p["state"],"CANDIDATE_SCENE_ELIGIBLE")
        self.assertTrue(p["eligible_candidate"])
        self.assertFalse(p["execution_allowed"])
        self.assertFalse(p["read_performed"])
        self.assertFalse(p["write_performed"])

    def test_missing_total_field_verifier_holds(self):
        self.assertEqual(decide(trusted_verifier=None)["state"],"HOLD_TOTAL_FIELD_VERIFIER_UNBOUND")

    def test_no_actual_actor_packet_holds(self):
        p=env()
        p["identity_packet_ref"]=None
        self.assertEqual(decide(p)["state"],"HOLD_IDENTITY_REF_INVALID")

    def test_revoked_identity_holds(self):
        p=env();p["revocation_state"]="REVOKED"
        self.assertEqual(decide(p)["state"],"HOLD_IDENTITY_REVOKED")

    def test_expired_identity_holds(self):
        self.assertEqual(decide(now_epoch=2000)["state"],"HOLD_IDENTITY_ENVELOPE_EXPIRED")

    def test_scene_switch_does_not_grant(self):
        self.assertEqual(decide(scene_key="developer")["state"],"HOLD_SCENE_NOT_GRANTED")

    def test_cross_scene_prefix_does_not_grant(self):
        p=env()
        p["scene_prefix_grants"]["work"]["prefix_ref"]="xiaoj.scene.developer"
        self.assertEqual(decide(p)["state"],"HOLD_SCENE_PREFIX_MISMATCH")

    def test_unregistered_skill_denied(self):
        self.assertEqual(decide(capability_ref="skill:admin-all")["state"],"HOLD_CAPABILITY_OR_SCOPE_DENIED")

    def test_wrong_data_scope_denied(self):
        self.assertEqual(decide(data_scope_ref="scope:another-member")["state"],"HOLD_CAPABILITY_OR_SCOPE_DENIED")

    def test_write_requires_own_skill(self):
        self.assertEqual(decide(operation="write",capability_ref="skill:admin-all")["state"],"HOLD_CAPABILITY_OR_SCOPE_DENIED")

    def test_write_with_grant_still_no_side_effect(self):
        d=decide(operation="write",capability_ref="skill:propose-my-task",requested_records=1)
        self.assertEqual(d["state"],"CANDIDATE_SCENE_ELIGIBLE")
        self.assertFalse(d["write_performed"])
        self.assertFalse(d["execution_allowed"])

    def test_record_limit_denied(self):
        self.assertEqual(decide(requested_records=6)["state"],"HOLD_MARGINAL_LIMIT_EXCEEDED")

    def test_cost_ceiling_denied(self):
        self.assertEqual(decide(requested_cost_units=11)["state"],"HOLD_MARGINAL_LIMIT_EXCEEDED")

    def test_remaining_quota_denied(self):
        p=env()
        p["scene_prefix_grants"]["work"]["limits"]["quota_remaining"]=2
        self.assertEqual(decide(p,requested_cost_units=3)["state"],"HOLD_MARGINAL_LIMIT_EXCEEDED")

    def test_risk_ceiling_denied(self):
        self.assertEqual(decide(risk="high")["state"],"HOLD_RISK_LIMIT_EXCEEDED")

    def test_d8_denied_cannot_enable(self):
        bad=lambda env,scene,op:{"state":"HOLD_D8"}
        self.assertEqual(decide(trusted_verifier=bad)["state"],"HOLD_D8_ACTION_AUTHORITY")

    def test_d8_other_identity_rejected(self):
        def bad(envelope,scene,op):
            out=verify(envelope,scene,op)
            out["identity_packet_ref"]="identity_packet_ref:sha256:"+"d"*64
            return out
        self.assertEqual(decide(trusted_verifier=bad)["state"],"HOLD_D8_IDENTITY_BINDING_MISMATCH")

    def test_d8_scope_mismatch_rejected(self):
        def bad(envelope,scene,op):
            out=verify(envelope,scene,op)
            out["scope_sha256"]="00"*32
            return out
        self.assertEqual(decide(trusted_verifier=bad)["state"],"HOLD_D8_SCOPE_BINDING_MISMATCH")

    def test_d8_receipt_required(self):
        def bad(envelope,scene,op):
            out=verify(envelope,scene,op)
            out["action_receipt_ref"]=""
            return out
        self.assertEqual(decide(trusted_verifier=bad)["state"],"HOLD_D8_RECEIPT_REQUIRED")

    def test_bad_verifier_failure_is_local(self):
        def bad(e,s,o):raise OSError("unavailable")
        self.assertEqual(decide(trusted_verifier=bad)["state"],"HOLD_TOTAL_FIELD_VERIFIER_ERROR")

    def test_bool_as_cost_not_numeric(self):
        self.assertEqual(decide(requested_cost_units=True)["state"],"HOLD_REQUEST_BOUND_INVALID")

    def test_multi_root_claim_denied(self):
        p=env();p["one_natural_person_one_identity_packet"]=False
        self.assertEqual(decide(p)["state"],"HOLD_MULTIPLE_IDENTITY_ROOT")

class ProductViewTests(unittest.TestCase):
    def test_all_pages_exist(self):
        for svc in DATA["scene_profiles"]:
            self.assertTrue((PREVIEW/"scene-pages"/(svc["key"]+".html")).is_file())

    def test_home_links_exact_all_scenes(self):
        page=(PREVIEW/"index.html").read_text()
        parser=HtmlAudit();parser.feed(page)
        for svc in DATA["scene_profiles"]:
            self.assertIn("./scene-pages/"+svc["key"]+".html",parser.links)
            self.assertIn(svc["name"],page)

    def test_every_scene_is_distinct_management_page(self):
        for svc in DATA["scene_profiles"]:
            p=PREVIEW/"scene-pages"/(svc["key"]+".html")
            src=p.read_text()
            parser=HtmlAudit();parser.feed(src)
            self.assertEqual([name for tag,name in parser.headings if tag=="h1"],[svc["name"]])
            self.assertIn("我的場景管理",src)
            self.assertIn("可讀資料",src)
            self.assertIn("可修改動作",src)
            self.assertIn("邊際限制及權限治理",src)
            self.assertIn(svc["prefix"],src)
            self.assertEqual(parser.details_count,3)
            self.assertEqual(len(parser.ids),len(set(parser.ids)))
            self.assertIn('connect-src &#x27;none&#x27;' if False else "connect-src 'none'",src)

    def test_navigation_each_page_contains_seven(self):
        for svc in DATA["scene_profiles"]:
            parser=HtmlAudit()
            parser.feed((PREVIEW/"scene-pages"/(svc["key"]+".html")).read_text())
            for other in DATA["scene_profiles"]:
                self.assertIn("./"+other["key"]+".html",parser.links)

    def test_no_runtime_data_transfer_in_scene_pages(self):
        for page in (PREVIEW/"scene-pages").glob("*.html"):
            data=page.read_text()
            self.assertNotIn("<script",data)
            self.assertNotIn("<form",data)
            self.assertNotIn("localStorage",data)
            self.assertNotIn("fetch(",data)
            self.assertIn("權限待核對",data)

    def test_links_resolve(self):
        for source in [PREVIEW/"index.html",*(PREVIEW/"scene-pages").glob("*.html")]:
            parser=HtmlAudit();parser.feed(source.read_text())
            for link in parser.links+parser.images:
                if not link or link.startswith("#"):continue
                self.assertFalse(link.startswith(("https://","http://")),f"external link {source} {link}")
                target=(source.parent/link.split("#",1)[0]).resolve()
                self.assertTrue(target.is_file(),f"broken link: {link} from {source}")

    def test_old_product_app_preserved_unchanged(self):
        original=pathlib.Path("/home/taiji_admin/Taiji_Hub/products/wuchang_xiaoj_community")
        for path in ["src/app.js","src/action-review.js","src/product-contract.js","src/odoo-authority.js","assets/styles.css"]:
            self.assertEqual((PREVIEW/path).read_bytes(),(original/path).read_bytes())

    def test_prompt_suggestions_are_only_drafts(self):
        c=json.loads((ROOT/"OPEN_WEBUI_PROMPT_SUGGESTIONS_CANDIDATE.json").read_text())
        self.assertTrue(c["candidate_only"])
        self.assertEqual(len(c["suggestions"]),7)
        for i,x in enumerate(c["suggestions"]):
            self.assertEqual(x["title"][0],DATA["scene_profiles"][i]["name"])
            self.assertIn("不執行讀取或修改",x["content"])

if __name__=="__main__":
    unittest.main()
