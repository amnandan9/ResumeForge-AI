# 🔥 ResumeForge AI

**Automated ATS-Optimized Resume Generation Engine**

ResumeForge AI is a production-ready system that transforms any resume into a job-specific, ATS-optimized, professional resume — targeting **≥ 90% ATS compatibility**. Powered by local AI models via Ollama, orchestrated through n8n workflows, with LaTeX-based PDF output.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    n8n Workflow                      │
│  (Webhook → Parse → Optimize → LaTeX → PDF → Out)  │
└─────────┬───────────────────────────────┬───────────┘
          │ HTTP API Calls                │
    ┌─────▼─────┐                   ┌─────▼─────┐
    │ FastAPI   │◄──── Ollama ──────│ ATS Score │
    │ Backend   │     (Local LLM)   │  Engine   │
    └─────┬─────┘                   └───────────┘
          │
    ┌─────▼─────┐
    │  pdflatex │
    │  (LaTeX)  │
    └───────────┘
```

### Services (Docker Compose)

| Service | Port | Purpose |
|---------|------|---------|
| `resumeforge-api` | 8000 | Python FastAPI backend (parsing, AI, LaTeX, scoring) |
| `ollama` | 11434 | Local AI model server |
| Your existing `n8n` | 5678 | Workflow orchestration UI |

---

## ✨ Features

- ✅ **ATS Score ≥ 90%** — Keyword-optimized to pass Applicant Tracking Systems
- ✅ **AI-Powered Optimization** — Local LLM rewrites bullet points with X-Y-Z formula
- ✅ **Keyword Gap Analysis** — Identifies missing JD keywords automatically
- ✅ **Before vs After** — Shows what changed and why
- ✅ **LaTeX → PDF Pipeline** — Professional, clean resume output
- ✅ **User Customization** — Custom instructions, section preferences, manual keywords
- ✅ **PDF \& LaTeX Input** — Accepts both formats
- ✅ **n8n Orchestration** — Visual, modular, extensible workflow
- ✅ **Fully Local** — No data sent to external APIs
- ✅ **Resume Strength Report** — Action verbs, weak phrases, quantification analysis

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Existing n8n container (or use the optional n8n service in docker-compose)
- ~8GB disk space (for AI model)

### 1. Clone and Setup

```powershell
git clone https://github.com/YOUR_USERNAME/ResumeForge-AI.git
cd ResumeForge-AI
.\scripts\setup.ps1
```

This will:
- Build the FastAPI container (with TeX Live)
- Start Ollama and pull the AI model (~4GB)
- Connect your existing n8n to the shared network

### 2. Import n8n Workflow

1. Open n8n UI (`http://localhost:5678`)
2. Go to **Workflows → Import from File**
3. Select `n8n-workflow/resumeforge_workflow.json`
4. **Activate** the workflow

### 3. Test the Pipeline

```powershell
.\scripts\test_pipeline.ps1
```

### 4. Use via n8n Webhook

Send a POST request to your n8n webhook:

```bash
curl -X POST http://localhost:5678/webhook/resumeforge \
  -F "file=@your_resume.pdf" \
  -F "job_description=Paste the full JD here..." \
  -F "keywords=Python, AWS, Docker" \
  -F "custom_instructions=Focus on backend experience" \
  -F "section_preferences={\"Projects\": \"Relevant Projects\"}"
```

Or use the **direct API** at `http://localhost:8000/full-pipeline`.

---

## 📂 Project Structure

```
ResumeForge-AI/
├── docker-compose.yml              # Docker services (Ollama + API)
├── api/
│   ├── Dockerfile                  # Python 3.12 + TeX Live
│   ├── requirements.txt            # Python dependencies
│   ├── main.py                     # FastAPI app (6 endpoints)
│   ├── resume_parser.py            # PDF/LaTeX text extraction
│   ├── ai_optimizer.py             # Ollama AI integration
│   ├── ats_scorer.py               # ATS scoring engine
│   ├── latex_generator.py          # LaTeX rendering + PDF
│   └── templates/
│       └── resume_template.tex     # Jinja2 LaTeX template
├── n8n-workflow/
│   └── resumeforge_workflow.json   # Importable n8n workflow
├── scripts/
│   ├── setup.ps1                   # One-click setup
│   └── test_pipeline.ps1           # End-to-end test
├── test_data/
│   ├── sample_resume.tex           # Sample resume
│   └── sample_jd.txt               # Sample job description
└── README.md
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/parse-resume` | POST | Parse PDF/LaTeX file → structured text |
| `/optimize` | POST | AI-powered resume optimization |
| `/generate-latex` | POST | Render optimized JSON → LaTeX source |
| `/generate-pdf` | POST | Compile LaTeX → PDF |
| `/analyze-ats` | POST | Compute ATS score + keyword report |
| `/full-pipeline` | POST | End-to-end: file in → PDF + report out |

API Docs: `http://localhost:8000/docs`

---

## ⚙️ Configuration

### Environment Variables (docker-compose.yml)

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `mistral:7b` | AI model to use |

### Recommended Models by Hardware

| RAM | GPU | Recommended Model |
|-----|-----|-------------------|
| ≥16GB | NVIDIA | `llama3:8b` |
| 8-16GB | None | `mistral:7b` |
| ≤8GB | None | `phi3:mini` |

---

## 🔧 Connecting Your Existing n8n

If you already have an n8n container running:

```powershell
# Connect it to the ResumeForge network
docker network connect resumeforge-network YOUR_N8N_CONTAINER_NAME

# Inside n8n, use this URL for API calls:
# http://resumeforge-api:8000
```

---

## 📊 ATS Scoring Breakdown

| Factor | Weight | Criteria |
|--------|--------|----------|
| Keyword Match | 50% | JD keywords found in resume |
| Action Verbs | 15% | Strong verbs (8+ for full score) |
| Quantification | 15% | Metrics and numbers (6+ for full) |
| Formatting | 10% | Bullet points, section structure |
| Length | 10% | 300-800 words optimal |

---

## 📜 License

MIT License — Free to use, modify, and distribute.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Open a Pull Request
