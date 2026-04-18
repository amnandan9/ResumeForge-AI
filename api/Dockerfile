FROM python:3.12-slim

# Install system dependencies: TeX Live for PDF generation, curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-recommended \
    latexmk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data for keyword extraction
# Use the CLI downloader to avoid circular import crash in nltk/__init__.py
RUN python -m nltk.downloader punkt punkt_tab stopwords averaged_perceptron_tagger averaged_perceptron_tagger_eng wordnet omw-1.4

# Copy application code
COPY . .

# Create directories for shared files and output
RUN mkdir -p /app/shared /app/output /app/templates

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
