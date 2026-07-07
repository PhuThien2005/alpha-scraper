import os
from dotenv import load_dotenv

from scraper import run_scraper
from upload_to_gcs import upload_to_gcs_delta, trigger_vertex_rag_import

def main():
    load_dotenv()
    MARKDOWN_FOLDER = "./articles"
    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

    print("================ DAILY JOB PIPELINE START ================\n")

    # Step 1: Scrape latest data
    run_scraper()

    if os.path.exists(MARKDOWN_FOLDER):
        # Step 2: Delta upload to GCS
        files_to_update = upload_to_gcs_delta(MARKDOWN_FOLDER, BUCKET_NAME)

        # Step 3: Trigger RAG embedding for updated files
        trigger_vertex_rag_import(files_to_update, BUCKET_NAME)
    else:
        print(f"Error: Folder '{MARKDOWN_FOLDER}' does not exist.")

    print("\n================ DAILY JOB PIPELINE END ================")

if __name__ == "__main__":
    main()