# ══════════════════════════════════════════════════════════
# ResumeForge AI — End-to-End Test Script
# ══════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     ResumeForge AI — Pipeline Test           ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Test 1: Health Check ─────────────────────────────────
Write-Host "[1/4] Testing API health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
    Write-Host "  ✓ API Status: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ API is not running. Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

# ── Test 2: Resume Parsing ───────────────────────────────
Write-Host "[2/4] Testing resume parsing..." -ForegroundColor Yellow
$resumePath = Join-Path $ProjectRoot "test_data\sample_resume.tex"
try {
    $form = @{
        file = Get-Item -Path $resumePath
    }
    $parseResult = Invoke-RestMethod -Uri "http://localhost:8000/parse-resume" `
        -Method POST -Form $form
    Write-Host "  ✓ Resume parsed: $($parseResult.word_count) words, $($parseResult.sections.Count) sections" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Resume parsing failed: $_" -ForegroundColor Red
}

# ── Test 3: ATS Analysis ────────────────────────────────
Write-Host "[3/4] Testing ATS analysis..." -ForegroundColor Yellow
$jdContent = Get-Content (Join-Path $ProjectRoot "test_data\sample_jd.txt") -Raw
$atsBody = @{
    resume_text = $parseResult.raw_text
    job_description = $jdContent
    keywords = @("Python", "AWS", "Docker", "Kubernetes")
} | ConvertTo-Json -Depth 5

try {
    $atsResult = Invoke-RestMethod -Uri "http://localhost:8000/analyze-ats" `
        -Method POST -Body $atsBody -ContentType "application/json"
    $report = $atsResult.report
    Write-Host "  ✓ ATS Score: $($report.ats_score)% (Grade: $($report.ats_grade))" -ForegroundColor Green
    Write-Host "    Keywords Matched: $($report.keyword_analysis.matched_count)/$($report.keyword_analysis.jd_keywords_total)" -ForegroundColor White
    Write-Host "    Missing Keywords: $($report.keyword_analysis.missing_count)" -ForegroundColor White
} catch {
    Write-Host "  ✗ ATS analysis failed: $_" -ForegroundColor Red
}

# ── Test 4: Full Pipeline ───────────────────────────────
Write-Host "[4/4] Testing full pipeline (this may take 2-5 minutes)..." -ForegroundColor Yellow
try {
    $form = @{
        file                = Get-Item -Path $resumePath
        job_description     = $jdContent
        keywords            = "Python, AWS, Docker, Kubernetes, TypeScript, React"
        custom_instructions = "Focus on backend and cloud experience. Quantify all achievements."
        section_preferences = '{"Projects": "Relevant Projects"}'
    }
    $pipelineResult = Invoke-RestMethod -Uri "http://localhost:8000/full-pipeline" `
        -Method POST -Form $form -TimeoutSec 600

    Write-Host "  ✓ Pipeline completed!" -ForegroundColor Green
    Write-Host "    ATS Score: $($pipelineResult.ats_report.ats_score)%" -ForegroundColor White
    Write-Host "    PDF: $($pipelineResult.pdf_filename)" -ForegroundColor White
    Write-Host "    Suggestions: $($pipelineResult.suggestions.Count)" -ForegroundColor White

    # Save PDF locally
    $outputDir = Join-Path $ProjectRoot "output"
    if (!(Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir | Out-Null }

    $pdfBytes = [System.Convert]::FromBase64String($pipelineResult.pdf_base64)
    $pdfPath = Join-Path $outputDir $pipelineResult.pdf_filename
    [System.IO.File]::WriteAllBytes($pdfPath, $pdfBytes)
    Write-Host "    ✓ PDF saved to: $pdfPath" -ForegroundColor Green

} catch {
    Write-Host "  ✗ Full pipeline failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Tests complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
