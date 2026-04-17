"""
ResumeForge AI — ATS Scorer
Computes ATS match score, keyword analysis, and resume strength report.
"""

import re
import logging
from collections import Counter

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger("resumeforge.scorer")

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    nltk.download("stopwords", quiet=True)


class ATSScorer:
    SKILL_PATTERNS = [
        r"\b(python|java|javascript|typescript|c\+\+|c#|ruby|go|rust|swift|kotlin|php|sql|html|css)\b",
        r"\b(react|angular|vue|node\.?js|express|django|flask|spring|\.net|next\.?js)\b",
        r"\b(aws|azure|gcp|docker|kubernetes|terraform|jenkins|ci/cd|github\s+actions)\b",
        r"\b(mysql|postgresql|mongodb|redis|elasticsearch|dynamodb|cassandra)\b",
        r"\b(git|linux|agile|scrum|rest\s+api|graphql|microservices|machine\s+learning|deep\s+learning)\b",
    ]

    ACTION_VERBS = {
        "achieved", "architected", "automated", "built", "created", "decreased",
        "delivered", "designed", "developed", "drove", "engineered", "established",
        "executed", "expanded", "generated", "grew", "implemented", "improved",
        "increased", "initiated", "integrated", "launched", "led", "managed",
        "mentored", "migrated", "modernized", "optimized", "orchestrated",
        "pioneered", "reduced", "refactored", "scaled", "secured", "simplified",
        "spearheaded", "streamlined", "strengthened", "transformed",
    }

    def __init__(self):
        self.stop_words = set(stopwords.words("english"))
        self.stop_words.update({"responsible", "duties", "assisted", "helped", "various", "using", "used", "work", "worked"})

    def full_analysis(self, resume_text: str, job_description: str, manual_keywords: list[str] = None) -> dict:
        manual_keywords = manual_keywords or []
        jd_keywords = self.extract_jd_keywords(job_description)
        ats_score = self.calculate_ats_score(resume_text, jd_keywords)
        missing = [kw for kw in jd_keywords if kw.lower() not in resume_text.lower()]
        matched = [kw for kw in jd_keywords if kw.lower() in resume_text.lower()]
        manual_found = [kw for kw in manual_keywords if kw.lower() in resume_text.lower()]
        manual_missing = [kw for kw in manual_keywords if kw.lower() not in resume_text.lower()]
        quality = self.assess_quality(resume_text)

        grade = "A+" if ats_score >= 90 else "A" if ats_score >= 80 else "B+" if ats_score >= 70 else "B" if ats_score >= 60 else "C" if ats_score >= 50 else "D"
        recs = self._generate_recommendations(ats_score, missing, quality, manual_missing)

        return {
            "ats_score": round(ats_score, 1),
            "ats_grade": grade,
            "keyword_analysis": {
                "jd_keywords_total": len(jd_keywords),
                "matched_keywords": matched,
                "matched_count": len(matched),
                "missing_keywords": missing,
                "missing_count": len(missing),
                "match_percentage": round((len(matched) / max(len(jd_keywords), 1)) * 100, 1),
            },
            "manual_keywords": {
                "required": manual_keywords,
                "found": manual_found,
                "missing": manual_missing,
                "all_present": len(manual_missing) == 0,
            },
            "quality_metrics": quality,
            "recommendations": recs,
        }

    def extract_jd_keywords(self, job_description: str) -> list[str]:
        try:
            vectorizer = TfidfVectorizer(max_features=50, stop_words="english", ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform([job_description.lower()])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]
            tfidf_keywords = [kw for kw, score in zip(feature_names, scores) if score > 0.05]
        except Exception:
            tfidf_keywords = []

        tech_keywords = set()
        for pattern in self.SKILL_PATTERNS:
            tech_keywords.update(re.findall(pattern, job_description.lower()))

        all_kw = list(set(tfidf_keywords) | tech_keywords)
        return sorted([kw for kw in all_kw if len(kw) > 2])

    def calculate_ats_score(self, resume_text: str, jd_keywords: list[str]) -> float:
        resume_lower = resume_text.lower()
        score = 0.0

        if jd_keywords:
            matched = sum(1 for kw in jd_keywords if kw.lower() in resume_lower)
            score += (matched / len(jd_keywords)) * 50

        word_set = set(resume_lower.split())
        action_score = min(len(word_set & self.ACTION_VERBS) / 8, 1.0)
        score += action_score * 15

        metrics = re.findall(r"\d+[%$]|\$[\d,]+|\d+\+?\s*(?:years?|months?|users?|projects?)", resume_lower)
        score += min(len(metrics) / 6, 1.0) * 15

        lines = resume_text.strip().split("\n")
        bullets = sum(1 for l in lines if l.strip().startswith(("•", "-", "–")))
        fmt = min(bullets / 5, 1.0) * 5
        sections = sum(1 for l in lines if l.strip().isupper() and len(l.strip().split()) <= 4)
        fmt += min(sections / 3, 1.0) * 5
        score += fmt

        wc = len(resume_text.split())
        if 300 <= wc <= 800: score += 10
        elif 200 <= wc <= 1000: score += 7
        elif 100 <= wc <= 1500: score += 4

        return min(score, 100)

    def assess_quality(self, resume_text: str) -> dict:
        words = resume_text.split()
        lines = resume_text.strip().split("\n")
        rl = resume_text.lower()
        word_set = set(rl.split())
        action_used = sorted(word_set & self.ACTION_VERBS)
        metrics = re.findall(r"\d+[%$]|\$[\d,]+|\d+\+?\s*(?:years?|months?|users?|projects?)", rl)
        weak = [p for p in ["responsible for", "duties included", "helped with", "assisted in", "familiar with"] if p in rl]

        return {
            "word_count": len(words),
            "bullet_points": sum(1 for l in lines if l.strip().startswith(("•", "-", "–"))),
            "action_verbs_count": len(action_used),
            "action_verbs_used": action_used,
            "quantified_achievements": len(metrics),
            "weak_phrases_found": weak,
            "has_summary": any(s in rl for s in ["summary", "objective", "profile"]),
            "estimated_pages": max(1, round(len(words) / 500)),
        }

    def _generate_recommendations(self, score, missing, quality, manual_missing):
        recs = []
        if missing:
            recs.append(f"Add these keywords: {', '.join(missing[:10])}")
        if manual_missing:
            recs.append(f"CRITICAL — Required keywords missing: {', '.join(manual_missing)}")
        if quality["quantified_achievements"] < 4:
            recs.append("Add more quantified achievements (numbers, %, $). Aim for 6+.")
        if quality["action_verbs_count"] < 5:
            recs.append("Use more strong action verbs to start bullet points.")
        if quality["weak_phrases_found"]:
            recs.append(f"Remove weak phrases: {', '.join(quality['weak_phrases_found'])}")
        if not quality["has_summary"]:
            recs.append("Add a professional summary section at the top.")
        if not recs:
            recs.append("Resume looks strong! Minor tweaks may help.")
        return recs
