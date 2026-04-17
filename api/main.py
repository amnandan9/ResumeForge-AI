"""
ResumeForge AI — FastAPI Backend
Main application with all REST endpoints for the resume optimization pipeline.
"""

import os
import json
import base64
import uuid
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from resume_parser import ResumeParser
from ai_optimizer import AIOptimizer
from ats_scorer import ATSScorer
from latex_generator import LaTeXGenerator

# ─── Logging ────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("resumeforge")

# ─── App Init ───────────────────────────────────────────────
app = FastAPI(
    title="ResumeForge AI",
    description="Automated ATS-optimized resume generation engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Service Instances ──────────────────────────────────────
parser = ResumeParser()
optimizer = AIOptimizer(
    ollama_host=os.getenv("OLLAMA_HOST", "http://ollama:11434"),
    model=os.getenv("OLLAMA_MODEL", "mistral:7b"),
)
scorer = ATSScorer()
latex_gen = LaTeXGenerator(template_dir=Path(__file__).parent / "templates")

# ─── Shared directory for file exchange ─────────────────────
SHARED_DIR = Path("/app/shared")
OUTPUT_DIR = Path("/app/output")
SHARED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════

class OptimizeRequest(BaseModel):
    resume_text: str
    job_description: str
    keywords: list[str] = []
    custom_instructions: str = ""
    section_preferences: dict = {}


class GenerateLatexRequest(BaseModel):
    optimized_data: dict
    template_name: str = "resume_template.tex"


class GeneratePDFRequest(BaseModel):
    latex_content: str


class ATSAnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str
    keywords: list[str] = []


class FullPipelineRequest(BaseModel):
    job_description: str
    keywords: str = ""                # comma-separated
    custom_instructions: str = ""
    section_preferences: str = ""     # JSON string


# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and n8n."""
    return {"status": "healthy", "service": "resumeforge-api", "version": "1.0.0"}


@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    """
    Parse a resume file (PDF or LaTeX) and extract structured text.
    Returns raw text and identified sections.
    """
    logger.info(f"Parsing resume: {file.filename} ({file.content_type})")

    try:
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith(".pdf"):
            result = parser.parse_pdf(content)
        elif filename.endswith(".tex"):
            result = parser.parse_latex(content.decode("utf-8", errors="replace"))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename}. Use .pdf or .tex",
            )

        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "raw_text": result["raw_text"],
            "sections": result["sections"],
            "word_count": len(result["raw_text"].split()),
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Parse error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")


@app.post("/optimize")
async def optimize_resume(request: OptimizeRequest):
    """
    Send resume + JD to AI model for optimization.
    Returns structured JSON with optimized content.
    """
    logger.info("Starting AI optimization...")

    try:
        result = optimizer.optimize(
            resume_text=request.resume_text,
            job_description=request.job_description,
            keywords=request.keywords,
            custom_instructions=request.custom_instructions,
            section_preferences=request.section_preferences,
        )

        # Post-process: enforce all manual keywords are present
        if request.keywords:
            result = optimizer.enforce_keywords(result, request.keywords)

        return JSONResponse(content={
            "success": True,
            "optimized": result,
        })

    except Exception as e:
        logger.error(f"Optimization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI optimization failed: {str(e)}")


@app.post("/generate-latex")
async def generate_latex(request: GenerateLatexRequest):
    """
    Generate LaTeX source code from optimized resume JSON.
    """
    logger.info("Generating LaTeX...")

    try:
        latex_content = latex_gen.render_template(
            data=request.optimized_data,
            template_name=request.template_name,
        )

        return JSONResponse(content={
            "success": True,
            "latex_content": latex_content,
            "char_count": len(latex_content),
        })

    except Exception as e:
        logger.error(f"LaTeX generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LaTeX generation failed: {str(e)}")


@app.post("/generate-pdf")
async def generate_pdf(request: GeneratePDFRequest):
    """
    Compile LaTeX source into a PDF file.
    Returns Base64-encoded PDF.
    """
    logger.info("Compiling PDF...")

    try:
        pdf_bytes = latex_gen.compile_to_pdf(request.latex_content)

        # Save a copy to shared directory
        pdf_id = str(uuid.uuid4())[:8]
        pdf_path = OUTPUT_DIR / f"resume_{pdf_id}.pdf"
        pdf_path.write_bytes(pdf_bytes)

        # Also save to shared volume for n8n access
        shared_pdf = SHARED_DIR / f"resume_{pdf_id}.pdf"
        shared_pdf.write_bytes(pdf_bytes)

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return JSONResponse(content={
            "success": True,
            "pdf_base64": pdf_base64,
            "pdf_filename": f"resume_{pdf_id}.pdf",
            "pdf_size_bytes": len(pdf_bytes),
        })

    except Exception as e:
        logger.error(f"PDF compilation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF compilation failed: {str(e)}")


@app.post("/analyze-ats")
async def analyze_ats(request: ATSAnalyzeRequest):
    """
    Compute ATS score and keyword analysis for a resume against a JD.
    """
    logger.info("Running ATS analysis...")

    try:
        report = scorer.full_analysis(
            resume_text=request.resume_text,
            job_description=request.job_description,
            manual_keywords=request.keywords,
        )

        return JSONResponse(content={
            "success": True,
            "report": report,
        })

    except Exception as e:
        logger.error(f"ATS analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ATS analysis failed: {str(e)}")


@app.post("/full-pipeline")
async def full_pipeline(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    keywords: str = Form(""),
    custom_instructions: str = Form(""),
    section_preferences: str = Form("{}"),
):
    """
    End-to-end pipeline: Parse → Optimize → Generate LaTeX → PDF → ATS Report.
    This is the single-call endpoint for the complete workflow.
    """
    logger.info(f"=== FULL PIPELINE START === File: {file.filename}")

    try:
        # ── Step 1: Parse Resume ──────────────────────────
        logger.info("[1/5] Parsing resume...")
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith(".pdf"):
            parsed = parser.parse_pdf(content)
        elif filename.endswith(".tex"):
            parsed = parser.parse_latex(content.decode("utf-8", errors="replace"))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        resume_text = parsed["raw_text"]
        original_sections = parsed["sections"]

        # ── Step 2: Parse Inputs ──────────────────────────
        logger.info("[2/5] Processing inputs...")
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        try:
            sec_prefs = json.loads(section_preferences) if section_preferences else {}
        except json.JSONDecodeError:
            sec_prefs = {}

        # ── Step 3: AI Optimization ───────────────────────
        logger.info("[3/5] Running AI optimization...")
        optimized = optimizer.optimize(
            resume_text=resume_text,
            job_description=job_description,
            keywords=kw_list,
            custom_instructions=custom_instructions,
            section_preferences=sec_prefs,
        )

        if kw_list:
            optimized = optimizer.enforce_keywords(optimized, kw_list)

        # ── Step 4: Generate LaTeX + PDF ──────────────────
        logger.info("[4/5] Generating LaTeX and PDF...")
        latex_content = latex_gen.render_template(optimized)

        pdf_bytes = latex_gen.compile_to_pdf(latex_content)
        pdf_id = str(uuid.uuid4())[:8]

        # Save outputs
        tex_path = OUTPUT_DIR / f"resume_{pdf_id}.tex"
        pdf_path = OUTPUT_DIR / f"resume_{pdf_id}.pdf"
        tex_path.write_text(latex_content, encoding="utf-8")
        pdf_path.write_bytes(pdf_bytes)

        # Copy to shared volume
        (SHARED_DIR / f"resume_{pdf_id}.tex").write_text(latex_content, encoding="utf-8")
        (SHARED_DIR / f"resume_{pdf_id}.pdf").write_bytes(pdf_bytes)

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # ── Step 5: ATS Analysis ──────────────────────────
        logger.info("[5/5] Running ATS analysis...")
        # Build optimized resume text from the JSON for scoring
        optimized_text = optimized.get("summary", "")
        for section in optimized.get("sections", []):
            optimized_text += " " + section.get("title", "")
            optimized_text += " " + " ".join(section.get("content", []))
        optimized_text += " " + " ".join(optimized.get("skills", []))

        ats_report = scorer.full_analysis(
            resume_text=optimized_text,
            job_description=job_description,
            manual_keywords=kw_list,
        )

        # ── Build Before vs After ─────────────────────────
        before_after = []
        for section in optimized.get("sections", []):
            title = section.get("title", "")
            original_content = original_sections.get(title, "")
            new_content = "\n".join(section.get("content", []))
            if original_content or new_content:
                before_after.append({
                    "section": title,
                    "before": original_content if original_content else "(not in original)",
                    "after": new_content,
                })

        logger.info("=== FULL PIPELINE COMPLETE ===")

        return JSONResponse(content={
            "success": True,
            "pipeline_id": pdf_id,
            "optimized_data": optimized,
            "latex_content": latex_content,
            "pdf_base64": pdf_base64,
            "pdf_filename": f"resume_{pdf_id}.pdf",
            "ats_report": ats_report,
            "before_after": before_after,
            "suggestions": optimized.get("suggestions", []),
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
# APP STARTUP
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
