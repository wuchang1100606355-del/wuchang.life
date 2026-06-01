#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate print-ready patent filing PDFs.

This script reads the local patent package generated in
patent_filing/readonly_boot_edge_runtime_m5_v0_1 and emits A4 PDFs.
It uses ReportLab CID fonts for Chinese text and does not require
system-wide package installation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
ROOT = Path("/home/taiji_admin/Taiji_Hub")
PKG = ROOT / "patent_filing" / "readonly_boot_edge_runtime_m5_v0_1"
OUT = PKG / "print_ready_pdf"
TITLE = "一種基於唯讀啟動媒體與五維度規封包之邊緣運算執行環境注入、瞬態 I/O 記憶體調度及可稽核狀態回滾方法"


try:
    pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
    BASE_FONT = "MSung-Light"
except Exception:
    BASE_FONT = "Helvetica"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


INVENTOR = {
    "name": env("TAIJI_PATENT_INVENTOR_NAME", "江政隆"),
    "id": env("TAIJI_PATENT_INVENTOR_ID", "F124771717"),
    "address": env("TAIJI_PATENT_INVENTOR_ADDRESS", "新北市三重區仁義街161號1樓"),
}

BUSINESS = {
    "name": env("TAIJI_PATENT_BUSINESS_NAME", "上品食品行（聊國咖啡館重新總店）"),
    "ubn": env("TAIJI_PATENT_BUSINESS_UBN", "34778660"),
    "address": env("TAIJI_PATENT_BUSINESS_ADDRESS", "新北市三重區重新路三段204號"),
    "representative": env("TAIJI_PATENT_BUSINESS_REPRESENTATIVE", INVENTOR["name"]),
}


def styles():
    s = getSampleStyleSheet()
    normal = ParagraphStyle(
        "TWNormal",
        parent=s["Normal"],
        fontName=BASE_FONT,
        fontSize=11.2,
        leading=18,
        alignment=TA_LEFT,
        wordWrap="CJK",
        spaceAfter=4,
    )
    title = ParagraphStyle(
        "TWTitle",
        parent=normal,
        fontSize=18,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    h1 = ParagraphStyle(
        "TWH1",
        parent=normal,
        fontSize=14,
        leading=22,
        spaceBefore=10,
        spaceAfter=7,
    )
    h2 = ParagraphStyle(
        "TWH2",
        parent=normal,
        fontSize=12.5,
        leading=20,
        spaceBefore=6,
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "TWSmall",
        parent=normal,
        fontSize=9.5,
        leading=14,
        wordWrap="CJK",
    )
    return normal, title, h1, h2, small


NORMAL, TITLE_STYLE, H1, H2, SMALL = styles()


def clean_md(text: str) -> str:
    text = re.sub(r"^# +", "", text, flags=re.M)
    text = re.sub(r"^## +", "", text, flags=re.M)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text.strip()


def read_file(name: str) -> str:
    return clean_md((PKG / name).read_text(encoding="utf-8"))


def paras_from_text(text: str):
    flow = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("【") and block.endswith("】"):
            flow.append(Paragraph(block, H1))
        elif re.match(r"^(一、|二、|三、|四、|五、|六、|七、|八、|九、|十、)", block):
            flow.append(Paragraph(block, H1))
        elif block.startswith("- "):
            for line in block.splitlines():
                flow.append(Paragraph("• " + line[2:].strip(), NORMAL))
        else:
            for line in block.splitlines():
                if line.strip():
                    flow.append(Paragraph(line.strip(), NORMAL))
        flow.append(Spacer(1, 2 * mm))
    return flow


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BASE_FONT, 8)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"第 {doc.page} 頁")
    canvas.restoreState()


def build_pdf(path: Path, title: str, flowables, pagesize=A4, footer_on=True):
    doc = SimpleDocTemplate(
        str(path),
        pagesize=pagesize,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
        title=title,
        author=INVENTOR["name"],
    )
    cb = footer if footer_on else None
    doc.build(flowables, onFirstPage=cb, onLaterPages=cb)


class FigureFlowable(Flowable):
    def __init__(self, fig_no: int):
        super().__init__()
        self.fig_no = fig_no
        self.width = landscape(A4)[0] - 3.0 * cm
        self.height = landscape(A4)[1] - 4.0 * cm

    def wrap(self, availWidth, availHeight):
        self.width = min(self.width, availWidth)
        self.height = min(self.height, availHeight)
        return self.width, self.height

    def draw_box(self, x, y, w, h, title, lines=()):
        c = self.canv
        c.roundRect(x, y, w, h, 6, stroke=1, fill=0)
        c.setFont(BASE_FONT, 10)
        c.drawCentredString(x + w / 2, y + h - 15, title)
        c.setFont(BASE_FONT, 8)
        yy = y + h - 32
        for line in lines:
            c.drawCentredString(x + w / 2, yy, line)
            yy -= 12

    def arrow(self, x1, y1, x2, y2):
        c = self.canv
        c.line(x1, y1, x2, y2)
        # simple arrow head
        if x2 >= x1:
            c.line(x2, y2, x2 - 6, y2 + 3)
            c.line(x2, y2, x2 - 6, y2 - 3)
        else:
            c.line(x2, y2, x2 + 6, y2 + 3)
            c.line(x2, y2, x2 + 6, y2 - 3)

    def draw(self):
        c = self.canv
        c.setFont(BASE_FONT, 16)
        c.drawCentredString(self.width / 2, self.height - 10, f"圖{self.fig_no}")
        if self.fig_no == 1:
            self.draw_box(10, 300, 95, 90, "110 輸入介面", ["待執行動作", "身份/權限資訊"])
            self.draw_box(145, 300, 110, 90, "120 封包產生", ["M5=&lt;N,D,A,W,R&gt;"])
            self.draw_box(300, 300, 130, 90, "140 AI 匝道判決", ["依 M5 與政策", "輸出 Vr"])
            self.draw_box(480, 300, 130, 90, "150 I/O 調度", ["控制排載", "讀寫/回滾"])
            self.draw_box(665, 330, 110, 65, "160 AI runtime", ["最小上下文"])
            self.draw_box(665, 230, 110, 65, "190 邊緣節點", ["本地/外接儲存"])
            self.draw_box(300, 130, 130, 65, "170 稽核記錄", ["M5/Vr/hash"])
            self.draw_box(480, 130, 130, 65, "180 回復模組", ["清除/回復/隔離"])
            self.draw_box(300, 30, 130, 50, "130 政策基準", ["規則/版本/條件"])
            self.arrow(105, 345, 145, 345)
            self.arrow(255, 345, 300, 345)
            self.arrow(430, 345, 480, 345)
            self.arrow(610, 360, 665, 360)
            self.arrow(610, 330, 665, 260)
            self.arrow(365, 300, 365, 195)
            self.arrow(545, 300, 545, 195)
            self.arrow(365, 80, 365, 130)
            c.setFont(BASE_FONT, 12)
            c.drawCentredString(self.width / 2, 410, "系統架構方塊圖")
        elif self.fig_no == 2:
            c.setFont(BASE_FONT, 15)
            c.roundRect(260, 350, 260, 45, 6, stroke=1, fill=0)
            c.drawCentredString(390, 367, "M5 = &lt; N, D, A, W, R &gt;")
            labels = [
                ("N", "節點或身份", ["裝置", "使用者", "服務帳戶", "容器"]),
                ("D", "資料敏感性", ["公開", "內部", "敏感", "機密"]),
                ("A", "動作意圖", ["讀取", "寫入", "推論", "回滾"]),
                ("W", "權限時間窗口", ["起訖時間", "授權場域", "有效期限"]),
                ("R", "可逆性/公共價值", ["可逆/不可逆", "回復成本", "人類確認"]),
            ]
            x = 25
            for code, title, lines in labels:
                self.draw_box(x, 120, 130, 180, f"{code} {title}", lines)
                self.arrow(390, 350, x + 65, 300)
                x += 150
            c.setFont(BASE_FONT, 12)
            c.drawCentredString(self.width / 2, 410, "五維度規向量封包資料結構示意圖")
        else:
            titles = {
                3: ("AI 匝道判決流程圖", ["接收待執行動作", "產生 M5", "讀取政策基準", "計算治理判決 Vr", "輸出 allow/audit/warn/block"]),
                4: ("邊緣 I/O 記憶體調度流程圖", ["接收 Vr", "判斷排載記憶體區段", "判斷讀取上下文片段", "判斷重組上下文", "建立稽核紀錄", "必要時觸發回復"]),
                5: ("稽核紀錄與回滾流程示意圖", ["讀取稽核紀錄", "確認回滾條件", "撤銷記憶體掛載", "刪除暫存上下文", "封存輸出結果", "恢復至先前狀態", "更新稽核紀錄"]),
            }
            title, steps = titles[self.fig_no]
            c.setFont(BASE_FONT, 12)
            c.drawCentredString(self.width / 2, 410, title)
            y = 350
            for i, step in enumerate(steps, 1):
                self.draw_box(250, y, 290, 35, f"S{self.fig_no}{i:02d} {step}", [])
                if i < len(steps):
                    self.arrow(395, y, 395, y - 25)
                y -= 55


def application_flow(kind: str):
    applicant = INVENTOR["name"] if kind == "individual" else BUSINESS["name"]
    ident = INVENTOR["id"] if kind == "individual" else BUSINESS["ubn"]
    address = INVENTOR["address"] if kind == "individual" else BUSINESS["address"]
    rows = [
        ["申請種類", "發明專利"],
        ["發明名稱", TITLE],
        ["申請人", applicant],
        ["識別資料", ident],
        ["地址", address],
        ["發明人", INVENTOR["name"]],
        ["發明人識別資料", INVENTOR["id"]],
        ["發明人地址", INVENTOR["address"]],
        ["指定代表圖", "圖1"],
    ]
    flow = [Paragraph("發明專利申請書草稿", TITLE_STYLE), Spacer(1, 6 * mm)]
    table = Table([[Paragraph(a, NORMAL), Paragraph(b, NORMAL)] for a, b in rows], colWidths=[4.2 * cm, 11.6 * cm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    flow.append(table)
    flow.append(Spacer(1, 8 * mm))
    flow.append(Paragraph("備註：實際申請書欄位請依智慧財產局電子申請系統轉填。本頁供列印核對與專利師審查。", SMALL))
    return flow


def abstract_flow():
    return [Paragraph("摘要", TITLE_STYLE)] + paras_from_text(read_file("02_摘要.md"))


def specification_flow():
    return [Paragraph("說明書", TITLE_STYLE)] + paras_from_text(read_file("03_說明書.md"))


def claims_flow():
    return [Paragraph("申請專利範圍", TITLE_STYLE)] + paras_from_text(read_file("04_申請專利範圍.md"))


def figure_description_flow():
    return [Paragraph("圖式簡單說明", TITLE_STYLE)] + paras_from_text(read_file("05_圖式簡單說明.md"))


def symbol_flow():
    data = [["符號", "說明"]]
    for line in read_file("06_符號說明.md").splitlines():
        line = line.strip()
        if line.startswith("- ") and "：" in line:
            a, b = line[2:].split("：", 1)
            data.append([a.strip(), b.strip()])
    table = Table([[Paragraph(a, NORMAL), Paragraph(b, NORMAL)] for a, b in data], colWidths=[4 * cm, 11.8 * cm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [Paragraph("符號說明", TITLE_STYLE), table]


def figures_flow():
    flow = [Paragraph("圖式", TITLE_STYLE), Paragraph("以下圖式為黑白線稿版，供列印與送件前審查。", SMALL), PageBreak()]
    for n in range(1, 6):
        flow.append(FigureFlowable(n))
        if n != 5:
            flow.append(PageBreak())
    return flow


def combined_flow(kind: str):
    flow = application_flow(kind)
    for part in [abstract_flow, specification_flow, claims_flow, figure_description_flow, symbol_flow, figures_flow]:
        flow.append(PageBreak())
        flow.extend(part())
    return flow


def write_manifest():
    files = []
    for p in sorted(OUT.glob("*.pdf")):
        files.append({"path": str(p.relative_to(PKG)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size})
    (OUT / "PDF_MANIFEST.json").write_text(json.dumps({"generated_at": NOW.isoformat(), "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    build_pdf(OUT / "10A_可列印送件合併本_自然人申請.pdf", "可列印送件合併本_自然人", combined_flow("individual"))
    build_pdf(OUT / "10B_可列印送件合併本_商號申請.pdf", "可列印送件合併本_商號", combined_flow("business"))
    build_pdf(OUT / "11_摘要.pdf", "摘要", abstract_flow())
    build_pdf(OUT / "12_說明書.pdf", "說明書", specification_flow())
    build_pdf(OUT / "13_申請專利範圍.pdf", "申請專利範圍", claims_flow())
    build_pdf(OUT / "14_圖式.pdf", "圖式", figures_flow(), pagesize=landscape(A4), footer_on=True)
    build_pdf(OUT / "15_圖式簡單說明.pdf", "圖式簡單說明", figure_description_flow())
    build_pdf(OUT / "16_符號說明.pdf", "符號說明", symbol_flow())
    write_manifest()
    print(OUT)


if __name__ == "__main__":
    main()
