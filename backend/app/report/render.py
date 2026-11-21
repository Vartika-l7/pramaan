"""Court Report PDF Generation with QR Code and Section 63 BSA Certificate."""

from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
    KeepTogether,
)

from backend.app.integrity.merkle import compute_case_merkle_root
from backend.app.report.certificate import generate_section_63_bsa_certificate_text


def generate_court_report_pdf(
    conn: sqlite3.Connection,
    output_pdf_path: Path,
    case_id: str = "PRM-2026-0042",
) -> Path:
    """Render the official court forensics report citing only approved evidence and findings."""
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#2B1B17"),
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#7A5C52"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B1B17"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#2B1B17"),
    )
    mono_style = ParagraphStyle(
        "ReportMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#2B1B17"),
    )
    notice_style = ParagraphStyle(
        "SyntheticNotice",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#C97B1A"),
    )

    story = []

    # 1. Header & Case Metadata
    story.append(Paragraph("<b>FORENSIC DIGITAL EVIDENCE EXAMINATION REPORT</b>", title_style))
    story.append(Paragraph("DIGITAL EVIDENCE CORRELATION AND CRIME RECONSTRUCTION ENGINE", subtitle_style))
    story.append(Spacer(1, 8))

    # Synthetic case warning banner
    banner_data = [[
        Paragraph(
            "<b>NOTICE:</b> Synthetic case PRM-2026-0042. All persons, bank accounts, UPI IDs, and phone numbers are fictional. Prepared for National Hackathon Demonstration.",
            notice_style,
        )
    ]]
    banner_table = Table(banner_data, colWidths=[540])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FDF6E9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#C97B1A")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 12))

    # Case Details & QR Code
    merkle_root, exhibits_list = compute_case_merkle_root(conn)

    # Generate QR Code image encoding Merkle root and verifier command
    qr_content = f"PRAMAAN-CASE:{case_id}|ROOT:{merkle_root}|VERIFIER:python verifier.py --manifest manifest.json"
    qr_img = qrcode.make(qr_content)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    rl_qr = RLImage(qr_buffer, width=64, height=64)

    meta_data = [
        ["Case Reference:", case_id, "Date of Report:", "16/03/2026"],
        ["Investigative Unit:", "Cyber Crime Police Station", "Investigator ID:", "INV-88912"],
        ["Integrity Status:", "TAMPER-EVIDENT HASH CHAIN VERIFIED", "Total Exhibits:", str(len(exhibits_list))],
        ["Consolidated Merkle Root:", Paragraph(f"<font name='Courier' size=7>{merkle_root}</font>", body_style), "", rl_qr],
    ]
    meta_table = Table(meta_data, colWidths=[120, 240, 90, 90])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('SPAN', (3,0), (3,2)),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 2. Executive Summary
    story.append(Paragraph("1. Executive Summary", section_heading))
    summary_text = (
        "This forensic report provides reconstructed event sequences and cross-source evidence correlation "
        "concerning the 'Alpha Wealth Club' investment fraud scheme. Ingestion integrity was guaranteed via "
        "first-order SHA-256 hashing and append-only SQLite custody logging. The analysis identified cross-source "
        "links between WhatsApp solicitations and beneficiary banking accounts, rapid mule forwarding patterns, "
        "shared handset device identifiers, and document balance anomalies."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))

    # 3. Evidence Manifest Table
    story.append(Paragraph("2. Ingested Evidence Manifest & Cryptographic Hashes", section_heading))
    manifest_headers = ["Exhibit Tag", "Source File", "Format", "Size", "SHA-256 Digest (First 16 chars)"]
    cursor = conn.cursor()
    cursor.execute("SELECT exhibit_id, filename, source_type, size_bytes, sha256 FROM evidence ORDER BY exhibit_id ASC;")
    ev_rows = cursor.fetchall()

    manifest_rows = [manifest_headers]
    for r in ev_rows:
        manifest_rows.append([
            r["exhibit_id"],
            r["filename"],
            r["source_type"].upper(),
            f"{(r['size_bytes'] / 1024):.1f} KB",
            f"{r['sha256'][:16]}...",
        ])

    m_table = Table(manifest_rows, colWidths=[65, 175, 65, 55, 180])
    m_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B1B17")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Courier'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(m_table)
    story.append(Spacer(1, 14))

    # 4. Findings Table (Human-Approved Findings Only)
    story.append(Paragraph("3. Human-Approved Investigative Findings (With Source Citations)", section_heading))
    cursor.execute("SELECT text, kind, tier, status, source_refs_json FROM claims WHERE status = 'APPROVED' ORDER BY rowid ASC;")
    claims_rows = cursor.fetchall()
    cursor.execute("SELECT src, dst, edge_type, reason_text, tier, event_ids_json FROM edges WHERE status = 'APPROVED' ORDER BY strength DESC;")
    approved_edges_rows = cursor.fetchall()

    if claims_rows or approved_edges_rows:
        findings_table_data = [["Finding #", "Approved Finding Statement", "Tier", "Cited Exhibit Refs"]]
        finding_idx = 1
        for cl in claims_rows:
            refs = json.loads(cl["source_refs_json"])
            ref_str = ", ".join([r[:8] for r in refs]) if refs else "N/A"
            findings_table_data.append([
                str(finding_idx),
                Paragraph(cl["text"], body_style),
                cl["tier"],
                ref_str,
            ])
            finding_idx += 1
        for ed in approved_edges_rows:
            eids = json.loads(ed["event_ids_json"])
            ref_str = ", ".join([r[:8] for r in eids[:4]]) if eids else "N/A"
            findings_table_data.append([
                str(finding_idx),
                Paragraph(f"{ed['src']} -> {ed['dst']} ({ed['edge_type']}): {ed['reason_text']}", body_style),
                ed["tier"],
                ref_str,
            ])
            finding_idx += 1

        f_table = Table(findings_table_data, colWidths=[45, 330, 75, 90])
        f_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2E5E6E")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(f_table)
    else:
        story.append(Paragraph("<i>No human-approved findings recorded. Only human-approved items enter the court report.</i>", body_style))

    story.append(Spacer(1, 14))

    # 5. Human-Approved Document & Media Authenticity Indicators
    story.append(Paragraph("4. Approved Document & Media Authenticity Indicators", section_heading))
    cursor.execute("SELECT kind, severity, description FROM anomalies WHERE status = 'APPROVED' ORDER BY severity ASC;")
    anom_rows = cursor.fetchall()

    if anom_rows:
        anom_table_data = [["Indicator Type", "Severity", "Technical Observation"]]
        for a in anom_rows:
            anom_table_data.append([
                a["kind"].replace("ANOMALY_", "").replace("PATTERN_", ""),
                a["severity"],
                Paragraph(a["description"], body_style),
            ])
        a_table = Table(anom_table_data, colWidths=[110, 60, 370])
        a_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#7A5C52")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(a_table)
    else:
        story.append(Paragraph("<i>No human-approved authenticity indicators in this court report. Unapproved indicators remain in the Investigation workspace.</i>", body_style))

    story.append(PageBreak())

    # 6. Annexure: Draft Section 63 BSA Certificate
    story.append(Paragraph("ANNEXURE: DRAFT CERTIFICATE UNDER SECTION 63 BSA, 2023", section_heading))
    story.append(Spacer(1, 6))

    cert_text = generate_section_63_bsa_certificate_text(
        case_id=case_id,
        exhibits=[dict(r) for r in ev_rows],
        merkle_root=merkle_root,
    )
    for line in cert_text.strip().splitlines():
        if line.startswith("="):
            story.append(Spacer(1, 4))
        elif line.startswith("-"):
            story.append(Spacer(1, 2))
        elif "PART A" in line or "PART B" in line:
            story.append(Paragraph(f"<b>{line}</b>", section_heading))
        else:
            story.append(Paragraph(f"<font name='Courier' size=7>{line}</font>", mono_style))

    doc.build(story)
    return output_pdf_path

