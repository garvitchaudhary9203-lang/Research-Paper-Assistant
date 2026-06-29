import os
import csv
import json
import logging
import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from utils.citations import CitationsGenerator

logger = logging.getLogger("app")

class ExportService:
    def __init__(self, export_dir: str):
        self.export_dir = export_dir
        self._init_styles()

    def _init_styles(self) -> None:
        """Initialize beautiful custom ReportLab styles for high-fidelity PDF documents."""
        self.styles = getSampleStyleSheet()
        
        # Primary Color Theme: Slate & Purple Accent
        primary_color = colors.HexColor("#4F46E5") # Electric Indigo
        text_color = colors.HexColor("#1F2937") # Charcoal
        
        # Modify existing or create new Paragraph Styles
        self.title_style = ParagraphStyle(
            'DocTitle',
            parent=self.styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=primary_color,
            spaceAfter=15
        )
        
        self.h1_style = ParagraphStyle(
            'DocH1',
            parent=self.styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True
        )

        self.h2_style = ParagraphStyle(
            'DocH2',
            parent=self.styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#374151"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )

        self.body_style = ParagraphStyle(
            'DocBody',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_color,
            spaceAfter=6
        )

        self.code_style = ParagraphStyle(
            'DocCode',
            parent=self.styles['Code'],
            fontName='Courier',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#111827"),
            backColor=colors.HexColor("#F3F4F6"),
            borderPadding=6,
            spaceAfter=8
        )

        self.meta_style = ParagraphStyle(
            'DocMeta',
            parent=self.body_style,
            fontName='Helvetica-Oblique',
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=10
        )

    def _build_pdf(self, file_path: str, story: list) -> None:
        """Helper to build standard Letter sized PDF with basic margins."""
        try:
            doc = SimpleDocTemplate(
                file_path,
                pagesize=letter,
                leftMargin=54, # 0.75 in
                rightMargin=54,
                topMargin=54,
                bottomMargin=54
            )
            doc.build(story)
            logger.info(f"PDF successfully exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise e

    # --- Export Single Paper Summary ---
    def export_summary_pdf(self, paper_metadata: Dict[str, Any], filename: str) -> str:
        """Generates a professional PDF containing a research paper summary."""
        file_path = os.path.join(self.export_dir, filename)
        story = []

        # Document Header
        story.append(Paragraph("Research Paper Executive Summary", self.title_style))
        story.append(Paragraph(f"Paper: {paper_metadata.get('name', 'Unknown')}", self.h1_style))
        
        # Meta info
        meta_text = (
            f"<b>Title:</b> {paper_metadata.get('title', 'N/A')}<br/>"
            f"<b>Authors:</b> {paper_metadata.get('authors', 'N/A')}<br/>"
            f"<b>DOI:</b> {paper_metadata.get('doi', 'N/A')} | "
            f"<b>Year:</b> {paper_metadata.get('pub_year', 'N/A')}"
        )
        story.append(Paragraph(meta_text, self.meta_style))
        story.append(Spacer(1, 10))

        # Parse Summary Json
        summary_str = paper_metadata.get("summary_json", "{}")
        try:
            summary = json.loads(summary_str) if summary_str else {}
        except Exception:
            summary = {}

        sections = [
            ("Executive Summary", summary.get("executive_summary", "Not generated yet.")),
            ("Main Objective", summary.get("objective", "Not generated yet.")),
            ("Methodology", summary.get("methodology", "Not generated yet.")),
            ("Results & Findings", summary.get("results", "Not generated yet.")),
            ("Conclusion", summary.get("conclusion", "Not generated yet."))
        ]

        for heading, content in sections:
            story.append(Paragraph(heading, self.h2_style))
            story.append(Paragraph(content, self.body_style))
            story.append(Spacer(1, 6))

        # Contributions, Limitations, Future
        if "contributions" in summary:
            story.append(Paragraph("Key Contributions", self.h2_style))
            for i, c in enumerate(summary["contributions"]):
                story.append(Paragraph(f"<b>Contribution {i+1}:</b> {c}", self.body_style))
            story.append(Spacer(1, 6))

        if "limitations" in summary:
            story.append(Paragraph("Limitations", self.h2_style))
            for k, v in summary["limitations"].items():
                story.append(Paragraph(f"<b>{k.replace('_', ' ').title()}:</b> {v}", self.body_style))
            story.append(Spacer(1, 6))

        if "future_work" in summary:
            story.append(Paragraph("Future Directions", self.h2_style))
            for k, v in summary["future_work"].items():
                story.append(Paragraph(f"<b>{k.replace('_', ' ').title()}:</b> {v}", self.body_style))
            story.append(Spacer(1, 6))

        # Citation section
        story.append(Spacer(1, 10))
        story.append(Paragraph("APA Citation", self.h2_style))
        story.append(Paragraph(CitationsGenerator.to_apa(paper_metadata), self.body_style))

        self._build_pdf(file_path, story)
        return file_path

    # --- Export Paper Comparison ---
    def export_comparison_pdf(self, comparison_record: Dict[str, Any], papers: List[Dict[str, Any]], filename: str) -> str:
        """Generates a PDF displaying side-by-side paper comparisons and analysis synthesis."""
        file_path = os.path.join(self.export_dir, filename)
        story = []

        story.append(Paragraph("Research Paper Comparative Report", self.title_style))
        story.append(Paragraph(f"Created on: {comparison_record.get('created_at', '')[:10]}", self.meta_style))
        story.append(Spacer(1, 10))

        # List papers
        story.append(Paragraph("Papers Compared", self.h1_style))
        for p in papers:
            title = p.get("title") if p.get("title") else p.get("name")
            authors = p.get("authors", "Unknown")
            story.append(Paragraph(f"• <b>{title}</b> - {authors} ({p.get('pub_year', 'N/A')})", self.body_style))
        story.append(Spacer(1, 10))

        # Comparison Grid Table
        comp_data = comparison_record.get("comparison_data", {})
        
        # Build Table Data
        # Columns: Criterion, Paper 1, Paper 2, ...
        headers = ["Criterion"] + [p.get("name")[:25] + "..." if len(p.get("name", "")) > 25 else p.get("name", "") for p in papers]
        table_rows = [headers]

        criteria = [
            ("Research Problem", "research_problem"),
            ("Methodology", "methodology"),
            ("Dataset", "dataset"),
            ("Results", "results"),
            ("Contributions", "contributions"),
            ("Limitations", "limitations")
        ]

        # In comp_data, the structure is usually: {paper_id: {criterion: text}}
        for title, key in criteria:
            row = [Paragraph(f"<b>{title}</b>", self.body_style)]
            for p in papers:
                p_id = p.get("id")
                content = comp_data.get(p_id, {}).get(key, "N/A")
                row.append(Paragraph(content, self.body_style))
            table_rows.append(row)

        # Set up ReportLab table width calculations
        col_width = 480 / len(headers)
        col_widths = [col_width] * len(headers)
        
        comp_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E5E7EB")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        
        story.append(comp_table)
        story.append(Spacer(1, 15))

        # AI Synthesis Sections
        if "synthesis" in comp_data:
            story.append(Paragraph("AI Comparative Synthesis", self.h1_style))
            story.append(Paragraph(comp_data["synthesis"].get("analysis", ""), self.body_style))
            story.append(Spacer(1, 10))

            story.append(Paragraph("Common Strengths", self.h2_style))
            story.append(Paragraph(comp_data["synthesis"].get("strengths", "N/A"), self.body_style))
            story.append(Spacer(1, 6))

            story.append(Paragraph("Common Weaknesses & Gaps", self.h2_style))
            story.append(Paragraph(comp_data["synthesis"].get("weaknesses", "N/A"), self.body_style))
            story.append(Spacer(1, 6))

        self._build_pdf(file_path, story)
        return file_path

    # --- Export Chat Transcript ---
    def export_chat_pdf(self, session_name: str, history: List[Dict[str, Any]], filename: str) -> str:
        """Generates a PDF transcribing chatbot conversation logs."""
        file_path = os.path.join(self.export_dir, filename)
        story = []

        story.append(Paragraph("Research Chat Conversation Transcript", self.title_style))
        story.append(Paragraph(f"Session Name: {session_name}", self.h1_style))
        story.append(Spacer(1, 15))

        for msg in history:
            role_label = "RESEARCH ASSISTANT" if msg["role"] == "assistant" else "USER"
            role_color = "#4F46E5" if msg["role"] == "assistant" else "#0F172A"
            
            # Message bubble header
            role_style = ParagraphStyle(
                'ChatRole',
                parent=self.body_style,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor(role_color),
                spaceBefore=8,
                spaceAfter=2
            )
            story.append(Paragraph(role_label, role_style))
            
            # Content
            content_text = msg["content"]
            story.append(Paragraph(content_text, self.body_style))
            
            # Citations (if present)
            citations_str = msg.get("citations_json", "[]")
            try:
                citations = json.loads(citations_str) if citations_str else []
                if citations:
                    cit_style = ParagraphStyle(
                        'CitText',
                        parent=self.body_style,
                        fontName='Helvetica-Oblique',
                        textColor=colors.HexColor("#4B5563"),
                        leftIndent=15,
                        spaceBefore=4
                    )
                    story.append(Paragraph("Citations:", ParagraphStyle('CitHeader', parent=cit_style, fontName='Helvetica-Bold')))
                    for cit in citations:
                        story.append(Paragraph(f"• {cit['paper_name']} (Page {cit['page_number']})", cit_style))
            except Exception:
                pass
                
            story.append(Spacer(1, 8))

        self._build_pdf(file_path, story)
        return file_path

    # --- Export Full Research Report ---
    def export_full_report_pdf(self, project_name: str, papers: List[Dict[str, Any]], comparisons: List[Dict[str, Any]], filename: str) -> str:
        """Generates a complete multi-chapter PDF Research Report."""
        file_path = os.path.join(self.export_dir, filename)
        story = []

        # Title Page
        story.append(Spacer(1, 100))
        story.append(Paragraph(f"Comprehensive Research Project Report", ParagraphStyle('CoverTitle', parent=self.title_style, fontSize=28, leading=34, alignment=1)))
        story.append(Paragraph(f"Workspace: {project_name}", ParagraphStyle('CoverSub', parent=self.h1_style, alignment=1)))
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ParagraphStyle('CoverDate', parent=self.meta_style, alignment=1)))
        story.append(PageBreak())

        # Chapter 1: Uploaded Papers & Summaries
        story.append(Paragraph("Chapter 1: Indexed Publications", self.title_style))
        story.append(Spacer(1, 10))
        
        for idx, p in enumerate(papers):
            story.append(Paragraph(f"1.{idx+1} Summary: {p.get('name')}", self.h1_style))
            
            meta_text = (
                f"<b>Title:</b> {p.get('title', 'N/A')}<br/>"
                f"<b>Authors:</b> {p.get('authors', 'N/A')}<br/>"
                f"<b>Year:</b> {p.get('pub_year', 'N/A')} | <b>DOI:</b> {p.get('doi', 'N/A')}"
            )
            story.append(Paragraph(meta_text, self.meta_style))
            
            # Add summary details
            summary_str = p.get("summary_json", "{}")
            try:
                summary = json.loads(summary_str) if summary_str else {}
            except Exception:
                summary = {}
                
            sections = [
                ("Objective", summary.get("objective", "N/A")),
                ("Methodology", summary.get("methodology", "N/A")),
                ("Results & Findings", summary.get("results", "N/A")),
                ("Conclusion", summary.get("conclusion", "N/A"))
            ]
            for h, c in sections:
                story.append(Paragraph(h, self.h2_style))
                story.append(Paragraph(c, self.body_style))
                
            story.append(Spacer(1, 15))
            
        story.append(PageBreak())

        # Chapter 2: Comparative Summaries
        if comparisons:
            story.append(Paragraph("Chapter 2: Comparative Synthesis", self.title_style))
            story.append(Spacer(1, 10))
            
            for idx, c in enumerate(comparisons):
                story.append(Paragraph(f"2.{idx+1} Comparative Matrix", self.h1_style))
                comp_data = c.get("comparison_data", {})
                
                if "synthesis" in comp_data:
                    story.append(Paragraph("AI Analysis Synthesizer", self.h2_style))
                    story.append(Paragraph(comp_data["synthesis"].get("analysis", ""), self.body_style))
                    story.append(Spacer(1, 10))
                    
                    story.append(Paragraph("Shared Strengths", self.h2_style))
                    story.append(Paragraph(comp_data["synthesis"].get("strengths", ""), self.body_style))
                    story.append(Spacer(1, 6))
                    
                    story.append(Paragraph("Shared Limitations", self.h2_style))
                    story.append(Paragraph(comp_data["synthesis"].get("weaknesses", ""), self.body_style))
                    
                story.append(Spacer(1, 15))
            story.append(PageBreak())

        # Chapter 3: Citations Bibliography
        story.append(Paragraph("Chapter 3: Bibliography References", self.title_style))
        story.append(Spacer(1, 15))
        for idx, p in enumerate(papers):
            bib = CitationsGenerator.to_apa(p)
            story.append(Paragraph(f"[{idx+1}] {bib}", self.body_style))
            story.append(Spacer(1, 8))

        self._build_pdf(file_path, story)
        return file_path

    # --- Export Analytics CSV ---
    def export_analytics_csv(self, metrics: Dict[str, Any], filename: str) -> str:
        """Exports API usage log data and benchmarks to a CSV file."""
        file_path = os.path.join(self.export_dir, filename)
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                # Global metrics header
                writer.writerow(["=== RESEARCH ASSISTANT PRO ANALYTICS ==="])
                writer.writerow([])
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total LLM Requests", metrics.get("total_requests", 0)])
                writer.writerow(["Total Prompt Tokens Used", metrics.get("total_prompt_tokens", 0)])
                writer.writerow(["Total Completion Tokens Used", metrics.get("total_completion_tokens", 0)])
                writer.writerow(["Total Estimated Cost (USD)", f"${metrics.get('total_cost', 0.0):.4f}"])
                writer.writerow([])
                
                # Provider usage
                writer.writerow(["=== PROVIDER BENCHMARKS ==="])
                writer.writerow(["Provider", "Request Count", "Estimated Cost (USD)"])
                for pb in metrics.get("provider_breakdown", []):
                    writer.writerow([pb.get("provider"), pb.get("count"), f"${pb.get('cost', 0.0):.4f}"])
                writer.writerow([])

                # Model usage
                writer.writerow(["=== MODEL BREAKDOWN ==="])
                writer.writerow(["Model", "Request Count", "Estimated Cost (USD)"])
                for mb in metrics.get("model_breakdown", []):
                    writer.writerow([mb.get("model"), mb.get("count"), f"${mb.get('cost', 0.0):.4f}"])
                writer.writerow([])

                # Daily queries log
                writer.writerow(["=== DAILY USAGE LOGS ==="])
                writer.writerow(["Day", "Request Count", "Daily Cost (USD)"])
                for du in metrics.get("daily_usage", []):
                    writer.writerow([du.get("day"), du.get("count"), f"${du.get('cost', 0.0):.4f}"])

            logger.info(f"CSV Analytics exported to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to generate CSV export: {e}")
            raise e
