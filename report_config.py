"""
Report configuration constants and shared utilities.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

WIDTH, HEIGHT = A4
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MARGIN = 60
CONTENT_WIDTH = WIDTH - 2 * MARGIN

# Color palette
COLORS = {
    'primary': HexColor('#1a1a2e'),
    'accent': HexColor('#6366f1'),
    'accent_light': HexColor('#818cf8'),
    'text': HexColor('#1e293b'),
    'text_light': HexColor('#64748b'),
    'heading': HexColor('#0f172a'),
    'white': HexColor('#ffffff'),
    'bg_light': HexColor('#f8fafc'),
    'border': HexColor('#e2e8f0'),
    'success': HexColor('#22c55e'),
    'danger': HexColor('#ef4444'),
    'warning': HexColor('#f59e0b'),
    'code_bg': HexColor('#f1f5f9'),
    'table_header': HexColor('#4338ca'),
    'table_alt': HexColor('#f1f5f9'),
}

# Project metadata
PROJECT = {
    'title': 'Customer Churn Prediction System',
    'subtitle': 'Using Machine Learning and Predictive Analytics',
    'author': 'Aryan Sharma',
    'year': '2026',
    'institution': '',
    'app_name': 'ChurnGuard AI',
}

# Screenshot paths (user-provided)
SCREENSHOT_DIR = os.path.join(BASE_DIR, 'screenshots')


def get_styles():
    """Return custom paragraph styles for the report."""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        'ReportTitle', parent=styles['Title'],
        fontSize=28, leading=34, textColor=COLORS['white'],
        alignment=TA_CENTER, spaceAfter=12, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'ReportSubtitle', parent=styles['Normal'],
        fontSize=14, leading=20, textColor=HexColor('#c7d2fe'),
        alignment=TA_CENTER, spaceAfter=6, fontName='Helvetica',
    ))
    styles.add(ParagraphStyle(
        'ChapterTitle', parent=styles['Heading1'],
        fontSize=22, leading=28, textColor=COLORS['accent'],
        spaceBefore=20, spaceAfter=14, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'SectionTitle', parent=styles['Heading2'],
        fontSize=16, leading=22, textColor=COLORS['heading'],
        spaceBefore=16, spaceAfter=8, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'SubSection', parent=styles['Heading3'],
        fontSize=13, leading=18, textColor=COLORS['text'],
        spaceBefore=10, spaceAfter=6, fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'BodyText2', parent=styles['Normal'],
        fontSize=11, leading=17, textColor=COLORS['text'],
        alignment=TA_JUSTIFY, spaceAfter=8, fontName='Helvetica',
        firstLineIndent=20,
    ))
    styles.add(ParagraphStyle(
        'BodyNoIndent', parent=styles['Normal'],
        fontSize=11, leading=17, textColor=COLORS['text'],
        alignment=TA_JUSTIFY, spaceAfter=8, fontName='Helvetica',
    ))
    styles.add(ParagraphStyle(
        'BulletStyle', parent=styles['Normal'],
        fontSize=11, leading=17, textColor=COLORS['text'],
        spaceAfter=4, fontName='Helvetica', leftIndent=30, bulletIndent=15,
    ))
    styles.add(ParagraphStyle(
        'CodeStyle', parent=styles['Normal'],
        fontSize=9, leading=13, textColor=COLORS['text'],
        fontName='Courier', backColor=COLORS['code_bg'],
        leftIndent=15, rightIndent=15, spaceBefore=6, spaceAfter=6,
        borderWidth=1, borderColor=COLORS['border'], borderPadding=8,
    ))
    styles.add(ParagraphStyle(
        'Caption', parent=styles['Normal'],
        fontSize=9, leading=13, textColor=COLORS['text_light'],
        alignment=TA_CENTER, spaceAfter=12, fontName='Helvetica-Oblique',
    ))
    styles.add(ParagraphStyle(
        'TOCEntry', parent=styles['Normal'],
        fontSize=12, leading=22, textColor=COLORS['text'],
        fontName='Helvetica', leftIndent=20,
    ))
    styles.add(ParagraphStyle(
        'TOCChapter', parent=styles['Normal'],
        fontSize=13, leading=24, textColor=COLORS['heading'],
        fontName='Helvetica-Bold', leftIndent=0, spaceBefore=4,
    ))
    styles.add(ParagraphStyle(
        'PageNumber', parent=styles['Normal'],
        fontSize=9, textColor=COLORS['text_light'],
        alignment=TA_CENTER, fontName='Helvetica',
    ))
    styles.add(ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=COLORS['text_light'],
        alignment=TA_CENTER, fontName='Helvetica',
    ))
    
    return styles
