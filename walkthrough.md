# ResumeForge AI — Walkthrough

## ✅ What Was Built

A complete, production-ready resume optimization engine with **15 files** across **5 components**.

---

### Component 1: Docker Infrastructure
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Ollama + FastAPI services stack |
| `api/Dockerfile` | Python 3.12 + TeX Live for PDF generation |
| `api/requirements.txt` | FastAPI, pdfplumber, PyMuPDF, scikit-learn, NLTK, Jinja2 |

### Component 2: Python FastAPI Backend (Core Engine)
| File | Purpose |
|------|---------|
| `api/main.py` | 7 REST endpoints including full-pipeline |
| `api/resume_parser.py` | PDF (pdfplumber + PyMuPDF fallback) and LaTeX parsing |
| `api/ai_optimizer.py` | Ollama LLM integration, prompt engineering, JSON repair |
| `api/ats_scorer.py` | TF-IDF keyword extraction, multi-factor ATS scoring |
| `api/latex_generator.py` | Jinja2 → LaTeX rendering + pdflatex PDF compilation |

### Component 3: LaTeX Template
| File | Purpose |
|------|---------|
| `api/templates/resume_template.tex` | ATS-friendly template with custom Jinja2 delimiters |

### Component 4: n8n Workflow
| File | Purpose |
|------|---------|
| `n8n-workflow/resumeforge_workflow.json` | 10-node pipeline: Webhook → Parse → Optimize → LaTeX → PDF → Output |

### Component 5: Scripts & Test Data
| File | Purpose |
|------|---------|
| `scripts/setup.ps1` | One-click setup: builds containers, pulls model, connects n8n |
| `scripts/test_pipeline.ps1` | End-to-end test with sample data |
| `test_data/sample_resume.tex` | Sample resume (passive voice, no metrics) for testing |
| `test_data/sample_jd.txt` | Sample Senior Full-Stack Engineer job description |
| `README.md` | Full documentation |

---

## 🚀 Setup & Run

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- An existing **n8n** container (or use the commented-out service in `docker-compose.yml`)
- ~8GB disk space for the AI model

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ResumeForge-AI.git
cd ResumeForge-AI
```

### Step 2: Start the Services

```powershell
# Option A: Automated setup (recommended)
.\scripts\setup.ps1

# Option B: Manual setup
docker compose up -d --build
# Wait for services to start, then pull the AI model:
docker exec resumeforge-ollama ollama pull mistral:7b
```

This will:
- Build the Python FastAPI container (includes TeX Live)
- Start the Ollama AI server and pull the model (~4GB download)
- Auto-detect and connect your existing n8n container to the shared network

### Step 3: Import the n8n Workflow

1. Open your n8n UI (default: `http://localhost:5678`)
2. Go to **Workflows → Import from File**
3. Select `n8n-workflow/resumeforge_workflow.json`
4. Click **Activate** to enable the webhook

### Step 4: Test the Pipeline

```powershell
.\scripts\test_pipeline.ps1
```

Or test manually via curl:

```bash
curl -X POST http://localhost:5678/webhook/resumeforge \
  -F "file=@test_data/sample_resume.tex" \
  -F "job_description=$(cat test_data/sample_jd.txt)" \
  -F "keywords=Python, AWS, Docker, Kubernetes" \
  -F "custom_instructions=Focus on backend and cloud experience"
```

### Step 5: Direct API Access (Optional)

You can also hit the FastAPI backend directly:

- **API Base:** `http://localhost:8000`
- **Swagger Docs:** `http://localhost:8000/docs`
- **Full Pipeline:** `POST http://localhost:8000/full-pipeline`

---

## 📊 Pipeline Flow

```
User submits (resume + JD + keywords)
        ↓
[n8n Webhook] → [Parse Resume] → [Preprocess]
        ↓
[AI Optimization via Ollama] → [Validate JSON]
        ↓                           ↓
[Generate LaTeX] → [PDF]    [ATS Analysis]
        ↓                           ↓
        └──────── [Output] ─────────┘
                    ↓
    PDF + LaTeX + ATS Report + Suggestions
```

---

## ⚙️ Configuration

### Changing the AI Model

Edit `docker-compose.yml` → `OLLAMA_MODEL` environment variable:

| RAM | GPU | Recommended Model |
|-----|-----|-------------------|
| ≥16GB | NVIDIA | `llama3:8b` |
| 8-16GB | None | `mistral:7b` (default) |
| ≤8GB | None | `phi3:mini` |

Then pull the new model:
```bash
docker exec resumeforge-ollama ollama pull <model-name>
```

### Connecting an Existing n8n Container

```bash
docker network connect resumeforge-network <your-n8n-container-name>
```

Inside n8n, use `http://resumeforge-api:8000` as the API base URL.

---

## 📤 Output

The system returns:
- ✅ **Optimized PDF** — Professional, ATS-friendly resume
- ✅ **LaTeX Source** — Editable `.tex` file
- ✅ **ATS Score** — Match percentage with grade (target ≥ 90%)
- ✅ **Keyword Analysis** — Matched vs missing keywords
- ✅ **Before vs After** — Comparison of original and optimized content
- ✅ **Suggestions** — Further improvement recommendations
