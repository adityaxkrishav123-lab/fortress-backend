"""
OUTPUT FORMATTER — Multi-Format Export Engine
=============================================
Converts validated operational data + encrypted PII into three outputs:

1. CSV / Excel (for the NGO user):
   - All operational columns: category, item_type, quantity, urgency
   - PII columns present but shown as [ENCRYPTED]
   - User decrypts locally on their device via the Flutter app

2. AI Agent JSON (for internal dispatch/connectors):
   - PII fields completely stripped — AI agents never see [ENCRYPTED] either
   - Only: category, item_type, quantity, urgency, urgency_breakdown
   - This is the clean feed for NGO-connector, volunteer matcher, etc.

3. PDF Summary (human-readable report):
   - Date, parse_id, item count, top urgency breakdown
   - Suitable for WhatsApp sharing, print, or official filing
"""

import io
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("OutputFormatter")

# Optional dependency flags
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


class OutputFormatter:
    """
    Converts parser output into multiple user-ready and AI-ready formats.
    All PII is shown as [ENCRYPTED] in exported files.
    AI agents receive a fully stripped clean feed.
    """

    # -------------------------------------------------------
    # CSV / EXCEL EXPORT (User-facing)
    # -------------------------------------------------------
    def to_csv(self, validated_data: list, encrypted_pii: dict, parse_id: str) -> bytes:
        """
        Produces a CSV file for the NGO user.
        PII columns included but values shown as [ENCRYPTED].
        User decrypts on their device via the Flutter app.

        Args:
            validated_data: list of dicts from _normalize_and_validate()
            encrypted_pii: {encrypted_blob, salt, nonce} from EncryptionManager
            parse_id: trace ID from the parser run

        Returns:
            bytes — ready to save as .csv or send to device
        """
        if not PANDAS_AVAILABLE:
            raise RuntimeError("pandas required for CSV export. Run: pip install pandas")

        rows = []
        for item in validated_data:
            rows.append({
                "parse_id":           parse_id,
                "category":           item.get("category", ""),
                "item_type":          item.get("item_type", ""),
                "quantity":           item.get("quantity", 0),
                "urgency":            item.get("urgency", ""),
                "is_uncertain":       item.get("is_uncertain", False),
                "review_stage":       item.get("review_stage", 1),
                "stage1_approved":    item.get("stage1_approved", False),
                "stage2_confirmed":   item.get("stage2_confirmed", False),
                "dispatch_locked":    item.get("dispatch_locked", True),
                # PII columns — shown as ******1234, decryptable by user only
                "donor_info":         "******1234" if encrypted_pii.get("encrypted_blob") else "N/A",
                "contact_details":    "******1234" if encrypted_pii.get("encrypted_blob") else "N/A",
                "pii_salt":           encrypted_pii.get("salt", ""),
                "pii_nonce":          encrypted_pii.get("nonce", ""),
                "pii_blob":           encrypted_pii.get("encrypted_blob", ""),
                "export_timestamp":   datetime.utcnow().isoformat() + "Z"
            })

        df = pd.DataFrame(rows)
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')  # utf-8-sig for Excel compatibility
        logger.info(f"OutputFormatter: CSV export — {len(rows)} rows, parse_id={parse_id}")
        return output.getvalue()

    def to_excel(self, validated_data: list, encrypted_pii: dict, parse_id: str) -> bytes:
        """
        Produces an Excel file (.xlsx) for the NGO user.
        Same structure as CSV but with formatting.
        """
        if not PANDAS_AVAILABLE:
            raise RuntimeError("pandas required for Excel export. Run: pip install pandas openpyxl")

        rows = []
        for item in validated_data:
            rows.append({
                "Parse ID":           parse_id,
                "Category":           item.get("category", ""),
                "Item Type":          item.get("item_type", ""),
                "Quantity":           item.get("quantity", 0),
                "Urgency":            item.get("urgency", ""),
                "Uncertain?":         item.get("is_uncertain", False),
                "Review Stage":       item.get("review_stage", 1),
                "Stage 1 Approved":   item.get("stage1_approved", False),
                "Stage 2 Confirmed":  item.get("stage2_confirmed", False),
                "Dispatch Locked":    item.get("dispatch_locked", True),
                "Donor Info":         "******1234" if encrypted_pii.get("encrypted_blob") else "N/A",
                "Contact Details":    "******1234" if encrypted_pii.get("encrypted_blob") else "N/A",
                "PII Salt":           encrypted_pii.get("salt", ""),
                "PII Nonce":          encrypted_pii.get("nonce", ""),
                "PII Blob":           encrypted_pii.get("encrypted_blob", ""),
                "Exported At":        datetime.utcnow().isoformat() + "Z"
            })

        df = pd.DataFrame(rows)
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Relief Needs')

            # Apply basic formatting
            workbook = writer.book
            worksheet = writer.sheets['Relief Needs']
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or "")) for cell in col) + 4
                worksheet.column_dimensions[col[0].column_letter].width = min(max_len, 40)

        logger.info(f"OutputFormatter: Excel export — {len(rows)} rows, parse_id={parse_id}")
        return output.getvalue()

    # -------------------------------------------------------
    # AI AGENT FEED (Internal — PII completely stripped)
    # -------------------------------------------------------
    def to_ai_feed(self, validated_data: list, parse_id: str) -> list:
        """
        Returns clean operational JSON for AI agents.
        PII is COMPLETELY absent — not even [ENCRYPTED] placeholders.
        AI agents only see what they need for dispatch decisions.

        Returns:
            list of dicts — the AI-clean operational feed
        """
        ai_feed = []
        for item in validated_data:
            ai_feed.append({
                "parse_id":         parse_id,
                "category":         item.get("category"),
                "item_type":        item.get("item_type"),
                "quantity":         item.get("quantity"),
                "urgency":          item.get("urgency"),
                "urgency_breakdown": item.get("urgency_breakdown", {}),
                "is_uncertain":     item.get("is_uncertain", False),
                # Double-confirmation state — dispatch agents check this before acting
                "stage1_approved":  item.get("stage1_approved", False),
                "stage2_confirmed": item.get("stage2_confirmed", False),
                "dispatch_locked":  item.get("dispatch_locked", True),
                # No donor_info, no contact_details, no PII blobs
            })

        logger.info(f"OutputFormatter: AI feed — {len(ai_feed)} items, parse_id={parse_id}")
        return ai_feed

    # -------------------------------------------------------
    # PDF SUMMARY (Human-readable report)
    # -------------------------------------------------------
    def to_pdf(self, validated_data: list, parse_id: str, org_name: str = "NGO") -> bytes:
        """
        Produces a PDF summary report.
        Suitable for WhatsApp sharing, printing, or official filing.
        No PII included — operational summary only.

        Returns:
            bytes — ready to save as .pdf
        """
        if not FPDF_AVAILABLE:
            # Fallback: produce a simple plain-text "PDF" as bytes
            logger.warning("fpdf2 not installed. Producing plain text report.")
            return self._text_fallback_report(validated_data, parse_id, org_name)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Header
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Disaster Relief Needs Report", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Organisation: {org_name}", ln=True, align="C")
        pdf.cell(0, 6, f"Parse ID: {parse_id}", ln=True, align="C")
        pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True, align="C")
        pdf.ln(8)

        # Summary counts
        critical = sum(1 for i in validated_data if i.get("urgency") == "critical")
        essential = sum(1 for i in validated_data if i.get("urgency") == "essential")
        support = sum(1 for i in validated_data if i.get("urgency") == "support")
        uncertain = sum(1 for i in validated_data if i.get("is_uncertain"))

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Summary", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Total Line Items: {len(validated_data)}", ln=True)
        pdf.cell(0, 6, f"Critical: {critical}  |  Essential: {essential}  |  Support: {support}", ln=True)
        if uncertain:
            pdf.cell(0, 6, f"Flagged for Review (uncertain): {uncertain}", ln=True)
        pdf.ln(6)

        # Items table header
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(50, 7, "Category", border=1, fill=True)
        pdf.cell(60, 7, "Item Type", border=1, fill=True)
        pdf.cell(25, 7, "Quantity", border=1, fill=True)
        pdf.cell(35, 7, "Urgency", border=1, fill=True)
        pdf.cell(20, 7, "Review?", border=1, fill=True, ln=True)

        # Items rows
        pdf.set_font("Helvetica", "", 9)
        for item in validated_data:
            urgency = item.get("urgency", "")
            if urgency == "critical":
                pdf.set_text_color(180, 0, 0)
            elif urgency == "essential":
                pdf.set_text_color(180, 100, 0)
            else:
                pdf.set_text_color(0, 0, 0)

            pdf.cell(50, 6, str(item.get("category", ""))[:25], border=1)
            pdf.cell(60, 6, str(item.get("item_type", ""))[:30], border=1)
            pdf.cell(25, 6, str(item.get("quantity", "")), border=1)
            pdf.cell(35, 6, urgency.upper(), border=1)
            pdf.cell(20, 6, "YES" if item.get("is_uncertain") else "No", border=1, ln=True)

        pdf.set_text_color(0, 0, 0)
        pdf.ln(8)

        # Footer disclaimer
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 5,
            "NOTICE: This report contains operational data only. All personally identifiable "
            "information (PII) including donor names, contacts, and addresses has been "
            "encrypted and is only accessible to authorised NGO personnel via the app. "
            "AI dispatch agents do not have access to any PII."
        )

        logger.info(f"OutputFormatter: PDF export — {len(validated_data)} items, parse_id={parse_id}")
        return bytes(pdf.output())

    def _text_fallback_report(self, validated_data: list, parse_id: str, org_name: str) -> bytes:
        """Plain text fallback if fpdf2 is not installed."""
        lines = [
            "DISASTER RELIEF NEEDS REPORT",
            f"Organisation: {org_name}",
            f"Parse ID: {parse_id}",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            "=" * 60,
        ]
        for item in validated_data:
            lines.append(
                f"[{item.get('urgency','').upper()}] "
                f"{item.get('category','')} / {item.get('item_type','')} "
                f"x{item.get('quantity','')}"
                f"{'  ⚠ UNCERTAIN' if item.get('is_uncertain') else ''}"
            )
        lines.append("=" * 60)
        lines.append("NOTE: PII encrypted. Not shown in this report.")
        return "\n".join(lines).encode('utf-8')

    # -------------------------------------------------------
    # COMPLETE PACKAGE — All formats at once
    # -------------------------------------------------------
    def build_complete_package(
        self,
        validated_data: list,
        encrypted_pii: dict,
        parse_id: str,
        org_name: str = "NGO"
    ) -> dict:
        """
        Builds all three output formats in one call.

        Returns:
            {
                "ai_feed": list,        → for internal AI agents
                "csv_bytes": bytes,     → for user download / device storage
                "excel_bytes": bytes,   → for user download / device storage
                "pdf_bytes": bytes,     → for sharing / printing
                "parse_id": str
            }
        """
        result = {
            "parse_id": parse_id,
            "ai_feed": self.to_ai_feed(validated_data, parse_id),
        }

        try:
            result["csv_bytes"] = self.to_csv(validated_data, encrypted_pii, parse_id)
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            result["csv_bytes"] = None

        try:
            result["excel_bytes"] = self.to_excel(validated_data, encrypted_pii, parse_id)
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            result["excel_bytes"] = None

        try:
            result["pdf_bytes"] = self.to_pdf(validated_data, parse_id, org_name)
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            result["pdf_bytes"] = None

        return result
