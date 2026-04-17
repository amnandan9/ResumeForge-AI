"""
ResumeForge AI — LaTeX Generator
Renders optimized resume JSON into LaTeX and compiles PDF.
"""

import os
import re
import subprocess
import tempfile
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("resumeforge.latex")


class LaTeXGenerator:
    """Generate LaTeX source and compile to PDF."""

    # Characters that need escaping in LaTeX
    LATEX_SPECIAL = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    def __init__(self, template_dir: Path = None):
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        self.template_dir = template_dir
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,  # LaTeX, not HTML
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
            comment_start_string="<#",
            comment_end_string="#>",
        )
        # Register escape filter
        self.jinja_env.filters["latex_escape"] = self.escape_latex

    @staticmethod
    def escape_latex(text: str) -> str:
        """Escape LaTeX special characters in text."""
        if not text:
            return ""
        result = str(text)
        # Must escape backslash first
        result = result.replace("\\", r"\textbackslash{}")
        for char, replacement in LaTeXGenerator.LATEX_SPECIAL.items():
            result = result.replace(char, replacement)
        return result

    def render_template(self, data: dict, template_name: str = "resume_template.tex") -> str:
        """
        Render optimized resume data into LaTeX using a Jinja2 template.
        """
        template = self.jinja_env.get_template(template_name)

        # Prepare data with escaped content
        context = self._prepare_context(data)

        latex_content = template.render(**context)
        logger.info(f"Generated LaTeX ({len(latex_content)} chars)")
        return latex_content

    def _prepare_context(self, data: dict) -> dict:
        """Prepare template context with escaped values."""
        esc = self.escape_latex

        # Contact info
        contact = data.get("contact", {})
        ctx = {
            "name": esc(contact.get("name", "Your Name")),
            "email": esc(contact.get("email", "")),
            "phone": esc(contact.get("phone", "")),
            "linkedin": contact.get("linkedin", ""),  # URLs shouldn't be escaped
            "github": contact.get("github", ""),
            "location": esc(contact.get("location", "")),
            "summary": esc(data.get("summary", "")),
            "skills": [esc(s) for s in data.get("skills", [])],
            "sections": [],
            "education": [],
        }

        # Sections
        for section in data.get("sections", []):
            ctx["sections"].append({
                "title": esc(section.get("title", "")),
                "content": [esc(line) for line in section.get("content", [])],
            })

        # Education
        for edu in data.get("education", []):
            ctx["education"].append({
                "degree": esc(edu.get("degree", "")),
                "institution": esc(edu.get("institution", "")),
                "year": esc(edu.get("year", "")),
                "gpa": esc(edu.get("gpa", "")),
            })

        return ctx

    def compile_to_pdf(self, latex_content: str) -> bytes:
        """
        Compile LaTeX string to PDF using pdflatex.
        Returns PDF as bytes.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "resume.tex")
            pdf_path = os.path.join(tmpdir, "resume.pdf")

            # Write LaTeX file
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # Run pdflatex twice (for references)
            for run in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )

                if result.returncode != 0 and run == 1:
                    logger.error(f"pdflatex error:\n{result.stdout[-2000:]}")
                    logger.error(f"pdflatex stderr:\n{result.stderr[-1000:]}")
                    raise RuntimeError(
                        f"PDF compilation failed. LaTeX errors:\n{result.stdout[-1000:]}"
                    )

            if not os.path.exists(pdf_path):
                raise FileNotFoundError("PDF was not generated. Check LaTeX syntax.")

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            logger.info(f"PDF compiled successfully ({len(pdf_bytes)} bytes)")
            return pdf_bytes
