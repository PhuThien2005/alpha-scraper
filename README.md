# OptiBot Mini-Clone

This repository contains a Python-based Daily Job Pipeline that scrapes OptiSigns support articles, converts them to Markdown, and synchronizes the files to Google Cloud Storage (GCS) and Google Vertex AI (Gemini). Only delta changes (new or modified files) are uploaded.

## 1. Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd <your-repo-name>
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv venv_alpha
   source venv_alpha/bin/activate  # On Windows: venv_alpha\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   - Copy the `.env.sample` file to `.env`:
     ```bash
     cp .env.sample .env
     ```
   - Fill in your actual GCP details in the `.env` file.
   - Place your Google Cloud service account JSON key in the root directory and name it `gcp-key.json` (ensure it is ignored by git).

## 2. How to Run Locally

With the virtual environment activated and `.env` configured, simply run:
```bash
python main.py
```
This will:
- Scrape Zendesk articles to the `articles/` folder.
- Hash and compare local files with GCS to find the delta.
- Upload only new/changed files to GCS.
- Trigger Vertex AI embedding for the updated files.

## 3. How to Run with Docker

1. **Build the image:**
   ```bash
   docker build -t optisigns-scraper .
   ```

2. **Run the container:**
   ```bash
   # Mount the GCP key and pass the env file
   docker run --env-file .env -v $(pwd)/gcp-key.json:/app/gcp-key.json optisigns-scraper
   ```

## 4. Daily Job Logs
*Insert your link to the GCP Cloud Run / Cloud Scheduler logs here after deploying.*
[Link to Daily Job Logs](#)

## 4. Chunking Strategy
*(Briefly explain your chunking strategy here. For example: "We rely on Vertex AI's default chunking strategy when importing files from GCS, which automatically parses markdown headings and paragraphs to preserve semantic context.")*

## 5. Assistant Screenshot
*Insert your screenshot of the Gemini/AI Studio assistant correctly answering the question: "How do I add a YouTube video?" with cited URLs here.*

![Assistant Screenshot](./screenshot.png)
