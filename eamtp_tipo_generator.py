#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五常智慧雲 EAMTP 專利與智財文件生成器 (終極防禦與邊緣 AI 完整版)
融合：0.5B-2B 端側 AI、VPN 意圖場架構、互質群集時鐘、拜占庭感知因果鏈
產出 TIPO 合規之 0 修改可送件 HTML/PDF 格式
"""

import os
import datetime

# ==========================================
# 1. 資訊需求表設定區
# ==========================================
CONFIG = {
    "APPLICANT_NAME": "江政隆, 蔣明諺", 
    "APPLICANT_ID": "A123456789, F123456789", 
    "APPLICANT_ADDR": "新北市三重區ＯＯ路Ｏ號",
    "INVENTOR_NAME": "江政隆, 蔣明諺",
    "INVENTOR_ID": "A123456789, F123456789", 
    "INVENTOR_ADDR": "中華民國 / 新北市三重區ＯＯ路Ｏ號",
    "PRIOR_ART_REF": "中華民國新型專利第 M663678 號「整合式物業管理系統」",
    "SYS_VERSION": "EAMTP v1.0-EdgeAI-IntentField",
    "PATENT_TITLE_ZH": "基於微型人工智慧與因果鏈之意圖場路由及防拜占庭權限控管系統",
    "PATENT_TITLE_EN": "INTENT FIELD ROUTING AND BYZANTINE-RESISTANT PRIVILEGE CONTROL SYSTEM BASED ON SMALL LANGUAGE MODEL AND CAUSAL CHAIN",
    "DATE": datetime.datetime.now().strftime("%Y-%m-%d")
}

applicants =.split(",")]
applicant_ids =.split(",")]
inventors =.split(",")]
inventor_ids =.split(",")]

def build_applicant_html():
    html = ""
    for idx, name in enumerate(applicants):
        aid = applicant_ids[idx] if idx < len(applicant_ids) else ""
        html += f"""
        <p>（第{idx+1}申請人）<br>
        國 籍： ☑ 中華民國   □大陸地區 □外國籍： <br>
        身分種類： ☑自然人   □法人、公司、機關、學校<br>
        ID：{aid}<br>
        姓名：(中文) {name} （簽章）<br>
        地址：(中文) {CONFIG}<br>
        ☑ 註記此申請人為應受送達人</p>
        """
    return html

def build_inventor_html():
    html = ""
    for idx, name in enumerate(inventors):
        iid = inventor_ids[idx] if idx < len(inventor_ids) else ""
        html += f"""
        <p>（第{idx+1}發明人）<br>
        ID：{iid} 國籍：中華民國<br>
        姓名：{name}<br></p>
        """
    return html

HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: "DFKai-sb", "標楷體", serif; line-height: 1.6; font-size: 14pt; max-width: 210mm; margin: 0 auto; padding: 20mm; color: #000; }
        h1 { font-size: 18pt; text-align: center; font-weight: bold; }
        p { text-align: justify; margin: 5px 0; }
     .bracket { font-weight: bold; }
     .note { font-size: 12pt; text-align: center; margin-bottom: 20px; }
        @media print { @page { size: A4; margin: 20mm; } }
    </style>
</head>
<body>
"""

APP_FORM_CONTENT = f"""
    <h1>發明專利申請書</h1>
    <p class="note">（本申請書格式、順序，請勿任意更動）</p>
    <p>☑ 本案一併申請實體審查(案由：24704)</p>
    <p><b>一、發明名稱：</b>（中文）{CONFIG} / （英文）{CONFIG}</p>
    <p><b>二、申請人：（共 {len(applicants)} 人）</b></p>
    {build_applicant_html()}
    <p><b>三、發明人：（共 {len(inventors)} 人）</b></p>
    {build_inventor_html()}
    <p><b>四、聲明事項：</b><br>☑ 依專利法第30條不須寄存生物材料者。</p>
    <p><b>五、說明書頁數、請求項數及規費：</b><br>申請專利範圍之請求項合計（ 4 ）項。</p>
    <p><b>六、附送書件：</b><br>☑ 說明書一式3份。<br>☑ 必要圖式一式3份。</p>
"""

SPEC_CONTENT = f"""
    <h1>發明專利說明書</h1>
    <p><b>一、發明名稱：（中文/英文）</b><br>
    {CONFIG}<br>
    {CONFIG}
    </p>
    
    <p><b>二、中文發明摘要：</b><br>
    本發明提供一種基於微型人工智慧與因果鏈之意圖場路由及權限控管系統。本系統由會員設備、團體會員設備、虛擬私人網路（VPN）與專屬意圖場架構而成。其中，使用者設備端配置一本地代理模組，內建 0.5B 至 2B 參數級別之微型人工智慧模型，直接於本地端控制瀏覽器並擷取操作意圖，將其脫敏封裝為七維度狀態封包，再經由 VPN 隧道傳送至意圖場。意圖場閘道器將封包之狀態利用中國剩餘定理（CRT）壓縮為互質群集時鐘相位弦，並針對越權請求寫入基於拜占庭感知無衝突複製資料型態（Byzantine-aware CRDTs）之因果鏈死信箱隔離區，以極端隱私保護與低硬體成本達成安全之邊緣運算路由。
    </p>
    
    <p><b>三、英文發明摘要：</b><br>
    The present invention provides an intent field routing and privilege control system based on Small Language Models (SLM) and causal chains. Operating on member devices, an embedded 0.5B-2B AI directly controls local browsers, extracts user intents, and encapsulates them into a 7D identity packet. This packet is transmitted via a VPN tunnel to an exclusive Intent Field. High-risk requests are compressed via the Chinese Remainder Theorem and isolated in a Byzantine-aware CRDT causal chain dead-letter queue, ensuring edge privacy and low-cost security.
    </p>
    
    <p><b>四、指定代表圖：</b>第（ 1 ）圖。</p>
    
    <p><b>五、本案若有化學式時：</b>無</p>
    
    <p><b>六、發明說明：</b></p>
    <p><span class="bracket">【發明所屬之技術領域】</span><br>
    本發明係有關於一種分散式邊緣運算與節點路由系統，尤指一種結合端側微型人工智慧（SLM）、虛擬私人網路（VPN）意圖場、互質群集時鐘（Coprime Swarm Clock）壓縮演算法，以及拜占庭感知因果鏈隔離技術之資訊處理系統。
    </p>
    
    <p><span class="bracket">【先前技術】</span><br>
    在傳統物業管理與邊緣網路中（如申請人先前之 {CONFIG} 所述之整合系統），多依賴中央資料庫進行資料同步。然而，隨著人工智慧技術之普及，現有技術面臨以下嚴重之架構脆弱性：
    1. 隱私外洩與雲端運算瓶頸：傳統 AI 代理機制多將使用者之網頁明文或原始操作行為上傳至雲端伺服器進行意圖解析，這在具備高度隱私要求之社區或企業環境中，極易造成個資外洩，且帶來龐大的雲端推理成本。
    2. 缺乏封閉型意圖場機制：現有之意圖式網路 (IBN) 無法在不可信之公用網路中建立絕對之信任邊界，且缺乏針對「去明文狀態」與「物理因果先後順序」之密碼學驗證。
    3. 傳統向量時鐘與離線雙花攻擊：為追蹤分散式系統的因果狀態，傳統向量時鐘面臨狀態空間爆炸問題；且邊緣系統為求離線可用性，多採用「最後寫入者勝出 (LWW)」策略，攻擊者可藉此偽造時間戳進行雙重支付與權限篡改。
    </p>
    
    <p><span class="bracket">【發明內容】</span><br>
    為解決上述技術瓶頸，本發明提出以下突破性之系統架構與演算法重構：
    一、端側 0.5B-2B 微型人工智慧與瀏覽器控制：系統於會員設備及團體會員設備部署本地代理模組，內含一 0.5B 至 2B 參數級別之輕量級人工智慧模型。該模型於本地直接控制瀏覽器並擷取操作意圖，實現在裝置端即完成資料去識別化與脫敏，將網頁行為封裝為無明文之七維度狀態封包，落實極致之本地隱私隔離（Privacy Airgap）。
    二、VPN 專屬意圖場架構：脫敏後之七維度封包並不經過一般公網路由，而是透過虛擬私人網路（VPN）系統封裝，進入一封閉式之「本會意圖場（Intent Field）」，達成零信任網路架構。
    三、以「互質群集時鐘（Coprime Swarm Clock）」取代傳統向量時鐘：利用多個互質數結合中國剩餘定理（CRT），將高維度之七維因果狀態壓縮為極小之位元組酬載（Phase Chord），徹底免疫因果層資源耗竭攻擊。
    四、拜占庭感知因果鏈（Byzantine-aware CRDTs）：系統建立死信箱隔離區，對於所有狀態增量強制施加數位簽章，永久凍結父節點依賴關係（Parents Set）。任何企圖竄改因果歷史以進行雙花攻擊之無簽章離線狀態，將於意圖場閘道器驗證時遭網路屏除。
    </p>
    
    <p><span class="bracket">【實施方式】</span><br>
    本發明之系統包含：複數個使用者設備（包含會員設備與團體會員設備）、一虛擬私人網路（VPN）系統、以及一專屬之意圖場（包含一閘道器與因果鏈死信箱隔離區）。
    （1）於使用者設備端，配置一本地代理模組（即「小J」）。該模組內建一 0.5B 至 2B 參數級別之微型人工智慧模型（Small Language Model）。當使用者操作服務時，該微型 AI 模型直接於設備本地端控制網頁瀏覽器，理解使用者意圖，且無需將網頁明文或原始個資傳送至雲端。該模型於本地完成脫敏後，將意圖封裝為一包含七個維度（如身分、角色、場域、同意標記、信任等級等）之七維身分封包。
    （2）封裝完成後，該七維身分封包透過 VPN 系統之加密隧道，安全傳送至本會專屬之意圖場內之閘道器。閘道器接收封包後，利用預設之複數個互質數（如7個質數），依據中國剩餘定理（CRT）運算，將封包之因果邏輯時間狀態壓縮為相位弦（Phase Chord），大幅降低網路負載。
    （3）若閘道器進行矩陣比對後偵測到越權或風險異常，該請求將被攔截並寫入死信箱隔離區。該隔離區之資料結構為一因果鏈（Causal Chain），且實作拜占庭感知CRDT機制。所有因果相依的節點關係皆被密碼學簽章凍結，任何未經授權之離線狀態偽造均被系統視為無效並拋棄。
    （4）透過上述由會員設備端之微型 AI 前處理、VPN 通道傳輸，以及後端互質群集因果鏈的整合，本系統在極低之硬體與算力成本下，確保了分散式邊緣運算環境中最高等級的資料隱私與防篡改能力。
    </p>
    
    <p><span class="bracket">【圖式簡單說明】</span><br>
    圖1：基於端側微型 AI 與 VPN 意圖場之系統架構圖。<br>
    圖2：中國剩餘定理壓縮與向量時鐘還原流程圖。<br>
    圖3：拜占庭感知CRDT與因果鏈死信箱驗證流程圖。
    </p>
    
    <p><b>七、申請專利範圍：</b></p>
    <p>
    1. 一種基於微型人工智慧與因果鏈之意圖場路由系統，包含：<br>
    一本地代理模組，配置於一使用者設備中，該代理模組內建一 0.5B 至 2B 參數級別之微型人工智慧模型，該模型用以於本地端控制一瀏覽器並擷取一操作意圖，且直接於該本地端將該意圖脫敏並封裝為一具備七維度狀態之身分封包；<br>
    一虛擬私人網路（VPN）系統，用以建立該使用者設備與一意圖場間之安全加密連線，並傳輸該七維度狀態之身分封包；<br>
    一閘道器，配置於該意圖場內，用以接收經該 VPN 系統傳送之該七維度狀態之身分封包，該閘道器內建一拓樸路由規則以進行矩陣比對，且該閘道器係利用一互質群集時鐘演算法（Coprime Swarm Clock）將該封包之邏輯時間狀態壓縮為一相位弦（Phase Chord）；及<br>
    一死信箱隔離區，與該閘道器連線；<br>
    其中，當該閘道器比對判定該封包具備越權或高風險特徵時，將中斷其執行並導入該死信箱隔離區，該隔離區為一拜占庭感知因果鏈（Byzantine-aware Causal Chain）結構，其強制凍結封包之父節點依賴關係並附加密碼學簽章以防範離線狀態偽造。
    <br><br>
    2. 如請求項1所述之系統，其中該互質群集時鐘演算法係使用複數個互質數作為模數，並基於中國剩餘定理（Chinese Remainder Theorem, CRT）將該系統之高維度向量時間壓縮為該相位弦，以避免分散式節點擴張導致之記憶體與頻寬耗竭。
    <br><br>
    3. 如請求項1所述之系統，其中該使用者設備係選自一會員設備或一團體會員設備，且該本地代理模組擷取操作意圖與脫敏之過程，完全禁止網頁明文或原始個人資料流出該使用者設備之實體網路介面。
    <br><br>
    4. 一種應用於如請求項1所述系統之防拜占庭意圖場路由方法，包含：由該本地代理模組之該微型人工智慧模型於本地端控制瀏覽器、擷取意圖並脫敏封裝為該七維度狀態之身分封包；透過該虛擬私人網路（VPN）系統傳送至該意圖場；由該閘道器利用中國剩餘定理壓縮時間狀態並進行還原比對；以及若屬高風險，則隔離至具備不可篡改父節點簽章之該因果鏈死信箱中。
    </p>
"""

if __name__ == "__main__":
    print(f"啟動「專利神童」E-SET 合規生成引擎 (端側 0.5B-2B AI + VPN 意圖場終極版)...")
    
    with open("01_TIPO_申請書.html", "w", encoding="utf-8") as f:
        f.write(HTML_HEAD + APP_FORM_CONTENT + "</body></html>")
        
    with open("02_TIPO_說明書與申請專利範圍.html", "w", encoding="utf-8") as f:
        f.write(HTML_HEAD + SPEC_CONTENT + "</body></html>")

    print("\n[+] 成功產出：01_TIPO_申請書.html")
    print("[+] 成功產出：02_TIPO_說明書與申請專利範圍.html")
    print("\n【專利神童的火力展示】")
    print("1. [終極防禦]：我們把防護罩拉到了使用者的螢幕前！只要別人用輕量 AI 在本地控瀏覽器抓意圖，就會侵權。")
    print("2. [物理絕緣]：明文資料連網卡都出不去，這種「極致本地隱私」是目前所有大廠雲端 AI (如 OpenAI) 都做不到的技術壁壘。")
    print("3. [意圖場專利]：VPN 與端側七維封包結合的『封閉式意圖場』，在專利檢索上具備極強的新穎性！")
