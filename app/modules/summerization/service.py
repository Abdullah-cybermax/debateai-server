import io
import os
from time import time
from xml.sax.saxutils import escape
from transformers import pipeline
from modules.summerization.repository import SummerizationRepository
from modules.arguments.service import ArgumentService
from modules.argument_segmentation.service import ArgumentSegmentationService
from modules.debates.service import DebateService
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from core.logger import logger

REPORTS_DIR = "storage/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


class SummerizationService:

    def __init__(self):
        self.arguments = ArgumentService()
        self.segmentation = ArgumentSegmentationService()
        self.repo = SummerizationRepository()
        self.debate_service = DebateService()
        self.summarizer = pipeline(
            "summarization",
            model="sshleifer/distilbart-cnn-12-6",
            tokenizer="sshleifer/distilbart-cnn-12-6",
            device=-1,
        )

    def generate_summary(self, debate_id: int) -> str:
        arguments_list = self.arguments.get_arguments(debate_id)
        arguments_content = [arg["content"] for arg in arguments_list.data]
        segmentations_list = [
            self.segmentation.segment_arguments(arg) for arg in arguments_content
        ]

        all_segments = []
        for seg in segmentations_list:
            all_segments.extend(seg)

        role_segment_pairs = []
        for arg, segs in zip(arguments_list.data, segmentations_list):
            for seg in segs:
                role_segment_pairs.append({"text": seg, "role": arg["role"]})

        pros = [
            item["text"] for item in role_segment_pairs if item["role"].value == "for"
        ]
        cons = [
            item["text"]
            for item in role_segment_pairs
            if item["role"].value == "against"
        ]
        neutral = [
            item["text"]
            for item in role_segment_pairs
            if item["role"].value == "neutral"
        ]

        def summarize_segments(segments: list) -> str:
            # Always returns a plain string now — no more dict/str mismatch
            if not segments:
                return "No point is provided."

            combined_text = " ".join(segments)

            summary = self.summarizer(
                combined_text,
                max_length=130,
                min_length=30,
                num_beams=4,
                length_penalty=1.0,
            )
            return summary[0]["summary_text"]

        res_data = {
            "pros": summarize_segments(pros),
            "cons": summarize_segments(cons),
            "neutral": summarize_segments(neutral),
        }

        file_name = self.generate_pdf_report(debate_id, res_data)
        self.repo.create_summary(debate_id=debate_id, url=file_name)

        return res_data

    def generate_pdf_report(self, debate_id: int, data: dict) -> str:
        """Builds the PDF and saves it to local storage. Returns the file_name
        (not a path/URL) — the download endpoint resolves this against
        REPORTS_DIR, so the DB never stores a filesystem-specific path."""

        try:
            logger.info(f"📄 Generating PDF report for debate {debate_id}")

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []

            styles = getSampleStyleSheet()
            normal = styles["Normal"]
            heading = styles["Heading2"]

            elements.append(
                Paragraph(f"Debate Summary (ID: {debate_id})", styles["Heading1"])
            )
            elements.append(Spacer(1, 16))

            elements.append(Paragraph("Arguments For:", heading))
            elements.append(Paragraph(escape(data.get("pros", "")), normal))
            elements.append(Spacer(1, 12))

            elements.append(Paragraph("Arguments Against:", heading))
            elements.append(Paragraph(escape(data.get("cons", "")), normal))
            elements.append(Spacer(1, 12))

            elements.append(Paragraph("Neutral Points:", heading))
            elements.append(Paragraph(escape(data.get("neutral", "")), normal))
            elements.append(Spacer(1, 12))

            doc.build(elements)
            buffer.seek(0)

            file_name = f"debate_summary_{debate_id}_{int(time())}.pdf"
            file_path = os.path.join(REPORTS_DIR, file_name)

            with open(file_path, "wb") as f:
                f.write(buffer.getvalue())

            logger.info(f"✅ PDF saved locally: {file_path}")

            return file_name

        except Exception as e:
            logger.error(f"❌ PDF generation failed: {str(e)}")
            raise

    def get_summary(self, debate_id: int):
        return self.repo.get_summary(debate_id=debate_id)

    def get_report_path(self, debate_id: int) -> str | None:
        """Resolves the stored file_name to a full local path for serving."""
        file_name = self.repo.get_summary(debate_id=debate_id)
        if not file_name:
            return None
        file_path = os.path.join(REPORTS_DIR, file_name)
        return file_path if os.path.exists(file_path) else None