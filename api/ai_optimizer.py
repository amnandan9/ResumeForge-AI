"""
ResumeForge AI — AI Optimizer
Interfaces with Ollama LLM to optimize resume content against job descriptions.
"""

import json
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger("resumeforge.optimizer")

# ─── Output Schema for AI ───────────────────────────────────
OUTPUT_SCHEMA = """{
  "ats_score": <number 0-100>,
  "missing_keywords": ["keyword1", "keyword2"],
  "added_keywords": ["keyword1", "keyword2"],
  "summary": "Professional summary paragraph",
  "skills": ["Skill 1", "Skill 2", "Skill 3"],
  "sections": [
    {
      "title": "Section Name",
      "content": [
        "• Bullet point using X-Y-Z formula",
        "• Another achievement"
      ]
    }
  ],
  "contact": {
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "phone number",
    "linkedin": "linkedin url",
    "github": "github url",
    "location": "City, State"
  },
  "education": [
    {
      "degree": "Degree Name",
      "institution": "University Name",
      "year": "Year or Date Range",
      "gpa": "GPA if mentioned"
    }
  ],
  "before_after": [
    {
      "before": "Original bullet point",
      "after": "Optimized bullet point"
    }
  ],
  "suggestions": [
    "Suggestion for further improvement"
  ]
}"""


class AIOptimizer:
    """Optimize resumes using a local LLM via Ollama."""

    def __init__(self, ollama_host: str = "http://ollama:11434", model: str = "mistral:7b"):
        self.ollama_host = ollama_host.rstrip("/")
        self.model = model
        self.api_url = f"{self.ollama_host}/api/generate"

    def optimize(
        self,
        resume_text: str,
        job_description: str,
        keywords: list[str] = None,
        custom_instructions: str = "",
        section_preferences: dict = None,
    ) -> dict:
        """
        Run the full AI optimization pipeline.
        Returns structured JSON with optimized resume content.
        """
        prompt = self._build_prompt(
            resume_text=resume_text,
            job_description=job_description,
            keywords=keywords or [],
            custom_instructions=custom_instructions,
            section_preferences=section_preferences or {},
        )

        logger.info(f"Sending optimization request to Ollama ({self.model})...")
        raw_response = self._call_ollama(prompt)
        logger.info(f"Received AI response ({len(raw_response)} chars)")

        result = self._parse_ai_response(raw_response)
        return result

    def _build_prompt(
        self,
        resume_text: str,
        job_description: str,
        keywords: list[str],
        custom_instructions: str,
        section_preferences: dict,
    ) -> str:
        """Construct the master optimization prompt."""

        keywords_str = ", ".join(keywords) if keywords else "None provided"

        section_prefs_str = ""
        if section_preferences:
            prefs = []
            for key, value in section_preferences.items():
                prefs.append(f"  - {key}: {value}")
            section_prefs_str = "\n".join(prefs)
        else:
            section_prefs_str = "No specific preferences"

        prompt = f"""You are an expert ATS (Applicant Tracking System) resume optimizer and senior hiring manager with 15+ years of experience reviewing resumes across technology companies.

═══════════════════════════════════════════
CANDIDATE'S CURRENT RESUME:
═══════════════════════════════════════════
{resume_text}

═══════════════════════════════════════════
TARGET JOB DESCRIPTION:
═══════════════════════════════════════════
{job_description}

═══════════════════════════════════════════
REQUIRED KEYWORDS (MUST be included):
═══════════════════════════════════════════
{keywords_str}

═══════════════════════════════════════════
USER'S CUSTOM INSTRUCTIONS:
═══════════════════════════════════════════
{custom_instructions if custom_instructions else "No specific instructions"}

═══════════════════════════════════════════
SECTION / HEADING PREFERENCES:
═══════════════════════════════════════════
{section_prefs_str}

═══════════════════════════════════════════
YOUR TASK:
═══════════════════════════════════════════

1. ANALYZE the job description thoroughly:
   - Extract ALL required skills, technologies, and qualifications
   - Identify the top priorities the employer is looking for
   - Note any specific experience levels or certifications required

2. COMPARE with the resume:
   - Identify which JD requirements are already covered
   - Find gaps — skills/keywords mentioned in JD but missing from resume
   - Identify weak bullet points that could be strengthened

3. OPTIMIZE the resume:
   - Rewrite bullet points using the X-Y-Z formula:
     "Accomplished [X] as measured by [Y], by doing [Z]"
   - Inject ALL required keywords naturally into relevant sections
   - Add quantified achievements wherever possible (%, $, time saved, users, scale)
   - Start every bullet point with a strong action verb
   - Ensure professional, concise language
   - Follow the user's custom instructions strictly
   - Apply any section naming/ordering preferences

4. ENSURE ATS COMPATIBILITY:
   - Use standard section headings
   - No special characters or formatting that ATS can't parse
   - Include exact keyword matches from the job description
   - Target an ATS match score of 90% or higher

═══════════════════════════════════════════
STRICT RULES:
═══════════════════════════════════════════
- Do NOT fabricate or hallucinate experience the candidate doesn't have
- Do NOT invent fake metrics — only quantify where reasonable from context
- KEEP the content truthful and realistic
- MAINTAIN a professional and concise tone
- EVERY bullet point must start with a strong action verb
- ALL required keywords provided by the user MUST appear in the output
- If the user provided section preferences, follow them exactly

═══════════════════════════════════════════
OUTPUT FORMAT:
═══════════════════════════════════════════
Return ONLY valid JSON (no markdown, no explanation, no code fences).
Use this exact schema:

{OUTPUT_SCHEMA}

IMPORTANT: Return ONLY the JSON object. No text before or after it. No markdown code fences."""

        return prompt

    def _call_ollama(self, prompt: str) -> str:
        """Send a prompt to Ollama and return the response text."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,       # Low for consistent, professional output
                    "top_p": 0.9,
                    "num_predict": 4096,       # Allow long responses for full resume
                    "repeat_penalty": 1.1,
                },
            }

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300,  # 5 min timeout for large resumes
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama. Is the service running?")
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.ollama_host}. "
                "Ensure the Ollama service is running."
            )
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out after 300s")
            raise TimeoutError("AI optimization timed out. Try with a shorter resume.")
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def _parse_ai_response(self, raw_response: str) -> dict:
        """
        Extract and validate JSON from the AI response.
        Handles cases where the AI wraps JSON in markdown code fences.
        """
        text = raw_response.strip()

        # Try to extract JSON from markdown code fences
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1).strip()

        # Try to find JSON object boundaries
        if not text.startswith("{"):
            start = text.find("{")
            if start != -1:
                text = text[start:]

        if not text.endswith("}"):
            end = text.rfind("}")
            if end != -1:
                text = text[: end + 1]

        # Parse JSON
        try:
            result = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed, attempting repair: {e}")
            result = self._repair_json(text)

        # Validate required fields
        result = self._validate_schema(result)

        return result

    def _repair_json(self, broken_json: str) -> dict:
        """Attempt to repair common JSON issues from AI output."""
        text = broken_json

        # Fix trailing commas before closing braces/brackets
        text = re.sub(r",\s*([}\]])", r"\1", text)

        # Fix unescaped newlines in strings
        text = re.sub(r'(?<=": ")(.*?)(?=")', lambda m: m.group(0).replace("\n", "\\n"), text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error("JSON repair failed. Returning fallback structure.")
            return self._fallback_response(broken_json)

    def _fallback_response(self, raw_text: str) -> dict:
        """Generate a fallback response structure if JSON parsing completely fails."""
        return {
            "ats_score": 0,
            "missing_keywords": [],
            "added_keywords": [],
            "summary": "",
            "skills": [],
            "sections": [],
            "contact": {},
            "education": [],
            "before_after": [],
            "suggestions": [
                "AI response could not be parsed. Please try again.",
                f"Raw response preview: {raw_text[:500]}...",
            ],
        }

    def _validate_schema(self, data: dict) -> dict:
        """Ensure all required fields exist in the response."""
        defaults = {
            "ats_score": 0,
            "missing_keywords": [],
            "added_keywords": [],
            "summary": "",
            "skills": [],
            "sections": [],
            "contact": {},
            "education": [],
            "before_after": [],
            "suggestions": [],
        }

        for key, default in defaults.items():
            if key not in data:
                data[key] = default

        # Ensure sections have correct structure
        valid_sections = []
        for section in data.get("sections", []):
            if isinstance(section, dict) and "title" in section:
                if "content" not in section:
                    section["content"] = []
                elif isinstance(section["content"], str):
                    section["content"] = [section["content"]]
                valid_sections.append(section)
        data["sections"] = valid_sections

        return data

    def enforce_keywords(self, result: dict, required_keywords: list[str]) -> dict:
        """
        Post-process to ensure ALL user-provided keywords appear in the resume.
        If a keyword is missing, inject it into the skills section.
        """
        # Build full text from the optimized result
        full_text = result.get("summary", "").lower()
        full_text += " " + " ".join(result.get("skills", [])).lower()
        for section in result.get("sections", []):
            full_text += " " + " ".join(section.get("content", [])).lower()

        missing = []
        for kw in required_keywords:
            if kw.lower() not in full_text:
                missing.append(kw)

        # Add missing keywords to skills
        if missing:
            logger.info(f"Injecting {len(missing)} missing keywords into skills: {missing}")
            current_skills = result.get("skills", [])
            for kw in missing:
                if kw not in current_skills:
                    current_skills.append(kw)
            result["skills"] = current_skills

            # Update added_keywords
            added = result.get("added_keywords", [])
            added.extend(missing)
            result["added_keywords"] = list(set(added))

        return result
