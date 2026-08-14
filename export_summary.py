"""Generate executive summary PDF from stats.json (presentation layer only)."""

import os
import json
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_PATH = os.path.join(BASE_DIR, 'data', 'stats.json')


def generate_executive_pdf():
    with open(STATS_PATH, 'r') as f:
        stats = json.load(f)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Title2', parent=styles['Heading1'], fontSize=22, spaceAfter=16, textColor=HexColor('#4F46E5')))
    styles.add(ParagraphStyle(name='H2', parent=styles['Heading2'], fontSize=14, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=11, leading=16, spaceAfter=8))

    best_name = stats.get('best_model', 'N/A')
    best = stats.get('model_results', {}).get(best_name, {})
    cm = stats.get('best_model_confusion_matrix', [[0, 0], [0, 0]])
    roc_auc = best.get('roc_auc', 0)

    story = [
        Paragraph('ChurnGuard AI — Executive Report', styles['Title2']),
        Paragraph(f'Generated {datetime.now().strftime("%B %d, %Y")}', styles['Body']),
        Spacer(1, 12),
        Paragraph(
            f'ChurnGuard AI addresses customer retention in telecommunications by predicting churn from '
            f'{stats.get("total_customers", 0):,} customer records. After preprocessing and stratified '
            f'80/20 evaluation with 5-fold cross-validation, <b>{best_name}</b> achieved a held-out '
            f'ROC AUC of <b>{roc_auc * 100:.2f}%</b> — substantially outperforming the naive '
            f'majority-class baseline (~50% ROC AUC).',
            styles['Body'],
        ),
        Paragraph('Headline Metrics (Best Model — Test Set)', styles['H2']),
    ]

    metrics_data = [
        ['Metric', 'Value'],
        ['Accuracy', f'{best.get("accuracy", 0) * 100:.2f}%'],
        ['Precision', f'{best.get("precision", 0) * 100:.2f}%'],
        ['Recall', f'{best.get("recall", 0) * 100:.2f}%'],
        ['F1 Score', f'{best.get("f1_score", 0) * 100:.2f}%'],
        ['ROC AUC', f'{roc_auc * 100:.2f}%'],
        ['CV ROC AUC', f'{best.get("cv_roc_auc_mean", 0) * 100:.2f}% ± {best.get("cv_roc_auc_std", 0) * 100:.2f}%'],
    ]
    t = Table(metrics_data, colWidths=[180, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#FFFFFF'), HexColor('#F7F8FC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E3E5EF')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))
    story.append(Paragraph('Confusion Matrix (Test Set)', styles['H2']))
    cm_table = Table([
        ['', 'Pred: Retained', 'Pred: Churned'],
        ['Actual: Retained', str(cm[0][0]), str(cm[0][1])],
        ['Actual: Churned', str(cm[1][0]), str(cm[1][1])],
    ], colWidths=[120, 120, 120])
    cm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E3E5EF')),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CDD0DE')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(cm_table)
    story.append(PageBreak())
    story.append(Paragraph('Model Comparison Summary', styles['H2']))

    rows = [['Model', 'Test ROC AUC', 'Test F1', 'Test Accuracy']]
    for name, r in stats.get('model_results', {}).items():
        rows.append([
            name,
            f'{r.get("roc_auc", 0) * 100:.2f}%',
            f'{r.get("f1_score", 0) * 100:.2f}%',
            f'{r.get("accuracy", 0) * 100:.2f}%',
        ])
    comp = Table(rows, colWidths=[180, 90, 80, 90])
    comp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#FFFFFF')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#E3E5EF')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    story.append(comp)
    story.append(Spacer(1, 16))
    story.append(Paragraph('Methodology Summary', styles['H2']))
    v = stats.get('validation', {})
    story.append(Paragraph(
        f'Imbalance handling: {v.get("imbalance_method", "class_weight")}. '
        f'Split: {v.get("train_test_split", "80/20 stratified")}. '
        f'Cross-validation: {v.get("cv_folds", 5)}-fold stratified. '
        f'{v.get("reproducibility_note", "")}',
        styles['Body'],
    ))
    story.append(Paragraph(
        'This report was generated by ChurnGuard AI for academic demonstration. '
        'Dataset: anonymised Telco Customer Churn benchmark. Not for production deployment without further validation.',
        styles['Body'],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
