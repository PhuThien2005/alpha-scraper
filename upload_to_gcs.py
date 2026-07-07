import os
import time
import hashlib
import base64
from google.cloud import storage
from google.cloud import aiplatform_v1beta1 as aiplatform_beta
from google.api_core.client_options import ClientOptions

def compute_local_md5(file_path):
    with open(file_path, "rb") as f:
        md5_hash = hashlib.md5(f.read()).digest()
        return base64.b64encode(md5_hash).decode('utf-8')

def upload_to_gcs_delta(source_folder, bucket_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    print("Syncing hash list from GCS...")
    existing_blobs = {blob.name: blob.md5_hash for blob in bucket.list_blobs()}
    files = [f for f in os.listdir(source_folder) if f.endswith('.md')]

    files_to_update = []
    skipped_count = updated_count = added_count = 0

    print(f"Comparing {len(files)} local files with GCS bucket '{bucket_name}'...")

    for file_name in files:
        local_path = os.path.join(source_folder, file_name)
        local_md5 = compute_local_md5(local_path)

        if file_name in existing_blobs:
            if existing_blobs[file_name] == local_md5:
                skipped_count += 1
                continue
            else:
                updated_count += 1
        else:
            added_count += 1

        blob = bucket.blob(file_name)
        blob.upload_from_filename(local_path)
        files_to_update.append(file_name)

    print(f"DELTA SYNC REPORT:")
    print(f"   - Added  : {added_count} files")
    print(f"   - Updated: {updated_count} files")
    print(f"   - Skipped: {skipped_count} files\n")

    return files_to_update

def trigger_vertex_rag_import(files, bucket_name):
    if not files:
        print("No new files. Skipping Vertex AI embedding.")
        return

    project_id = os.getenv("GCP_PROJECT_ID")
    location = "us-central1"
    corpus_id = os.getenv("VERTEX_CORPUS_ID")

    client_options = ClientOptions(api_endpoint="us-central1-aiplatform.googleapis.com")
    client = aiplatform_beta.VertexRagDataServiceClient(client_options=client_options)
    parent = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"

    print(f"Triggering embedding for {len(files)} changed files...")
    success_count = 0
    max_retries = 3

    for file_name in files:
        gcs_uri = f"gs://{bucket_name}/{file_name}"
        gcs_source = aiplatform_beta.GcsSource(uris=[gcs_uri])
        import_config = aiplatform_beta.ImportRagFilesConfig(gcs_source=gcs_source)
        request = aiplatform_beta.ImportRagFilesRequest(parent=parent, import_rag_files_config=import_config)

        for attempt in range(max_retries):
            try:
                client.import_rag_files(request=request).result()
                success_count += 1
                time.sleep(0.1)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"Skipped file {file_name}: {e}")

    print(f"EMBEDDING COMPLETE: {success_count}/{len(files)} files.")