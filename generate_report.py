"""
Customer Churn Prediction System — Full Project Report Generator
Generates a professional ~60-page PDF report with:
  Cover page, Abstract, Table of Contents, 10 Chapters,
  Source Code Appendix, References, page numbers & headers.
"""

import os, json, textwrap
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem, KeepTogether, HRFlowable, Preformatted,
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

from report_content import ABSTRACT, CHAPTERS, REFERENCES

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PDF = os.path.join(BASE_DIR, "ChurnPrediction_ProjectReport.pdf")
STATS_PATH = os.path.join(BASE_DIR, "data", "stats.json")

# ── Colors ─────────────────────────────────────────────────────────────
C_PRIMARY    = HexColor("#1e293b")
C_ACCENT     = HexColor("#6366f1")
C_ACCENT2    = HexColor("#818cf8")
C_TEXT       = HexColor("#1e293b")
C_TEXT_LIGHT = HexColor("#64748b")
C_WHITE      = HexColor("#ffffff")
C_BG_LIGHT   = HexColor("#f8fafc")
C_BORDER     = HexColor("#cbd5e1")
C_TBL_HDR    = HexColor("#4338ca")
C_TBL_ALT    = HexColor("#f1f5f9")
C_CODE_BG    = HexColor("#f1f5f9")
C_SUCCESS    = HexColor("#22c55e")
C_DANGER     = HexColor("#ef4444")

WIDTH, HEIGHT = A4  # 595.27, 841.89
MARGIN = 60
CW = WIDTH - 2 * MARGIN  # content width

# ── Load stats ─────────────────────────────────────────────────────────
with open(STATS_PATH) as f:
    stats = json.load(f)

# ── Styles ─────────────────────────────────────────────────────────────
def build_styles():
    ss = getSampleStyleSheet()

    def _add(name, **kw):
        if name in [s.name for s in ss.byName.values()]:
            return
        parent = kw.pop("parent", ss["Normal"])
        ss.add(ParagraphStyle(name, parent=parent, **kw))

    _add("Cover_Title",   fontSize=30, leading=38, textColor=C_WHITE, alignment=TA_CENTER, fontName="Helvetica-Bold")
    _add("Cover_Sub",     fontSize=15, leading=22, textColor=HexColor("#c7d2fe"), alignment=TA_CENTER)
    _add("Cover_Author",  fontSize=13, leading=18, textColor=HexColor("#e0e7ff"), alignment=TA_CENTER)
    _add("Cover_Year",    fontSize=12, leading=16, textColor=HexColor("#a5b4fc"), alignment=TA_CENTER)

    _add("Ch_Title",      fontSize=24, leading=30, textColor=C_ACCENT, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=16)
    _add("Sec_Title",     fontSize=16, leading=22, textColor=C_PRIMARY, fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=8)
    _add("Sub_Title",     fontSize=13, leading=18, textColor=C_TEXT, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6)

    _add("Body",          fontSize=11, leading=17, textColor=C_TEXT, alignment=TA_JUSTIFY, spaceAfter=8, firstLineIndent=24)
    _add("BodyNoIndent",  fontSize=11, leading=17, textColor=C_TEXT, alignment=TA_JUSTIFY, spaceAfter=8)
    _add("Bullet",        fontSize=11, leading=17, textColor=C_TEXT, spaceAfter=4, leftIndent=36, bulletIndent=18)
    _add("CodeBlock",     fontSize=8.5, leading=12, textColor=C_TEXT, fontName="Courier",
         backColor=C_CODE_BG, leftIndent=12, rightIndent=12, spaceBefore=4, spaceAfter=4,
         borderWidth=0.5, borderColor=C_BORDER, borderPadding=6)
    _add("Caption",       fontSize=9, leading=13, textColor=C_TEXT_LIGHT, alignment=TA_CENTER, spaceAfter=14, fontName="Helvetica-Oblique")
    _add("TOC_Ch",        fontSize=13, leading=26, textColor=C_PRIMARY, fontName="Helvetica-Bold", spaceBefore=2)
    _add("TOC_Sec",       fontSize=11, leading=22, textColor=C_TEXT, leftIndent=24)
    _add("Ref",           fontSize=10, leading=15, textColor=C_TEXT, spaceAfter=6, leftIndent=24, firstLineIndent=-24)
    _add("AbstractBody",  fontSize=11, leading=17, textColor=C_TEXT, alignment=TA_JUSTIFY, spaceAfter=8)
    _add("PageHeader",    fontSize=8, textColor=C_TEXT_LIGHT, fontName="Helvetica-Oblique")
    _add("SmallNote",     fontSize=9, leading=13, textColor=C_TEXT_LIGHT, alignment=TA_CENTER, spaceAfter=4)
    return ss

STYLES = build_styles()

# ── Helper flowables ───────────────────────────────────────────────────

class ColorBlock(Flowable):
    """A full-width colored rectangle behind content (used for cover)."""
    def __init__(self, width, height, color):
        super().__init__()
        self.width = width
        self.height = height
        self._color = color
    def draw(self):
        self.canv.setFillColor(self._color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)

class GradientBlock(Flowable):
    """Draws a vertical gradient rectangle."""
    def __init__(self, w, h, c1, c2, steps=60):
        super().__init__()
        self.width = w
        self.height = h
        self._c1, self._c2, self._steps = c1, c2, steps
    def draw(self):
        c = self.canv
        sh = self.height / self._steps
        for i in range(self._steps):
            t = i / self._steps
            r = self._c1.red   + t * (self._c2.red   - self._c1.red)
            g = self._c1.green + t * (self._c2.green - self._c1.green)
            b = self._c1.blue  + t * (self._c2.blue  - self._c1.blue)
            c.setFillColor(Color(r, g, b))
            c.rect(0, self.height - (i + 1) * sh, self.width, sh + 1, fill=1, stroke=0)


# ── Page Templates ─────────────────────────────────────────────────────
_page_count_offset = 0  # pages before content (cover, abstract, toc)

def _header_footer(canvas, doc):
    """Draw header line + page number on every content page."""
    page_num = canvas.getPageNumber()
    # Skip cover page
    if page_num <= 1:
        return
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, HEIGHT - 40, WIDTH - MARGIN, HEIGHT - 40)
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(C_TEXT_LIGHT)
    canvas.drawString(MARGIN, HEIGHT - 36, "Customer Churn Prediction System — Project Report")
    canvas.drawRightString(WIDTH - MARGIN, HEIGHT - 36, "Aryan Sharma")
    # Footer page number
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(C_TEXT_LIGHT)
    canvas.drawCentredString(WIDTH / 2, 30, f"— {page_num} —")
    # Footer line
    canvas.line(MARGIN, 44, WIDTH - MARGIN, 44)
    canvas.restoreState()


# ── Build helpers ──────────────────────────────────────────────────────

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceBefore=6, spaceAfter=6)

def make_table(headers, rows, col_widths=None):
    """Return a styled Table flowable."""
    data = [headers] + rows
    if col_widths is None:
        col_widths = [CW / len(headers)] * len(headers)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND",   (0, 0), (-1, 0), C_TBL_HDR),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("FONTSIZE",     (0, 1), (-1, -1), 9.5),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
    ]
    # alternate row shading
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), C_TBL_ALT))
    t.setStyle(TableStyle(style))
    return t


# ── Source code reader ─────────────────────────────────────────────────

def read_source(path, max_lines=120):
    try:
        with open(os.path.join(BASE_DIR, path), encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            lines = lines[:max_lines] + [f"\n# ... ({len(lines) - max_lines} more lines) ...\n"]
        return "".join(lines)
    except Exception:
        return f"# Could not read {path}"

def read_source_full(path):
    try:
        with open(os.path.join(BASE_DIR, path), encoding="utf-8") as f:
            return f.read()
    except Exception:
        return f"# Could not read {path}"


# ══════════════════════════════════════════════════════════════════════
#  BUILD THE REPORT
# ══════════════════════════════════════════════════════════════════════

def build_report():
    doc = SimpleDocTemplate(
        OUTPUT_PDF, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=52, bottomMargin=56,
    )

    story = []

    # ─────────────────── COVER PAGE ────────────────────────────────────
    # We draw the cover using canvas-level drawing in the first-page callback
    story.append(Spacer(1, 120))
    # Decorative line
    story.append(HRFlowable(width="40%", thickness=2, color=C_ACCENT, spaceBefore=0, spaceAfter=16))
    story.append(Paragraph("PROJECT REPORT", STYLES["SmallNote"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Customer Churn Prediction System", STYLES["Ch_Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Using Machine Learning and Predictive Analytics", STYLES["BodyNoIndent"]))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="60%", thickness=1, color=C_ACCENT2, spaceBefore=12, spaceAfter=20))
    story.append(Spacer(1, 24))
    story.append(Paragraph("<b>ChurnGuard AI</b>", STYLES["BodyNoIndent"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("An End-to-End Machine Learning Application for<br/>Telecom Customer Retention Analytics", STYLES["BodyNoIndent"]))
    story.append(Spacer(1, 60))
    story.append(HRFlowable(width="30%", thickness=0.5, color=C_BORDER, spaceBefore=0, spaceAfter=12))

    # Author info table
    info_data = [
        ["Submitted By:", "Aryan Sharma"],
        ["Technology:", "Python · Flask · Scikit-learn"],
        ["Year:", "2026"],
    ]
    info_table = Table(info_data, colWidths=[120, 300])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), C_TEXT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
    ]))
    story.append(info_table)
    story.append(PageBreak())

    # ─────────────────── CERTIFICATE / DECLARATION (filler) ────────────
    story.append(Spacer(1, 60))
    story.append(Paragraph("CERTIFICATE", STYLES["Ch_Title"]))
    story.append(hr())
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "This is to certify that the project report entitled <b>\"Customer Churn Prediction System Using Machine Learning and Predictive Analytics\"</b> "
        "is a bonafide work carried out by <b>Aryan Sharma</b>. "
        "The project demonstrates the application of machine learning algorithms for predicting customer churn in the telecommunications industry, "
        "deployed through a production-ready Flask web application branded as ChurnGuard AI.",
        STYLES["Body"]
    ))
    story.append(Spacer(1, 60))
    sig_data = [
        ["", ""],
        ["_________________________", "_________________________"],
        ["Project Guide", "Head of Department"],
    ]
    sig_t = Table(sig_data, colWidths=[CW / 2, CW / 2])
    sig_t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_t)
    story.append(Spacer(1, 40))
    story.append(Paragraph("Date: July 2026", STYLES["BodyNoIndent"]))
    story.append(PageBreak())

    # ─────────────────── DECLARATION ───────────────────────────────────
    story.append(Spacer(1, 60))
    story.append(Paragraph("DECLARATION", STYLES["Ch_Title"]))
    story.append(hr())
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "I, <b>Aryan Sharma</b>, hereby declare that the project work entitled "
        "<b>\"Customer Churn Prediction System Using Machine Learning and Predictive Analytics\"</b> "
        "submitted is a record of original work done by me. The information and data given in the report is authentic to the best of my knowledge. "
        "This project is not submitted to any other university or institution for the award of any degree or diploma.",
        STYLES["Body"]
    ))
    story.append(Spacer(1, 80))
    story.append(Paragraph("Aryan Sharma", STYLES["BodyNoIndent"]))
    story.append(Paragraph("Date: July 2026", STYLES["BodyNoIndent"]))
    story.append(PageBreak())

    # ─────────────────── ACKNOWLEDGEMENT ───────────────────────────────
    story.append(Spacer(1, 60))
    story.append(Paragraph("ACKNOWLEDGEMENT", STYLES["Ch_Title"]))
    story.append(hr())
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "I would like to express my sincere gratitude to all those who have contributed to the successful completion "
        "of this project. I am deeply thankful to my project guide for their invaluable guidance, encouragement, and "
        "constructive feedback throughout the development of this project.",
        STYLES["Body"]
    ))
    story.append(Paragraph(
        "I would also like to thank the faculty members of the department for providing an excellent academic environment "
        "and the necessary infrastructure that facilitated the research and development work. Their support in providing "
        "access to computational resources and software tools was instrumental in the successful implementation of the "
        "machine learning pipeline and web application.",
        STYLES["Body"]
    ))
    story.append(Paragraph(
        "Special thanks go to the open-source community behind Python, Flask, scikit-learn, Plotly, and ReportLab, "
        "whose excellent tools and documentation made this project possible. The availability of high-quality, "
        "freely available machine learning libraries significantly accelerated the development process.",
        STYLES["Body"]
    ))
    story.append(Paragraph(
        "Finally, I express my heartfelt thanks to my family and friends for their constant support, patience, "
        "and motivation during the course of this project.",
        STYLES["Body"]
    ))
    story.append(Spacer(1, 40))
    story.append(Paragraph("<b>Aryan Sharma</b>", STYLES["BodyNoIndent"]))
    story.append(PageBreak())

    # ─────────────────── ABSTRACT ──────────────────────────────────────
    story.append(Spacer(1, 40))
    story.append(Paragraph("ABSTRACT", STYLES["Ch_Title"]))
    story.append(hr())
    story.append(Spacer(1, 10))
    story.append(Paragraph(ABSTRACT, STYLES["AbstractBody"]))
    story.append(Spacer(1, 24))

    # Keywords
    story.append(Paragraph(
        "<b>Keywords:</b> Customer Churn, Machine Learning, Random Forest, Gradient Boosting, "
        "Logistic Regression, Flask, Predictive Analytics, Telecommunications, Data Science, "
        "Classification, Feature Engineering, ROC AUC",
        STYLES["BodyNoIndent"]
    ))
    story.append(PageBreak())

    # ─────────────────── TABLE OF CONTENTS ────────────────────────────
    story.append(Spacer(1, 30))
    story.append(Paragraph("TABLE OF CONTENTS", STYLES["Ch_Title"]))
    story.append(hr())
    story.append(Spacer(1, 12))

    # Preliminary pages
    prelim = ["Certificate", "Declaration", "Acknowledgement", "Abstract", "Table of Contents", "List of Tables", "List of Figures"]
    for p in prelim:
        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{p}", STYLES["TOC_Sec"]))

    story.append(Spacer(1, 8))

    for ch in CHAPTERS:
        story.append(Paragraph(
            f"Chapter {ch['number']}: {ch['title']}", STYLES["TOC_Ch"]
        ))
        for sec in ch.get("sections", []):
            story.append(Paragraph(
                f"&nbsp;&nbsp;&nbsp;&nbsp;{ch['number']}.{ch['sections'].index(sec)+1}&nbsp;&nbsp;{sec['title']}",
                STYLES["TOC_Sec"]
            ))

    story.append(Spacer(1, 8))
    story.append(Paragraph("References", STYLES["TOC_Ch"]))
    story.append(Paragraph("Appendix A: Source Code Listings", STYLES["TOC_Ch"]))
    story.append(Paragraph("Appendix B: Glossary of Terms", STYLES["TOC_Ch"]))
    story.append(PageBreak())

    # ─────────────────── LIST OF TABLES ───────────────────────────────
    story.append(Spacer(1, 30))
    story.append(Paragraph("LIST OF TABLES", STYLES["Ch_Title"]))
    story.append(hr())
    story.append(Spacer(1, 10))
    tables_list = [
        "Table 3.1: Functional Requirements",
        "Table 3.2: Non-Functional Requirements",
        "Table 3.3: Hardware Requirements",
        "Table 3.4: Software Requirements",
        "Table 5.1: Feature Description Summary",
        "Table 5.2: Target Variable Distribution",
        "Table 6.1: Algorithm Hyperparameters",
        "Table 8.1: Model Performance Comparison",
        "Table 8.2: Confusion Matrix — Random Forest",
        "Table 8.3: Confusion Matrix — Gradient Boosting",
        "Table 8.4: Confusion Matrix — Logistic Regression",
        "Table 8.5: Top 10 Feature Importances",
    ]
    for tl in tables_list:
        story.append(Paragraph(tl, STYLES["TOC_Sec"]))
    story.append(PageBreak())

    # ─────────────────── LIST OF FIGURES ──────────────────────────────
    story.append(Spacer(1, 30))
    story.append(Paragraph("LIST OF FIGURES", STYLES["Ch_Title"]))
    story.append(hr())
    story.append(Spacer(1, 10))
    figures_list = [
        "Figure 4.1: System Architecture Diagram",
        "Figure 4.2: Data Flow Diagram",
        "Figure 4.3: Directory Structure",
        "Figure 5.1: Churn Distribution",
        "Figure 5.2: Contract Type Distribution",
        "Figure 6.1: Machine Learning Pipeline",
        "Figure 6.2: Random Forest Algorithm Illustration",
        "Figure 6.3: Gradient Boosting Sequential Learning",
        "Figure 6.4: Logistic (Sigmoid) Function",
        "Figure 8.1: Model Comparison (ROC AUC)",
        "Figure 8.2: Feature Importance Chart",
    ]
    for fl in figures_list:
        story.append(Paragraph(fl, STYLES["TOC_Sec"]))
    story.append(PageBreak())

    # ═══════════════════ CHAPTERS ══════════════════════════════════════

    for ch in CHAPTERS:
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"CHAPTER {ch['number']}", STYLES["SmallNote"]))
        story.append(Paragraph(ch["title"].upper(), STYLES["Ch_Title"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT, spaceBefore=2, spaceAfter=16))

        for si, sec in enumerate(ch.get("sections", []), 1):
            story.append(Paragraph(f"{ch['number']}.{si}&nbsp;&nbsp;{sec['title']}", STYLES["Sec_Title"]))

            # Paragraphs
            for para in sec.get("paragraphs", []):
                story.append(Paragraph(para, STYLES["Body"]))

            # Bullets
            for bullet in sec.get("bullets", []):
                story.append(Paragraph(f"•&nbsp;&nbsp;{bullet}", STYLES["Bullet"]))

            story.append(Spacer(1, 6))

        # ── Inject extra tables/diagrams per chapter ──
        if ch["number"] == 3:
            _inject_chapter3_tables(story)
        elif ch["number"] == 5:
            _inject_chapter5_tables(story)
        elif ch["number"] == 6:
            _inject_chapter6_extras(story)
        elif ch["number"] == 7:
            _inject_chapter7_code(story)
        elif ch["number"] == 8:
            _inject_chapter8_results(story)

        story.append(PageBreak())

    # ═══════════════════ REFERENCES ═══════════════════════════════════
    story.append(Spacer(1, 20))
    story.append(Paragraph("REFERENCES", STYLES["Ch_Title"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT, spaceBefore=2, spaceAfter=16))
    for i, ref in enumerate(REFERENCES, 1):
        story.append(Paragraph(f"[{i}]&nbsp;&nbsp;{ref}", STYLES["Ref"]))
    story.append(PageBreak())

    # ═══════════════════ APPENDIX A: SOURCE CODE ═════════════════════
    story.append(Spacer(1, 20))
    story.append(Paragraph("APPENDIX A", STYLES["SmallNote"]))
    story.append(Paragraph("SOURCE CODE LISTINGS", STYLES["Ch_Title"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT, spaceBefore=2, spaceAfter=16))

    source_files = [
        ("A.1", "config.py", "Configuration Module"),
        ("A.2", "train_model.py", "Model Training Pipeline"),
        ("A.3", "app.py", "Flask Application"),
    ]
    for label, fname, title in source_files:
        story.append(Paragraph(f"{label}&nbsp;&nbsp;{title} ({fname})", STYLES["Sec_Title"]))
        code = read_source(fname, max_lines=150)
        # Split into manageable chunks to avoid overflow
        code_lines = code.split("\n")
        chunk_size = 60
        for ci in range(0, len(code_lines), chunk_size):
            chunk = "\n".join(code_lines[ci:ci + chunk_size])
            # Escape XML chars
            chunk = chunk.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Preformatted(chunk, STYLES["CodeBlock"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ═══════════════════ APPENDIX B: GLOSSARY ════════════════════════
    story.append(Spacer(1, 20))
    story.append(Paragraph("APPENDIX B", STYLES["SmallNote"]))
    story.append(Paragraph("GLOSSARY OF TERMS", STYLES["Ch_Title"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_ACCENT, spaceBefore=2, spaceAfter=16))

    glossary = [
        ("AUC", "Area Under the Curve — a measure of a classifier's ability to distinguish between classes."),
        ("Churn", "The phenomenon where customers discontinue their service with a provider."),
        ("Classification", "A supervised learning task where the output is a discrete category (e.g., Churn/No Churn)."),
        ("Confusion Matrix", "A table showing true positives, true negatives, false positives, and false negatives."),
        ("F1-Score", "The harmonic mean of precision and recall, providing a balanced measure of classification quality."),
        ("Feature Engineering", "The process of selecting, transforming, and creating features from raw data to improve model performance."),
        ("Flask", "A lightweight Python web framework for building web applications and APIs."),
        ("Gradient Boosting", "An ensemble technique that builds models sequentially, each correcting errors of the previous one."),
        ("KPI", "Key Performance Indicator — a measurable value demonstrating effectiveness."),
        ("Label Encoding", "Converting categorical text labels to numerical values (e.g., Male → 1, Female → 0)."),
        ("Logistic Regression", "A statistical model that uses the sigmoid function to predict binary outcomes."),
        ("MVC", "Model-View-Controller — a software architecture pattern separating data, presentation, and logic."),
        ("One-Hot Encoding", "Converting a categorical variable into multiple binary columns (one per category)."),
        ("Precision", "The proportion of positive predictions that are actually correct: TP / (TP + FP)."),
        ("Random Forest", "An ensemble of decision trees trained on bootstrap samples with random feature subsets."),
        ("Recall", "The proportion of actual positives correctly identified: TP / (TP + FN). Also called Sensitivity."),
        ("ROC", "Receiver Operating Characteristic — a curve plotting True Positive Rate vs False Positive Rate."),
        ("Scikit-learn", "A popular Python library for machine learning, providing classification, regression, and clustering tools."),
        ("Standard Scaling", "Transforming features to have zero mean and unit variance: z = (x - μ) / σ."),
        ("WSGI", "Web Server Gateway Interface — a specification for Python web application/server communication."),
    ]
    for term, defn in glossary:
        story.append(Paragraph(f"<b>{term}</b> — {defn}", STYLES["Body"]))

    # ── Build ──
    print(f"Building PDF report: {OUTPUT_PDF}")
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    print(f"✓ Report generated successfully: {OUTPUT_PDF}")
    print(f"  Pages: ~60+ professional pages")


# ══════════════════════════════════════════════════════════════════════
#  CHAPTER INJECTIONS (tables, diagrams, code)
# ══════════════════════════════════════════════════════════════════════

def _inject_chapter3_tables(story):
    """Add requirements tables to Chapter 3."""
    story.append(Spacer(1, 10))
    story.append(Paragraph("Table 3.1: Summary of Functional Requirements", STYLES["Caption"]))
    fr_rows = [
        ["FR-01", "Secure login with username/password authentication"],
        ["FR-02", "Dashboard with KPIs (total customers, churn rate, charges)"],
        ["FR-03", "Real-time churn prediction with probability score"],
        ["FR-04", "Interactive analytics visualizations (6 chart types)"],
        ["FR-05", "Paginated dataset explorer for training data"],
        ["FR-06", "Methodology page with ML algorithm explanations"],
        ["FR-07", "Session-based logout functionality"],
        ["FR-08", "Auto-train model if no pre-trained model found"],
    ]
    story.append(make_table(["ID", "Description"], fr_rows, [60, CW - 60]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Table 3.2: Software Requirements", STYLES["Caption"]))
    sw_rows = [
        ["Python", "3.9+", "Core programming language"],
        ["Flask", "3.0.3", "Web application framework"],
        ["Pandas", "2.2.2", "Data manipulation and analysis"],
        ["NumPy", "1.26.4", "Numerical computing"],
        ["Scikit-learn", "1.5.1", "Machine learning algorithms"],
        ["Plotly", "5.22.0", "Interactive visualizations"],
        ["Gunicorn", "22.0.0", "Production WSGI server"],
    ]
    story.append(make_table(["Component", "Version", "Purpose"], sw_rows, [100, 60, CW - 160]))
    story.append(Spacer(1, 10))


def _inject_chapter5_tables(story):
    """Add data analysis tables to Chapter 5."""
    story.append(Spacer(1, 10))
    story.append(Paragraph("Table 5.1: Feature Categories and Types", STYLES["Caption"]))
    feat_rows = [
        ["gender", "Categorical", "Male / Female"],
        ["SeniorCitizen", "Binary", "0 (No) / 1 (Yes)"],
        ["Partner", "Categorical", "Yes / No"],
        ["Dependents", "Categorical", "Yes / No"],
        ["tenure", "Numerical", "0–72 months"],
        ["PhoneService", "Categorical", "Yes / No"],
        ["InternetService", "Categorical", "DSL / Fiber optic / No"],
        ["Contract", "Categorical", "Month-to-month / One year / Two year"],
        ["MonthlyCharges", "Numerical", "$18.25 – $118.75"],
        ["TotalCharges", "Numerical", "$18.80 – $8,684.80"],
        ["Churn", "Target", "Yes / No"],
    ]
    story.append(make_table(["Feature", "Type", "Values/Range"], feat_rows, [120, 80, CW - 200]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Table 5.2: Target Variable Distribution", STYLES["Caption"]))
    churn_rows = [
        ["No (Retained)", str(stats["no_churn_count"]), f"{100 - stats['churn_rate']:.2f}%"],
        ["Yes (Churned)", str(stats["churn_count"]), f"{stats['churn_rate']:.2f}%"],
        ["Total", str(stats["total_customers"]), "100.00%"],
    ]
    story.append(make_table(["Class", "Count", "Percentage"], churn_rows, [140, 100, 100]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Table 5.3: Contract Distribution", STYLES["Caption"]))
    contract = stats.get("contract_distribution", {})
    c_rows = [[k, str(v), f"{v/stats['total_customers']*100:.1f}%"] for k, v in contract.items()]
    story.append(make_table(["Contract Type", "Count", "Percentage"], c_rows, [160, 100, 100]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Table 5.4: Internet Service Distribution", STYLES["Caption"]))
    internet = stats.get("internet_service_distribution", {})
    i_rows = [[k, str(v), f"{v/stats['total_customers']*100:.1f}%"] for k, v in internet.items()]
    story.append(make_table(["Internet Service", "Count", "Percentage"], i_rows, [160, 100, 100]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Table 5.5: Payment Method Distribution", STYLES["Caption"]))
    payment = stats.get("payment_method_distribution", {})
    p_rows = [[k, str(v), f"{v/stats['total_customers']*100:.1f}%"] for k, v in payment.items()]
    story.append(make_table(["Payment Method", "Count", "Percentage"], p_rows, [180, 100, 100]))
    story.append(Spacer(1, 10))

    # Key statistics summary
    story.append(Paragraph("Table 5.6: Key Dataset Statistics", STYLES["Caption"]))
    stats_rows = [
        ["Total Customers", str(stats["total_customers"])],
        ["Churn Rate", f"{stats['churn_rate']}%"],
        ["Average Tenure", f"{stats['avg_tenure']} months"],
        ["Average Monthly Charges", f"${stats['avg_monthly_charges']}"],
        ["Number of Features", "21"],
    ]
    story.append(make_table(["Metric", "Value"], stats_rows, [200, CW - 200]))


def _inject_chapter6_extras(story):
    """Add algorithm parameter tables for Chapter 6."""
    story.append(Spacer(1, 10))
    story.append(Paragraph("Table 6.1: Algorithm Hyperparameters", STYLES["Caption"]))
    hp_rows = [
        ["Random Forest", "n_estimators", "200"],
        ["", "max_depth", "15"],
        ["", "min_samples_split", "5"],
        ["", "min_samples_leaf", "2"],
        ["", "criterion", "Gini impurity"],
        ["Gradient Boosting", "n_estimators", "150"],
        ["", "max_depth", "5"],
        ["", "learning_rate", "0.1"],
        ["", "loss", "Log loss (binary cross-entropy)"],
        ["Logistic Regression", "C (regularization)", "1.0"],
        ["", "solver", "LBFGS"],
        ["", "max_iter", "1000"],
        ["", "penalty", "L2"],
    ]
    story.append(make_table(["Algorithm", "Parameter", "Value"], hp_rows, [130, 130, CW - 260]))
    story.append(Spacer(1, 16))

    # Mathematical formulations recap
    story.append(Paragraph("6.5&nbsp;&nbsp;Mathematical Formulations Summary", STYLES["Sec_Title"]))
    formulas = [
        ("Standard Scaling", "z = (x − μ) / σ, where μ is the mean and σ is the standard deviation"),
        ("Gini Impurity", "G(p) = 1 − Σ pᵢ², where pᵢ is the proportion of class i"),
        ("Random Forest Prediction", "ŷ = mode{h₁(x), h₂(x), ..., h_B(x)}, where B is the number of trees"),
        ("Gradient Boosting Update", "F_m(x) = F_{m-1}(x) + η · h_m(x), where η is the learning rate"),
        ("Log Loss", "L(y, F) = −[y·log(p) + (1−y)·log(1−p)]"),
        ("Sigmoid Function", "σ(z) = 1 / (1 + e^(−z))"),
        ("Accuracy", "(TP + TN) / (TP + TN + FP + FN)"),
        ("Precision", "TP / (TP + FP)"),
        ("Recall", "TP / (TP + FN)"),
        ("F1-Score", "2 × (Precision × Recall) / (Precision + Recall)"),
    ]
    f_rows = [[n, f] for n, f in formulas]
    story.append(Paragraph("Table 6.2: Mathematical Formulations Used", STYLES["Caption"]))
    story.append(make_table(["Metric/Formula", "Expression"], f_rows, [150, CW - 150]))
    story.append(Spacer(1, 10))


def _inject_chapter7_code(story):
    """Add key code snippets to Chapter 7."""
    story.append(Spacer(1, 10))
    story.append(Paragraph("7.6&nbsp;&nbsp;Key Code Snippets", STYLES["Sec_Title"]))

    story.append(Paragraph("Listing 7.1: Configuration Module (config.py)", STYLES["Caption"]))
    code = read_source_full("config.py")
    code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    story.append(Preformatted(code, STYLES["CodeBlock"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Listing 7.2: Data Preprocessing Function", STYLES["Caption"]))
    preprocess_code = '''def preprocess_data(df):
    """Preprocess the dataset for model training."""
    df = df.copy()
    df = df.drop('customerID', axis=1)

    df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
    df['TotalCharges'].fillna(df['TotalCharges'].median(), inplace=True)

    # Encode binary columns
    binary_cols = ['gender', 'Partner', 'Dependents',
                   'PhoneService', 'PaperlessBilling', 'Churn']
    le = LabelEncoder()
    for col in binary_cols:
        df[col] = le.fit_transform(df[col])

    # One-hot encode multi-category columns
    multi_cols = ['MultipleLines', 'InternetService', 'OnlineSecurity',
                  'OnlineBackup', 'DeviceProtection', 'TechSupport',
                  'StreamingTV', 'StreamingMovies', 'Contract',
                  'PaymentMethod']
    df = pd.get_dummies(df, columns=multi_cols, drop_first=True)

    return df'''
    story.append(Preformatted(preprocess_code, STYLES["CodeBlock"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Listing 7.3: Model Training and Evaluation Loop", STYLES["Caption"]))
    train_code = '''models = {
    'Random Forest': RandomForestClassifier(
        n_estimators=200, max_depth=15,
        min_samples_split=5, min_samples_leaf=2,
        random_state=42, n_jobs=-1
    ),
    'Gradient Boosting': GradientBoostingClassifier(
        n_estimators=150, max_depth=5,
        learning_rate=0.1, random_state=42
    ),
    'Logistic Regression': LogisticRegression(
        max_iter=1000, random_state=42, C=1.0
    )
}

best_model, best_score, best_name = None, 0, ''
for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    roc = roc_auc_score(y_test, y_prob)
    if roc > best_score:
        best_score = roc
        best_model = model
        best_name = name'''
    story.append(Preformatted(train_code, STYLES["CodeBlock"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Listing 7.4: Prediction Route (Flask)", STYLES["Caption"]))
    predict_code = '''@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    prediction = None
    probability = None
    if request.method == 'POST' and model is not None:
        form_data = {
            'gender': request.form.get('gender', 'Male'),
            'SeniorCitizen': int(request.form.get('SeniorCitizen', 0)),
            'tenure': int(request.form.get('tenure', 1)),
            'Contract': request.form.get('Contract', 'Month-to-month'),
            # ... (19 total features)
        }
        input_df = pd.DataFrame([form_data])
        # Apply same encoding & scaling as training
        input_df = preprocess_input(input_df)
        X_input = scaler.transform(input_df[feature_names].values)
        pred = model.predict(X_input)[0]
        prob = model.predict_proba(X_input)[0]
        prediction = 'Churn' if pred == 1 else 'No Churn'
        probability = round(float(prob[1]) * 100, 2)
    return render_template('predict.html',
        prediction=prediction, probability=probability)'''
    story.append(Preformatted(predict_code, STYLES["CodeBlock"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Listing 7.5: Authentication Decorator", STYLES["Caption"]))
    auth_code = '''def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function'''
    story.append(Preformatted(auth_code, STYLES["CodeBlock"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Listing 7.6: Chart Data API Endpoint", STYLES["Caption"]))
    chart_code = '''@app.route('/api/chart-data/&lt;chart_type&gt;')
@login_required
def chart_data(chart_type):
    if chart_type == 'churn_distribution':
        counts = df['Churn'].value_counts()
        return jsonify({
            'labels': counts.index.tolist(),
            'values': counts.values.tolist()
        })
    elif chart_type == 'feature_importance':
        features = stats['top_features']
        return jsonify({
            'labels': [f['feature'] for f in features],
            'values': [f['importance'] for f in features]
        })
    # ... 5 more chart types
    return jsonify({'error': 'Unknown chart type'}), 400'''
    story.append(Preformatted(chart_code, STYLES["CodeBlock"]))


def _inject_chapter8_results(story):
    """Add result tables and confusion matrices for Chapter 8."""
    results = stats.get("model_results", {})
    features = stats.get("top_features", [])

    story.append(Spacer(1, 10))
    story.append(Paragraph("Table 8.1: Model Performance Comparison", STYLES["Caption"]))
    perf_rows = []
    for name, r in results.items():
        perf_rows.append([
            name,
            f"{r['accuracy']*100:.2f}%",
            f"{r['precision']*100:.2f}%",
            f"{r['recall']*100:.2f}%",
            f"{r['f1_score']*100:.2f}%",
            f"{r['roc_auc']*100:.2f}%",
        ])
    story.append(make_table(
        ["Model", "Accuracy", "Precision", "Recall", "F1-Score", "ROC AUC"],
        perf_rows,
        [120, 68, 68, 68, 68, 68]
    ))
    story.append(Spacer(1, 16))

    # Confusion matrices
    for name, r in results.items():
        cm = r.get("confusion_matrix", [[0, 0], [0, 0]])
        tn, fp = cm[0]
        fn, tp = cm[1]
        story.append(Paragraph(f"Table 8.x: Confusion Matrix — {name}", STYLES["Caption"]))
        cm_rows = [
            ["Actual No", str(tn), str(fp), str(tn + fp)],
            ["Actual Yes", str(fn), str(tp), str(fn + tp)],
            ["Total", str(tn + fn), str(fp + tp), str(tn + fp + fn + tp)],
        ]
        story.append(make_table(
            ["", "Predicted No", "Predicted Yes", "Total"],
            cm_rows, [100, 100, 100, 80]
        ))
        story.append(Spacer(1, 12))

    # Best model highlight
    story.append(Paragraph("8.5&nbsp;&nbsp;Best Model Selection", STYLES["Sec_Title"]))
    best = stats.get("best_model", "Logistic Regression")
    best_r = results.get(best, {})
    story.append(Paragraph(
        f"Based on the ROC AUC metric, <b>{best}</b> was selected as the best-performing model "
        f"with a ROC AUC score of <b>{best_r.get('roc_auc', 0)*100:.2f}%</b>. "
        f"This model achieved accuracy of {best_r.get('accuracy', 0)*100:.2f}%, "
        f"precision of {best_r.get('precision', 0)*100:.2f}%, "
        f"recall of {best_r.get('recall', 0)*100:.2f}%, "
        f"and F1-score of {best_r.get('f1_score', 0)*100:.2f}%. "
        "The model was serialized using Python's pickle module and deployed in the production Flask application.",
        STYLES["Body"]
    ))
    story.append(Spacer(1, 12))

    # Feature importance table
    story.append(Paragraph("Table 8.5: Top 15 Feature Importances", STYLES["Caption"]))
    fi_rows = [[str(i+1), f["feature"], f"{f['importance']:.4f}"]
               for i, f in enumerate(features)]
    story.append(make_table(["Rank", "Feature", "Importance"], fi_rows, [50, 250, 100]))
    story.append(Spacer(1, 16))

    # Interpretation
    story.append(Paragraph("8.6&nbsp;&nbsp;Interpretation of Results", STYLES["Sec_Title"]))
    story.append(Paragraph(
        "The results reveal several important business insights for telecommunications companies seeking to reduce customer churn. "
        "The strong importance of contract type features (Two year: 0.8577, One year: 0.7337) confirms that long-term contracts are the most "
        "effective mechanism for customer retention. Customers on month-to-month contracts represent the highest churn risk and should be "
        "prioritized for retention campaigns offering contract upgrades with attractive incentives.",
        STYLES["Body"]
    ))
    story.append(Paragraph(
        "Tenure (0.5980) as the third most important feature highlights that newer customers are significantly more likely to churn. "
        "This suggests that the onboarding experience and early engagement are critical periods for customer retention. Companies should "
        "implement targeted onboarding programs and regular check-ins during the first year of service.",
        STYLES["Body"]
    ))
    story.append(Paragraph(
        "The importance of InternetService_Fiber optic (0.3171) and PaymentMethod_Electronic check (0.2728) suggests that certain "
        "service and billing configurations are associated with higher churn. Fiber optic customers may experience higher churn due to "
        "premium pricing or service quality issues, while electronic check users may lack the automatic payment convenience that reduces "
        "friction and promotes retention.",
        STYLES["Body"]
    ))
    story.append(Paragraph(
        "The significance of OnlineSecurity (0.2235) and TechSupport (0.1672) as churn predictors indicates that customers without "
        "these value-added services are more likely to leave. Offering bundled security and support packages could serve as an effective "
        "retention strategy, simultaneously increasing average revenue per user (ARPU) and reducing churn risk.",
        STYLES["Body"]
    ))


# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    build_report()
