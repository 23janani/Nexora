"""
Document Processor & Quality Gatekeeper
Supports: PDF, DOCX, DOC, TXT, JPG, JPEG, PNG (via native Apple Vision OCR)
Preserves: Headings, bullet points, sections, dates, qualifications, experience.
Checks: Document readability & quality.
"""

import os
import re
import subprocess
from typing import Dict, Any, Tuple
from pypdf import PdfReader
from docx import Document


class DocumentProcessor:
    def __init__(self, ocr_engine_path: str = "./ocr_engine"):
        self.ocr_engine_path = ocr_engine_path

    def extract_text(self, file_path: str, filename: str = "") -> Tuple[str, Dict[str, Any]]:
        """
        Extract text from file based on extension.
        Returns (extracted_text, metadata_dict)
        """
        if not filename:
            filename = os.path.basename(file_path)

        ext = os.path.splitext(filename)[1].lower()
        text = ""
        method = "unknown"

        if ext == ".txt":
            text, method = self._extract_txt(file_path)
        elif ext == ".pdf":
            text, method = self._extract_pdf(file_path)
        elif ext == ".docx":
            text, method = self._extract_docx(file_path)
        elif ext == ".doc":
            text, method = self._extract_doc(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
            text, method = self._extract_image_ocr(file_path)
        else:
            # Fallback attempt plain text
            text, method = self._extract_txt(file_path)

        cleaned_text = self.clean_and_normalize(text)
        quality_info = self.check_readability(cleaned_text, filename)

        metadata = {
            "filename": filename,
            "file_type": ext.replace(".", "").upper() if ext else "UNKNOWN",
            "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else len(text),
            "extraction_method": method,
            "quality": quality_info
        }

        return cleaned_text, metadata

    def _extract_txt(self, file_path: str) -> Tuple[str, str]:
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read(), "plain_text_utf8"
            except Exception:
                continue
        with open(file_path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore"), "plain_text_fallback"

    def _extract_pdf(self, file_path: str) -> Tuple[str, str]:
        full_text = ""
        try:
            reader = PdfReader(file_path)
            pages_text = []
            for i, page in enumerate(reader.pages):
                page_str = page.extract_text() or ""
                if page_str.strip():
                    pages_text.append(page_str)
            full_text = "\n\n".join(pages_text)
            # Check if text is substantial and not spaced out like 'A R T I F I C I A L'
            is_spaced_out = "A R T I F I C I A L" in full_text or "S T U D E N T" in full_text
            if len(full_text.strip()) > 50 and not is_spaced_out:
                return full_text, "pypdf_native"
        except Exception:
            full_text = ""

        # Neural Apple Vision OCR fallback for scanned, image-based, or non-standard font PDFs
        ocr_text, ocr_method = self._extract_image_ocr(file_path)
        if len(ocr_text.strip()) > len(full_text.strip()) and len(ocr_text.strip()) >= 40:
            return ocr_text, "apple_vision_pdf_ocr"

        if len(full_text.strip()) > 50:
            return full_text, "pypdf_native"
        elif len(full_text.strip()) > 0:
            return full_text, "pypdf_sparse"

        return "", "pdf_extraction_empty"

    def _extract_docx(self, file_path: str) -> Tuple[str, str]:
        try:
            doc = Document(file_path)
            paragraphs = []
            for p in doc.paragraphs:
                if p.text.strip():
                    # Preserve bullet markers if style indicates list
                    if "List" in (p.style.name if p.style else ""):
                        paragraphs.append(f"• {p.text.strip()}")
                    else:
                        paragraphs.append(p.text.strip())
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            return "\n\n".join(paragraphs), "python_docx"
        except Exception as e:
            return "", f"docx_error: {str(e)}"

    def _extract_doc(self, file_path: str) -> Tuple[str, str]:
        # Legacy .doc binary extraction fallback
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            strings = re.findall(b"[\x20-\x7E\t\r\n]{4,}", content)
            text = " ".join([s.decode("ascii", errors="ignore") for s in strings])
            return text, "doc_binary_extractor"
        except Exception as e:
            return "", f"doc_error: {str(e)}"

    def _extract_image_ocr(self, file_path: str) -> Tuple[str, str]:
        # Native macOS Apple Vision OCR via compiled ocr_engine
        if os.path.exists(self.ocr_engine_path):
            try:
                res = subprocess.run(
                    [self.ocr_engine_path, file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip(), "apple_vision_neural_ocr"
            except Exception as e:
                print(f"Apple Vision OCR execution error: {e}")

        return "", "ocr_unavailable_or_empty"

    def clean_and_normalize(self, text: str) -> str:
        """
        Clean text while strictly preserving headings, bullet points,
        dates, numbers, and structured formatting.
        """
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove native CoreGraphics diagnostic stdout warnings
        text = re.sub(r"(?i)^.*CoreGraphics PDF has logged an error.*$\n?", "", text, flags=re.MULTILINE)

        # Standardize common bullet characters to '•'
        text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u25CB\u25CF]", "•", text)

        # Ensure bullet points have a leading space and newline if squeezed
        text = re.sub(r"([^\n])\s*•\s*", r"\1\n• ", text)

        # Repair email addresses broken by narrow column layout wrapping (e.g. name@domain.edu.i\nn)
        text = re.sub(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]*[a-zA-Z])\n+([a-zA-Z]{1,4})\b", r"\1\2", text)

        # Normalize multiple spaces into single space, but retain newlines
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

        # Remove redundant empty lines (max 2 consecutive)
        cleaned_lines = []
        consecutive_blank = 0
        for line in lines:
            if not line:
                consecutive_blank += 1
                if consecutive_blank <= 1:
                    cleaned_lines.append("")
            else:
                consecutive_blank = 0
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def check_readability(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Readability & Quality Check:
        If document cannot be read properly:
        - readable: False
        - issue: Description of failure
        - suggestion: Prompt to upload clearer doc
        """
        if not text or len(text.strip()) < 40:
            return {
                "readable": False,
                "score": 0.0,
                "status": "Document could not be reliably read.",
                "issue": "Extracted text is empty or shorter than minimum viable content (<40 chars). File may be corrupted, blank, or an unsupported image format without recognizable text.",
                "suggestion": "Please upload a clearer PDF, Word document, high-resolution image, or paste the text directly."
            }

        words = re.findall(r"\b[A-Za-z]{2,}\b", text)
        total_chars = len(text)
        printable_chars = len(re.findall(r"[\x20-\x7E\n\t]", text))
        printable_ratio = (printable_chars / total_chars) if total_chars > 0 else 0

        # Check for garbled/binary contents
        if printable_ratio < 0.75:
            return {
                "readable": False,
                "score": round(printable_ratio * 100, 1),
                "status": "Document could not be reliably read.",
                "issue": f"Excessive non-printable characters detected ({round((1 - printable_ratio)*100)}% corrupt/binary encoding).",
                "suggestion": "Please save the file as a standard PDF or DOCX and re-upload, or copy-paste the text directly."
            }

        if len(words) < 15:
            return {
                "readable": False,
                "score": 25.0,
                "status": "Document could not be reliably read.",
                "issue": f"Only {len(words)} recognizable words found. Content lacks sufficient resume structure.",
                "suggestion": "Ensure the document contains full resume sections (Experience, Education, Skills) and is not a protected PDF."
            }

        section_matches = len(re.findall(
            r"(?i)\b(experience|education|skills|projects|summary|certifications|employment|work history)\b",
            text
        ))
        has_email = 1 if re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text) else 0

        quality_score = min(100.0, max(50.0, 50 + (min(len(words), 300) / 300.0) * 25 + min(section_matches * 5, 15) + (has_email * 10)))

        return {
            "readable": True,
            "score": round(quality_score, 1),
            "status": "High Quality" if quality_score >= 80 else "Acceptable Quality",
            "word_count": len(words),
            "character_count": total_chars,
            "has_sections": section_matches > 0,
            "issue": None,
            "suggestion": None
        }
