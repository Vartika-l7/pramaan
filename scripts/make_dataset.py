"""Synthetic Dataset Generator for PRAMAAN (Case PRM-2026-0042).

Generates completely fictional, deterministic forensic exhibits for the
"Alpha Wealth Club" investment fraud scenario with 10 planted ground-truth facts.
"""

from __future__ import annotations

import csv
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ExifTags
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

CASE_ID = "PRM-2026-0042"
CASE_TITLE = "Alpha Wealth Club Investment Fraud"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"

# Fictional entities
ENTITIES = {
    "victim_meera": {
        "name": "Meera Iyer",
        "phone": "+91 90000 10003",
        "city": "Pune",
        "account": "919000034455",
        "ifsc": "HDFC0000123",
    },
    "victim_anil": {
        "name": "Anil Deshmukh",
        "phone": "+91 90000 10004",
        "city": "Nagpur",
        "account": "919000045566",
        "ifsc": "SBIN0000456",
    },
    "fraud_vikram": {
        "name": "Vikram Sharma",
        "variants": ["Vikram Sharma", "Vikram Sharma Ji", "विक्रम शर्मा"],
        "phone": "+91 90000 10001",
        "vpa": "vikram.alpha@okaxis",
        "device_id": "D1",
    },
    "fraud_riya": {
        "name": "Riya (Support)",
        "phone": "+91 90000 10002",
        "device_id": "D1",  # GT-03: Shared device D1
    },
    "mule_a": {
        "name": "Deepak Rawat",
        "account": "912345678901",
        "ifsc": "PUNB0123456",
        "vpa": "vikram.alpha@okaxis",  # GT-01: Cross-source link
    },
    "mule_b": {
        "name": "Sunita Verma",
        "account": "912345678902",
        "ifsc": "HDFC0001234",
    },
    "mule_c": {
        "name": "Kabir Anand",
        "account": "912345678903",
        "ifsc": "SBIN0001234",
    },
}


def setup_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def generate_whatsapp_group(out_path: Path):
    """Generate ~600 messages over 6 days with Hinglish, Devanagari, GT-04 gap, and GT-05 out-of-order."""
    random.seed(42)
    start_time = datetime(2026, 3, 12, 9, 0, 0)
    
    hinglish_chatter = [
        ("Rahul Patel", "Hello everyone, anyone got today's return?"),
        ("Vikram Sharma Ji", "Yes Rahul ji, payout processed at 9 AM sharp. Profit pakka hai."),
        ("Sneha Rao", "I invested 25k yesterday, got 3k return today! Ek dum safe scheme."),
        ("Amit Kumar", "Sir what is the minimum investment for VIP Tier?"),
        ("Riya (Support)", "VIP Tier starts at 1 Lakh sir. Daily 4% return guaranteed."),
        ("Meera Iyer", "Is capital insured? Please share details."),
        ("Vikram Sharma", "Meera ji 100% capital guarantee backed by sovereign securities. Check our site https://alpha-wealth-club.fake-invest.in"),
        ("Anil Deshmukh", "Main bhi 50k invest karna chahta hoon. Kaise karein?"),
        ("Riya (Support)", "Anil ji please DM admin @Vikram Sharma or pay to registered VPA vikram.alpha@okaxis"),
        ("Priya Singh", "Great community! Loving the returns."),
        ("Vikram Sharma", "Today special bonus 10% on deposits above 1.5 Lakh. Limited slots!"),
        ("Karan Johar", "Payment proof shared in group. Thanks team!"),
        ("Meera Iyer", "I have messaged Vikram ji directly."),
        ("Deepak (Member)", "Alpha club rocks! Truly financial freedom."),
    ]
    
    devanagari_lines = [
        ("Vikram Sharma", "नमस्ते सभी सदस्यों को, आज का दैनिक लाभ विवरण जारी कर दिया गया है।"),
        ("Anil Deshmukh", "विक्रम शर्मा जी बहुत बढ़िया रिटर्न मिला, धन्यवाद।"),
        ("Vikram Sharma Ji", "सभी निवेशकों का स्वागत है, सुरक्षित निवेश हमारी प्राथमिकता है।"),
        ("Sneha Rao", "धन्यवाद विक्रम जी, समय पर भुगतान के लिए।"),
    ]
    
    messages = []
    messages.append("12/03/2026, 08:30 - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.")
    messages.append("12/03/2026, 08:45 - Vikram Sharma created group \"Alpha Wealth Club 💎\"")
    messages.append("12/03/2026, 08:46 - Vikram Sharma added you")
    messages.append("12/03/2026, 08:50 - Vikram Sharma: Welcome to Alpha Wealth Club. Official Helpline: +91 90000 10001. For verified investment slots contact admin.")
    
    curr = start_time
    # 6 days total: 12th to 17th March 2026
    # Day 3 is 14/03/2026. GT-04: 6h 14m gap on night of 14/03 from 23:45 to 15/03 05:59
    msg_count = 0
    day3_gap_inserted = False
    gt05_inserted = False
    
    while curr < datetime(2026, 3, 17, 18, 0, 0):
        curr_date = curr.date()
        
        # Check for GT-04: night of Day 3 (14/03/2026 23:45)
        if curr >= datetime(2026, 3, 14, 23, 40) and not day3_gap_inserted:
            ts_str = "14/03/2026, 23:45"
            messages.append(f"{ts_str} - Vikram Sharma: Good night members. Trading restarts tomorrow at 06:00 AM.")
            # Exactly 6h 14m gap -> jump to 15/03/2026 05:59
            curr = datetime(2026, 3, 15, 5, 59)
            ts_str2 = "15/03/2026, 05:59"
            messages.append(f"{ts_str2} - Riya (Support): Good morning team Alpha! Early market signals are highly bullish.")
            day3_gap_inserted = True
            msg_count += 2
            continue
            
        # Check for GT-05: on Day 4 (15/03/2026 afternoon), insert out-of-order message
        if curr >= datetime(2026, 3, 15, 14, 30) and not gt05_inserted:
            messages.append("15/03/2026, 14:35 - Rahul Patel: Did anyone face issue in withdrawal request?")
            # Out of order: timestamp 14:18 appears AFTER 14:35
            messages.append("15/03/2026, 14:18 - Vikram Sharma: System maintenance in progress for 15 mins.")
            gt05_inserted = True
            msg_count += 2
            curr = datetime(2026, 3, 15, 14, 40)
            continue
            
        # Normal chat generation
        step_min = random.randint(3, 15)
        curr += timedelta(minutes=step_min)
        
        # Skip late night quiet hours if not the gap night
        if curr.hour >= 23 or curr.hour < 7:
            if curr.hour >= 23:
                curr += timedelta(days=1)
            curr = curr.replace(hour=7, minute=random.randint(5, 25))
            continue
            
        ts_str = curr.strftime("%d/%m/%Y, %H:%M")
        
        # Pick Hinglish, Devanagari, or system media/deletion
        r = random.random()
        if r < 0.10:
            sender, text = random.choice(devanagari_lines)
            messages.append(f"{ts_str} - {sender}: {text}")
        elif r < 0.15:
            messages.append(f"{ts_str} - Vikram Sharma: <Media omitted>")
        elif r < 0.18:
            messages.append(f"{ts_str} - Rahul Patel: This message was deleted")
        else:
            sender, text = random.choice(hinglish_chatter)
            messages.append(f"{ts_str} - {sender}: {text}")
            
        msg_count += 1
        if msg_count > 620:
            break
            
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(messages) + "\n")
    print(f"Generated {len(messages)} messages in {out_path.name}")


def generate_whatsapp_1to1(out_path: Path):
    """Generate 1:1 chat between Meera and Vikram with 3 payment instructions."""
    messages = [
        "12/03/2026, 10:15 - Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.",
        "12/03/2026, 10:16 - Meera Iyer: Hello Vikram ji, I saw the group announcement. Want to know more about the scheme.",
        "12/03/2026, 10:18 - Vikram Sharma: Welcome Meera ji. We trade in algorithmic forex and crypto arbitrage. We guarantee fixed 15% weekly returns.",
        "12/03/2026, 10:20 - Meera Iyer: That sounds high. Is there any risk to principal amount?",
        "12/03/2026, 10:22 - Vikram Sharma: Zero risk ma'am. We have a reserve fund. You can start with trial amount of 50,000 INR.",
        "12/03/2026, 10:25 - Meera Iyer: Okay, let me try with 50k first.",
        "13/03/2026, 11:15 - Vikram Sharma: Good morning Meera ji. Are you ready for the initial tranche?",
        "13/03/2026, 11:20 - Meera Iyer: Yes, where should I transfer?",
        "13/03/2026, 11:22 - Vikram Sharma: Please transfer 50,000 INR to our treasury VPA: vikram.alpha@okaxis. Send me screenshot once done.",
        "13/03/2026, 11:31 - Meera Iyer: Done Vikram ji! Paid 50,000 to vikram.alpha@okaxis. Ref 607211001234.",
        "13/03/2026, 11:32 - Meera Iyer: <Media omitted>",
        "13/03/2026, 11:35 - Vikram Sharma: Received! Your position is activated. Daily credit will start from tomorrow.",
        "14/03/2026, 09:30 - Vikram Sharma: Meera ji, yesterday's trade made 22% profit. If you upgrade to Gold tier with 1,50,000 INR additional capital, you get VIP profit split.",
        "14/03/2026, 15:45 - Meera Iyer: I can arrange 1.5 Lakh today. Same UPI ID?",
        "14/03/2026, 16:00 - Vikram Sharma: Yes ma'am, pay 1,50,000 to vikram.alpha@okaxis immediately to lock current arbitrage slot.",
        "14/03/2026, 16:16 - Meera Iyer: Transferred 1,50,000 to vikram.alpha@okaxis just now. Transaction id 607311005678.",
        "14/03/2026, 16:20 - Vikram Sharma: Confirmed. Gold status active.",
        "15/03/2026, 00:50 - Vikram Sharma: Urgent opportunity Meera ji! Institutional block trade available. If you deposit 3,00,000 right now, your total returns double by Monday.",
        "15/03/2026, 01:05 - Meera Iyer: But it is 1 AM in the night! Can I do it in morning?",
        "15/03/2026, 01:10 - Vikram Sharma: Slot closes at 2 AM strictly. Don't miss this opportunity. Transfer to vikram.alpha@okaxis.",
        "15/03/2026, 01:21 - Meera Iyer: Okay, transferred 3,00,000 INR. UTR 607411009012. Please confirm.",
        "15/03/2026, 01:26 - Vikram Sharma: Got it. Congratulations on Platinum tier.",
        "16/03/2026, 12:00 - Meera Iyer: Vikram ji, I submitted a withdrawal request for 1,00,000 on website but it says pending.",
        "16/03/2026, 12:15 - Vikram Sharma: You need to pay 20% tax clearance fee first ma'am, 1,00,000 more required.",
        "16/03/2026, 12:20 - Meera Iyer: What tax? You never mentioned this earlier! Please refund my money.",
        "16/03/2026, 14:00 - Meera Iyer: Vikram ji please pick my call! Number is switched off.",
        "17/03/2026, 10:00 - Meera Iyer: I am lodging a cyber crime police complaint against you and this group.",
    ]
    
    # Pad to ~150 messages with contextual follow-ups
    padded_messages = []
    padded_messages.extend(messages[:10])
    for i in range(1, 45):
        padded_messages.append(f"12/03/2026, 14:{i:02d} - Meera Iyer: Asking query {i} regarding risk coverage.")
        padded_messages.append(f"12/03/2026, 14:{i+1:02d} - Vikram Sharma: Answering query {i}: All trades hedged in real-time.")
    padded_messages.extend(messages[10:])
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(padded_messages) + "\n")
    print(f"Generated {len(padded_messages)} messages in {out_path.name}")


def generate_bank_pdf_meera(out_path: Path):
    """Generate HDFC bank statement PDF for Meera Iyer with the 3 debits."""
    doc = SimpleDocTemplate(str(out_path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        "BankTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#004C8F"),
    )
    meta_style = ParagraphStyle("BankMeta", parent=styles["Normal"], fontSize=9, leading=12)
    
    story.append(Paragraph("<b>HDFC BANK LIMITED</b>", title_style))
    story.append(Paragraph("Account Statement | Savings Account", meta_style))
    story.append(Spacer(1, 10))
    
    info_data = [
        ["Account Holder:", "MEERA IYER", "Account Number:", "919000034455"],
        ["Customer ID:", "CUST-987214", "IFSC Code:", "HDFC0000123"],
        ["Branch:", "Aundh, Pune", "Currency:", "INR"],
        ["Statement Period:", "10/03/2026 to 17/03/2026", "Nomination:", "Registered"],
    ]
    info_table = Table(info_data, colWidths=[110, 160, 110, 160])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#333333")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Transactions table
    headers = ["Date", "Narration / Reference", "Chq/Ref No", "Debit (INR)", "Credit (INR)", "Balance (INR)"]
    rows = [
        ["10/03/2026", "OPENING BALANCE", "-", "-", "-", "5,75,000.00"],
        ["11/03/2026", "ACH/SALARY/INFOSYS LTD", "ACH8912", "-", "1,20,000.00", "6,95,000.00"],
        ["12/03/2026", "POS/SWIGGY/PUNE", "POS4412", "850.00", "-", "6,94,150.00"],
        ["13/03/2026", "UPI/DR/607211001234/vikram.alpha@okaxis/Wealth Club", "607211001234", "50,000.00", "-", "6,44,150.00"],
        ["14/03/2026", "UPI/DR/607311005678/vikram.alpha@okaxis/Alpha Tier2", "607311005678", "1,50,000.00", "-", "4,94,150.00"],
        ["15/03/2026", "UPI/DR/607411009012/vikram.alpha@okaxis/Alpha Final", "607411009012", "3,00,000.00", "-", "1,94,150.00"],
        ["16/03/2026", "ATM/WDL/AUNDH BRANCH", "ATM0092", "5,000.00", "-", "1,89,150.00"],
    ]
    
    table_data = [headers] + rows
    t = Table(table_data, colWidths=[55, 215, 70, 65, 65, 70])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#004C8F")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('ALIGN', (3,0), (5,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    
    doc.build(story)
    print(f"Generated Bank Statement PDF: {out_path.name}")


def generate_bank_pdf_mule_a(out_path: Path):
    """Generate PNB bank statement PDF for Mule A (Deepak Rawat).
    Contains:
      - GT-01: credited VPA vikram.alpha@okaxis matching WhatsApp chat.
      - GT-02: Funnel pattern (~90% forwarded within 40 mins to Accounts B and C).
      - GT-08: Broken running balance on row 8 (balance does not add up).
    """
    doc = SimpleDocTemplate(str(out_path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle("BankTitle", parent=styles["Heading1"], fontSize=16, leading=20, textColor=colors.HexColor("#A20000"))
    meta_style = ParagraphStyle("BankMeta", parent=styles["Normal"], fontSize=9, leading=12)
    
    story.append(Paragraph("<b>PUNJAB NATIONAL BANK</b>", title_style))
    story.append(Paragraph("Account Statement | Current Account", meta_style))
    story.append(Spacer(1, 10))
    
    info_data = [
        ["Account Holder:", "DEEPAK RAWAT", "Account Number:", "912345678901"],
        ["Customer ID:", "PNB-883912", "IFSC Code:", "PUNB0123456"],
        ["Branch:", "Noida Sector 18", "Linked VPA:", "vikram.alpha@okaxis"],
        ["Statement Period:", "12/03/2026 to 16/03/2026", "Status:", "Active"],
    ]
    info_table = Table(info_data, colWidths=[110, 160, 110, 160])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Transactions table
    # Row 1: Opening balance: 10,000.00
    # Row 2 (13/03 11:31): Credit 50,000 from Meera (VPA vikram.alpha@okaxis). Balance = 60,000.00
    # Row 3 (13/03 11:50): Forward debit 25,000 to Sunita Verma (Mule B 912345678902). Balance = 35,000.00
    # Row 4 (13/03 12:05): Forward debit 20,000 to Kabir Anand (Mule C 912345678903). Balance = 15,000.00 (Total 45k/50k = 90% in 34 mins)
    # Row 5 (14/03 16:17): Credit 1,50,000 from Meera. Balance = 1,65,000.00
    # Row 6 (14/03 16:45): Forward debit 70,000 to Sunita Verma (Mule B). Balance = 95,000.00
    # Row 7 (14/03 16:55): Forward debit 65,000 to Kabir Anand (Mule C). Balance = 30,000.00 (Total 135k/150k = 90% in 38 mins)
    # Row 8 (15/03 01:23): Credit 3,00,000 from Meera. Balance = 3,30,000.00
    # Row 9 (15/03 01:50): Forward debit 1,40,000 to Sunita Verma (Mule B). Correct balance = 1,90,000.00.
    #    *** GT-08: STATEMENT PRINTS 2,20,000.00 (BROKEN RUNNING BALANCE ARITHMETIC!) ***
    # Row 10 (15/03 02:02): Forward debit 1,30,000 to Kabir Anand (Mule C). Balance printed = 90,000.00
    headers = ["Date", "Narration / Reference", "Chq/Ref No", "Debit (INR)", "Credit (INR)", "Balance (INR)"]
    rows = [
        ["12/03/2026", "OPENING BALANCE", "-", "-", "-", "10,000.00"],
        ["13/03/2026", "UPI/CR/607211001234/vikram.alpha@okaxis/From Meera Iyer", "607211001234", "-", "50,000.00", "60,000.00"],
        ["13/03/2026", "IMPS/DR/60721199001/To Sunita Verma A/C 912345678902", "IMPS99001", "25,000.00", "-", "35,000.00"],
        ["13/03/2026", "IMPS/DR/60721199002/To Kabir Anand A/C 912345678903", "IMPS99002", "20,000.00", "-", "15,000.00"],
        ["14/03/2026", "UPI/CR/607311005678/vikram.alpha@okaxis/From Meera Iyer", "607311005678", "-", "1,50,000.00", "1,65,000.00"],
        ["14/03/2026", "IMPS/DR/60731199003/To Sunita Verma A/C 912345678902", "IMPS99003", "70,000.00", "-", "95,000.00"],
        ["14/03/2026", "IMPS/DR/60731199004/To Kabir Anand A/C 912345678903", "IMPS99004", "65,000.00", "-", "30,000.00"],
        ["15/03/2026", "UPI/CR/607411009012/vikram.alpha@okaxis/From Meera Iyer", "607411009012", "-", "3,00,000.00", "3,30,000.00"],
        ["15/03/2026", "IMPS/DR/60741199005/To Sunita Verma A/C 912345678902", "IMPS99005", "1,40,000.00", "-", "2,20,000.00"],  # Broken balance (should be 1,90,000.00)
        ["15/03/2026", "IMPS/DR/60741199006/To Kabir Anand A/C 912345678903", "IMPS99006", "1,30,000.00", "-", "90,000.00"],
    ]
    
    table_data = [headers] + rows
    t = Table(table_data, colWidths=[55, 215, 70, 65, 65, 70])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#A20000")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('ALIGN', (3,0), (5,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    
    doc.build(story)
    print(f"Generated Mule A Statement PDF (with broken balance): {out_path.name}")


def generate_bank_csv_mule_b(out_path: Path):
    """Generate CSV bank statement for Sunita Verma (Mule B)."""
    rows = [
        {"date": "12/03/2026", "narration": "OPENING BALANCE", "debit": 0.0, "credit": 0.0, "balance": 4500.0},
        {"date": "13/03/2026", "narration": "IMPS/CR/60721199001/Deepak Rawat/A/C 912345678901", "debit": 0.0, "credit": 25000.0, "balance": 29500.0},
        {"date": "13/03/2026", "narration": "ATM/CASH-WDL/DELHI LAJPAT NAGAR", "debit": 20000.0, "credit": 0.0, "balance": 9500.0},
        {"date": "14/03/2026", "narration": "IMPS/CR/60731199003/Deepak Rawat/A/C 912345678901", "debit": 0.0, "credit": 70000.0, "balance": 79500.0},
        {"date": "14/03/2026", "narration": "ATM/CASH-WDL/DELHI SOUTH EX", "debit": 50000.0, "credit": 0.0, "balance": 29500.0},
        {"date": "15/03/2026", "narration": "IMPS/CR/60741199005/Deepak Rawat/A/C 912345678901", "debit": 0.0, "credit": 140000.0, "balance": 169500.0},
        {"date": "15/03/2026", "narration": "NEFT/DR/CRYPTO-EXCHANGE-CASH", "debit": 130000.0, "credit": 0.0, "balance": 39500.0},
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "narration", "debit", "credit", "balance"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated Mule B CSV: {out_path.name}")


def generate_call_logs(out_path1: Path, out_path2: Path):
    """Generate call logs for Device 1 and Device 2.
    Plant:
      - GT-03: Device ID D1 appears in both call logs, used by Vikram and Support Desk.
      - GT-10: Call-log towers move from Noida to Jaipur between transfers.
    """
    fieldnames = ["timestamp", "direction", "number", "duration_sec", "cell_tower_id", "location_name", "device_id"]
    
    # Device 1: Used by Vikram (+91 90000 10001) and Support Desk (+91 90000 10002)
    # Starts in Noida (12-14 March), moves to Jaipur on 15 March
    rows1 = [
        {"timestamp": "2026-03-12 10:14:00", "direction": "OUTGOING", "number": "+91 90000 10003", "duration_sec": 145, "cell_tower_id": "TOW-NOI-042", "location_name": "Noida Sector 62", "device_id": "D1"},
        {"timestamp": "2026-03-12 11:30:00", "direction": "INCOMING", "number": "+91 90000 10004", "duration_sec": 210, "cell_tower_id": "TOW-NOI-042", "location_name": "Noida Sector 62", "device_id": "D1"},
        {"timestamp": "2026-03-13 11:10:00", "direction": "OUTGOING", "number": "+91 90000 10003", "duration_sec": 85, "cell_tower_id": "TOW-NOI-045", "location_name": "Noida Sector 18", "device_id": "D1"},
        {"timestamp": "2026-03-14 15:30:00", "direction": "INCOMING", "number": "+91 90000 10003", "duration_sec": 320, "cell_tower_id": "TOW-NOI-045", "location_name": "Noida Sector 18", "device_id": "D1"},
        # Movement to Jaipur on 15 March!
        {"timestamp": "2026-03-15 01:00:00", "direction": "OUTGOING", "number": "+91 90000 10003", "duration_sec": 190, "cell_tower_id": "TOW-JAI-108", "location_name": "Jaipur Malviya Nagar", "device_id": "D1"},
        {"timestamp": "2026-03-15 11:15:00", "direction": "INCOMING", "number": "+91 90000 10002", "duration_sec": 412, "cell_tower_id": "TOW-JAI-112", "location_name": "Jaipur C-Scheme", "device_id": "D1"},
        {"timestamp": "2026-03-16 10:00:00", "direction": "INCOMING", "number": "+91 90000 10003", "duration_sec": 0, "cell_tower_id": "TOW-JAI-112", "location_name": "Jaipur C-Scheme", "device_id": "D1"},
    ]
    
    # Device 2: Support Desk handset log, which also recorded calls from Device ID D1
    rows2 = [
        {"timestamp": "2026-03-12 09:15:00", "direction": "INCOMING", "number": "+91 90000 10001", "duration_sec": 305, "cell_tower_id": "TOW-NOI-042", "location_name": "Noida Sector 62", "device_id": "D1"},
        {"timestamp": "2026-03-13 14:20:00", "direction": "OUTGOING", "number": "+91 90000 10004", "duration_sec": 180, "cell_tower_id": "TOW-NOI-042", "location_name": "Noida Sector 62", "device_id": "D2"},
        {"timestamp": "2026-03-14 11:00:00", "direction": "INCOMING", "number": "+91 90000 10001", "duration_sec": 140, "cell_tower_id": "TOW-NOI-045", "location_name": "Noida Sector 18", "device_id": "D1"},
        {"timestamp": "2026-03-15 11:15:00", "direction": "OUTGOING", "number": "+91 90000 10001", "duration_sec": 412, "cell_tower_id": "TOW-DEL-009", "location_name": "Delhi Connaught Place", "device_id": "D2"},
    ]
    
    with open(out_path1, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows1)
        
    with open(out_path2, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows2)
        
    print(f"Generated Call Logs: {out_path1.name}, {out_path2.name}")


def generate_images(out_genuine: Path, out_edited: Path, out_reused_a: Path, out_reused_b: Path):
    """Generate synthetic images including:
      - Genuine payment screenshot (matches Meera statement)
      - GT-06: Edited screenshot with EXIF software, mod date > create date, and altered text block
      - GT-07: Reused media pair (PNG + re-saved JPEG) with matching perceptual hash
    """
    # 1. Genuine Payment Screenshot
    img_gen = Image.new("RGB", (400, 600), color=(248, 250, 252))
    draw = ImageDraw.Draw(img_gen)
    # Header bar
    draw.rectangle([0, 0, 400, 70], fill=(0, 128, 100))
    draw.text((20, 25), "UPI Payment Successful", fill=(255, 255, 255))
    # Card
    draw.rectangle([30, 100, 370, 360], fill=(255, 255, 255), outline=(220, 226, 230), width=2)
    draw.text((50, 130), "Paid to:", fill=(100, 100, 100))
    draw.text((50, 155), "Vikram Sharma", fill=(20, 20, 20))
    draw.text((50, 180), "vikram.alpha@okaxis", fill=(70, 70, 70))
    draw.text((50, 220), "Amount: INR 50,000.00", fill=(0, 100, 50))
    draw.text((50, 260), "Ref No: 607211001234", fill=(100, 100, 100))
    draw.text((50, 290), "Date: 13 Mar 2026, 11:30 AM", fill=(100, 100, 100))
    img_gen.save(out_genuine)
    print(f"Generated Genuine Screenshot: {out_genuine.name}")
    
    # 2. GT-06: Edited Withdrawal Screenshot
    img_edit = Image.new("RGB", (400, 600), color=(240, 244, 248))
    draw_e = ImageDraw.Draw(img_edit)
    # App header
    draw_e.rectangle([0, 0, 400, 70], fill=(25, 40, 65))
    draw_e.text((20, 25), "Alpha Wealth Club Portal", fill=(255, 255, 255))
    # Original content background
    draw_e.rectangle([30, 100, 370, 400], fill=(255, 255, 255), outline=(200, 210, 220), width=2)
    draw_e.text((50, 130), "Withdrawal Status: APPROVED", fill=(30, 140, 60))
    draw_e.text((50, 170), "Original Beneficiary: Meera Iyer", fill=(40, 40, 40))
    # Altered amount box (tampered block with high compression / color difference)
    draw_e.rectangle([45, 215, 355, 275], fill=(255, 235, 230), outline=(230, 80, 60), width=2)
    draw_e.text((55, 235), "Amount: INR 12,50,000.00", fill=(200, 20, 20))  # Edited amount!
    draw_e.text((50, 310), "Txn Hash: 0x88f4b1029c9e", fill=(120, 120, 120))
    draw_e.text((50, 340), "Timestamp: 15-03-2026 14:00:00", fill=(120, 120, 120))
    
    # Create native EXIF with editor metadata and mod date > create date
    exif = img_edit.getexif()
    exif[0x0131] = "PixelMod Editor Pro v2.4"  # Software
    exif[0x0132] = "2026:03:16 09:30:00"      # DateTime (modified)
    
    # 0x8769 is ExifOffset IFD
    try:
        exif_ifd = exif.get_ifd(0x8769)
        exif_ifd[0x9003] = "2026:03:15 14:00:00"  # DateTimeOriginal (created)
        exif_ifd[0x9004] = "2026:03:15 14:00:00"  # DateTimeDigitized
    except Exception:
        pass
        
    out_edited_jpg = out_edited.with_suffix(".jpg")
    img_edit.save(out_edited, "PNG")
    img_edit.save(out_edited_jpg, "JPEG", exif=exif, quality=95)
    print(f"Generated Edited Screenshot: {out_edited.name} & {out_edited_jpg.name}")
    
    # 3. GT-07: Reused Image Pair (Certificate / Promotion graphic)
    img_promo = Image.new("RGB", (450, 300), color=(18, 30, 49))
    draw_p = ImageDraw.Draw(img_promo)
    draw_p.rectangle([15, 15, 435, 285], outline=(212, 175, 55), width=3)
    draw_p.text((80, 60), "ALPHA WEALTH CLUB", fill=(212, 175, 55))
    draw_p.text((100, 110), "GUARANTEED 15% WEEKLY RETURN", fill=(255, 255, 255))
    draw_p.text((120, 150), "OFFICIAL CERTIFICATE", fill=(180, 200, 220))
    draw_p.text((130, 200), "VERIFIED BY ARBITRAGE POOL", fill=(100, 200, 120))
    
    img_promo.save(out_reused_a, "PNG")
    # Re-save as JPEG with 85 quality (same image, compressed) -> perceptual hash match
    img_promo.save(out_reused_b, "JPEG", quality=85)
    print(f"Generated Reused Image Pair: {out_reused_a.name}, {out_reused_b.name}")


def generate_ground_truth(out_path: Path):
    """Generate ground_truth.json containing all planted facts GT-01 to GT-10."""
    gt_data = {
        "case_id": CASE_ID,
        "title": CASE_TITLE,
        "synthetic_notice": "Synthetic case. All persons and identifiers are fictional.",
        "planted_facts": [
            {
                "id": "GT-01",
                "name": "Cross-Source Identifier Link",
                "description": "UPI ID vikram.alpha@okaxis appears in WhatsApp chat and as credited VPA in Mule A bank statement.",
                "type": "SAME_IDENTIFIER",
                "identifier": "vikram.alpha@okaxis",
                "sources": ["whatsapp_group_alpha_wealth.txt", "whatsapp_chat_meera_vikram.txt", "bank_statement_mule_A.pdf"],
                "tier": "LEAD",
                "basis": "exact_identifier",
            },
            {
                "id": "GT-02",
                "name": "Mule Funnel Pattern",
                "description": "Mule A forwards ~90% of each incoming credit to Mule B and Mule C within 40 minutes.",
                "type": "PATTERN_FUNNEL",
                "mule_account": "912345678901",
                "forwarding_accounts": ["912345678902", "912345678903"],
                "forwarding_ratio_min": 0.85,
                "window_minutes": 40,
                "sources": ["bank_statement_mule_A.pdf", "bank_statement_mule_B.csv"],
                "tier": "LEAD",
            },
            {
                "id": "GT-03",
                "name": "Shared Device Identifier",
                "description": "Device ID D1 appears in both call logs, shared by Vikram (+91 90000 10001) and Support Desk (+91 90000 10002).",
                "type": "SAME_DEVICE",
                "device_id": "D1",
                "numbers": ["+91 90000 10001", "+91 90000 10002"],
                "sources": ["call_log_device1.csv", "call_log_device2.csv"],
                "tier": "LEAD",
            },
            {
                "id": "GT-04",
                "name": "Chat Timeline Gap",
                "description": "A 6h 14m silence gap in the WhatsApp group chat on night 3 (14/03/2026 23:45 to 15/03/2026 05:59).",
                "type": "ANOMALY_CHAT_GAP",
                "source": "whatsapp_group_alpha_wealth.txt",
                "gap_duration_minutes": 374,
                "gap_start": "2026-03-14 23:45",
                "gap_end": "2026-03-15 05:59",
                "severity": "HIGH",
            },
            {
                "id": "GT-05",
                "name": "Out-of-Order Timestamp",
                "description": "A message at 14:18 appears after a message timestamped 14:35 on 15/03/2026 in the group chat.",
                "type": "ANOMALY_OUT_OF_ORDER",
                "source": "whatsapp_group_alpha_wealth.txt",
                "preceding_time": "15/03/2026 14:35",
                "failing_time": "15/03/2026 14:18",
                "severity": "MEDIUM",
            },
            {
                "id": "GT-06",
                "name": "Edited Screenshot Metadata & ELA Indicator",
                "description": "Withdrawal screenshot has EXIF Software tag 'PixelMod Editor Pro v2.4', modified later than created, with localized editing artifacts.",
                "type": "ANOMALY_IMAGE_EDITED",
                "source": "screenshot_withdrawal_edited.jpg",
                "software_tag": "PixelMod Editor Pro v2.4",
                "created_time": "2026:03:15 14:00:00",
                "modified_time": "2026:03:16 09:30:00",
                "severity": "HIGH",
            },
            {
                "id": "GT-07",
                "name": "Reused Media Across Conversations",
                "description": "Identical promotion certificate image sent in two different formats (PNG and compressed JPEG) with perceptual hash distance <= 2.",
                "type": "ANOMALY_REUSED_MEDIA",
                "sources": ["screenshot_reused_a.png", "screenshot_reused_b.jpg"],
                "phash_max_distance": 2,
                "severity": "MEDIUM",
            },
            {
                "id": "GT-08",
                "name": "Bank Statement Balance Arithmetic Discrepancy",
                "description": "Mule A bank statement row 8 has broken running balance (printed 2,20,000.00 vs expected 1,90,000.00).",
                "type": "ANOMALY_BALANCE_MISMATCH",
                "source": "bank_statement_mule_A.pdf",
                "failing_row_index": 8,
                "expected_balance": 190000.0,
                "found_balance": 220000.0,
                "severity": "HIGH",
            },
            {
                "id": "GT-09",
                "name": "Fuzzy Name Variant Resolution",
                "description": "Variants 'Vikram Sharma', 'Vikram Sharma Ji', and 'विक्रम शर्मा' resolve to the same person as a LEAD edge.",
                "type": "SAME_PERSON_FUZZY",
                "variants": ["Vikram Sharma", "Vikram Sharma Ji", "विक्रम शर्मा"],
                "target_entity": "Vikram Sharma",
                "tier": "LEAD",
            },
            {
                "id": "GT-10",
                "name": "Spatial Cell Tower Movement",
                "description": "Call logs record cell tower movement from Noida Sector 62 (TOW-NOI-042) to Jaipur Malviya Nagar (TOW-JAI-108) between transfers.",
                "type": "SPATIAL_THREAD",
                "locations": ["Noida Sector 62", "Jaipur Malviya Nagar"],
                "tower_ids": ["TOW-NOI-042", "TOW-JAI-108"],
                "sources": ["call_log_device1.csv", "call_log_device2.csv"],
                "tier": "LEAD",
            },
        ],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(gt_data, f, indent=2, ensure_ascii=False)
    print(f"Generated Ground Truth JSON: {out_path.name}")


def main():
    target_dir = setup_dir()
    print(f"Generating synthetic forensic dataset for {CASE_ID} into {target_dir}...")
    
    generate_whatsapp_group(target_dir / "whatsapp_group_alpha_wealth.txt")
    generate_whatsapp_1to1(target_dir / "whatsapp_chat_meera_vikram.txt")
    generate_bank_pdf_meera(target_dir / "bank_statement_meera.pdf")
    generate_bank_pdf_mule_a(target_dir / "bank_statement_mule_A.pdf")
    generate_bank_csv_mule_b(target_dir / "bank_statement_mule_B.csv")
    generate_call_logs(target_dir / "call_log_device1.csv", target_dir / "call_log_device2.csv")
    generate_images(
        target_dir / "screenshot_payment_genuine.png",
        target_dir / "screenshot_withdrawal_edited.png",
        target_dir / "screenshot_reused_a.png",
        target_dir / "screenshot_reused_b.jpg",
    )
    generate_ground_truth(target_dir / "ground_truth.json")
    print(f"\n[DONE] Synthetic dataset generation completed successfully. All 10 planted facts generated.")


if __name__ == "__main__":
    main()
