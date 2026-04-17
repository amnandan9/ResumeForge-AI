"""
ResumeForge AI — Resume Parser
Extracts text and structured sections from PDF and LaTeX resume files.
"""

import re
import logging
from typing import Optional

import pdfplumber
import fitz  # PyMuPDF

logger = logging.getLogger("resumeforge.parser")


class ResumeParser:
    """Parse PDF and LaTeX resumes into structured text."""

    # Common resume section headings
    SECTION_PATTERNS = [
        r"(?i)^(summary|professional\s+summary|objective|profile)",
        r"(?i)^(experience|work\s+experience|professional\s+experience|employment)",
        r"(?i)^(education|academic|qualifications)",
        r"(?i)^(skills|technical\s+skills|core\s+competencies|technologies)",
        r"(?i)^(projects|personal\s+projects|relevant\s+projects|key\s+projects)",
        r"(?i)^(certifications?|licenses?|credentials)",
        r"(?i)^(awards?|honors?|achievements?)",
        r"(?i)^(publications?|research)",
        r"(?i)^(volunteer|community|extracurricular)",
        r"(?i)^(interests?|hobbies)",
        r"(?i)^(languages?)",
        r"(?i)^(references?)",
    ]

    # LaTeX commands to strip
    LATEX_COMMANDS = [
        r"\\documentclass\{[^}]*\}",
        r"\\usepackage(\[[^\]]*\])?\{[^}]*\}",
        r"\\begin\{document\}",
        r"\\end\{document\}",
        r"\\begin\{(itemize|enumerate|description|center|tabular|table)\}",
        r"\\end\{(itemize|enumerate|description|center|tabular|table)\}",
        r"\\(hfill|vfill|hspace|vspace|newpage|clearpage|pagebreak)\{?[^}]*\}?",
        r"\\(tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\b",
        r"\\(textbf|textit|texttt|emph|underline)\{([^}]*)\}",
        r"\\(bf|it|tt|em|sc)\b",
        r"\\(centering|raggedright|raggedleft)\b",
        r"\\(noindent|par)\b",
        r"\\\\",
        r"\\item\b",
        r"\\href\{[^}]*\}\{([^}]*)\}",
        r"\\[a-zA-Z]+\*?\{",  # generic command opener
        r"\}",
    ]

    def parse_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Extract text from PDF using pdfplumber, with PyMuPDF as fallback.
        Returns dict with 'raw_text' and 'sections'.
        """
        raw_text = self._extract_with_pdfplumber(pdf_bytes)

        # Fallback to PyMuPDF if pdfplumber returns empty/short text
        if not raw_text or len(raw_text.strip()) < 50:
            logger.warning("pdfplumber extraction too short, falling back to PyMuPDF")
            raw_text = self._extract_with_pymupdf(pdf_bytes)

        if not raw_text or len(raw_text.strip()) < 20:
            raise ValueError("Could not extract meaningful text from PDF. File may be image-based.")

        sections = self._identify_sections(raw_text)

        return {
            "raw_text": raw_text.strip(),
            "sections": sections,
        }

    def parse_latex(self, tex_content: str) -> dict:
        """
        Parse LaTeX source and extract structured text.
        Returns dict with 'raw_text' and 'sections'.
        """
        # First, extract sections from LaTeX structure
        sections = self._parse_latex_sections(tex_content)

        # Then clean to get raw text
        raw_text = self._strip_latex_commands(tex_content)

        return {
            "raw_text": raw_text.strip(),
            "sections": sections if sections else self._identify_sections(raw_text),
        }

    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> str:
        """Extract text using pdfplumber."""
        import io
        try:
            text_parts = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
            return ""

    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> str:
        """Extract text using PyMuPDF (fitz) as fallback."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
            return ""

    def _strip_latex_commands(self, tex: str) -> str:
        """Remove LaTeX commands and return plain text."""
        text = tex

        # Remove comments
        text = re.sub(r"%.*$", "", text, flags=re.MULTILINE)

        # Replace \href{url}{text} with just text
        text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)

        # Replace \textbf{text}, \textit{text}, etc. with just text
        text = re.sub(r"\\(?:textbf|textit|texttt|emph|underline)\{([^}]*)\}", r"\1", text)

        # Remove section/subsection commands but keep the title
        text = re.sub(r"\\(?:section|subsection|subsubsection)\*?\{([^}]*)\}", r"\n\1\n", text)

        # Remove remaining LaTeX commands
        for pattern in self.LATEX_COMMANDS:
            text = re.sub(pattern, " ", text)

        # Remove remaining curly braces
        text = text.replace("{", "").replace("}", "")

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        return text.strip()

    def _parse_latex_sections(self, tex: str) -> dict:
        """
        Extract sections from LaTeX structure using \\section commands.
        Returns dict mapping section title to content text.
        """
        sections = {}

        # Find all \section{Title} or \section*{Title}
        pattern = r"\\(?:section|subsection)\*?\{([^}]+)\}"
        matches = list(re.finditer(pattern, tex))

        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(tex)

            section_content = tex[start:end]
            # Clean the section content
            clean_content = self._strip_latex_commands(section_content)
            sections[title] = clean_content.strip()

        return sections

    def _identify_sections(self, text: str) -> dict:
        """
        Identify resume sections from plain text using pattern matching.
        Returns dict mapping section name to content.
        """
        lines = text.split("\n")
        sections = {}
        current_section = "header"
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if this line is a section header
            is_header = False
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, stripped):
                    # Save previous section
                    if current_content:
                        sections[current_section] = "\n".join(current_content).strip()

                    current_section = stripped
                    current_content = []
                    is_header = True
                    break

            # Heuristic: ALL CAPS short line is likely a header
            if not is_header and stripped.isupper() and len(stripped.split()) <= 5:
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = stripped.title()
                current_content = []
                is_header = True

            if not is_header:
                current_content.append(stripped)

        # Save last section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections
