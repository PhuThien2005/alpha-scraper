import os
from dotenv import load_dotenv

from scraper import run_scraper
from upload_to_gcs import sync_to_gcs_and_rag

def main():
    load_dotenv()
    MARKDOWN_FOLDER = "./articles"
    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

    print("================ DAILY JOB PIPELINE START ================\n")

    # Step 1: Scrape latest data
    run_scraper()

    if os.path.exists(MARKDOWN_FOLDER):
        # Step 2 & 3: 3-way sync with GCS and Vertex RAG
        sync_to_gcs_and_rag(MARKDOWN_FOLDER, BUCKET_NAME)
    else:
        print(f"Error: Folder '{MARKDOWN_FOLDER}' does not exist.")

    print("\n================ DAILY JOB PIPELINE END ================")

if __name__ == "__main__":
    main()