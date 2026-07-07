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

def sync_to_gcs_and_rag(source_folder, bucket_name):
    project_id = os.getenv("GCP_PROJECT_ID")
    location = "us-central1"
    corpus_id = os.getenv("VERTEX_CORPUS_ID")
    
    # 1. Initialize clients
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    client_options = ClientOptions(api_endpoint=f"{location}-aiplatform.googleapis.com")
    rag_client = aiplatform_beta.VertexRagDataServiceClient(client_options=client_options)
    parent = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"

    # 2. Get Local State
    print("Scanning local files...")
    local_files = {}
    if os.path.exists(source_folder):
        for f in os.listdir(source_folder):
            if f.endswith('.md'):
                local_path = os.path.join(source_folder, f)
                local_files[f] = compute_local_md5(local_path)

    # 3. Get GCS State
    print("Scanning GCS bucket...")
    gcs_blobs = {blob.name: blob for blob in bucket.list_blobs()}

    # 4. Get Vertex RAG State
    print("Scanning Vertex RAG Corpus...")
    rag_files = {}
    request = aiplatform_beta.ListRagFilesRequest(parent=parent)
    # The pager handles pagination automatically
    for rag_file in rag_client.list_rag_files(request=request):
        rag_files[rag_file.display_name] = rag_file.name

    # 5. Determine Actions
    # 5.1 Deletions
    gcs_to_delete = list(set(gcs_blobs.keys()) - set(local_files.keys()))
    rag_to_delete = list(set(rag_files.keys()) - set(local_files.keys()))
    
    for idx, file_name in enumerate(gcs_to_delete, 1):
        print(f"[{idx}/{len(gcs_to_delete)}] Deleting from GCS: {file_name}")
        gcs_blobs[file_name].delete()

    for idx, file_name in enumerate(rag_to_delete, 1):
        print(f"[{idx}/{len(rag_to_delete)}] Deleting from RAG: {file_name}")
        max_retries_del = 4
        for attempt in range(max_retries_del):
            try:
                delete_request = aiplatform_beta.DeleteRagFileRequest(name=rag_files[file_name])
                rag_client.delete_rag_file(request=delete_request)
                time.sleep(0.5)
                break
            except Exception as e:
                if "429" in str(e) or attempt < max_retries_del - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"Failed to delete {file_name} from RAG: {e}")

    # 5.2 Uploads & Imports
    files_to_import_to_rag = []
    added_count = updated_count = skipped_count = 0
    
    print(f"\nComparing {len(local_files)} files with GCS & RAG...")
    for file_name, local_md5 in local_files.items():
        # Check if file needs to be pushed to GCS (missing or hash mismatch)
        needs_gcs_upload = False
        if file_name not in gcs_blobs or gcs_blobs[file_name].md5_hash != local_md5:
            needs_gcs_upload = True

        if file_name not in rag_files:
            # Missing in RAG -> It is a new Add
            added_count += 1
            if needs_gcs_upload:
                local_path = os.path.join(source_folder, file_name)
                bucket.blob(file_name).upload_from_filename(local_path)
            files_to_import_to_rag.append(file_name)
            
        else:
            # Exists in RAG -> Check if we need to update based on GCS MD5
            if needs_gcs_upload:
                updated_count += 1
                # Content changed, delete old version from RAG first
                print(f"Updating {file_name}: Deleting old version from RAG first...")
                max_retries_del = 4
                for attempt in range(max_retries_del):
                    try:
                        delete_request = aiplatform_beta.DeleteRagFileRequest(name=rag_files[file_name])
                        rag_client.delete_rag_file(request=delete_request)
                        time.sleep(0.5)
                        break
                    except Exception as e:
                        if "429" in str(e) or attempt < max_retries_del - 1:
                            time.sleep(5 * (attempt + 1))
                        else:
                            print(f"Warning: Failed to delete old {file_name} from RAG: {e}")
                
                # Push new version to GCS
                local_path = os.path.join(source_folder, file_name)
                bucket.blob(file_name).upload_from_filename(local_path)
                files_to_import_to_rag.append(file_name)
                
            else:
                # Exists in RAG and content hasn't changed
                skipped_count += 1

    # 6. Setup Chunking Config
    chunking_config = aiplatform_beta.RagFileChunkingConfig(
        chunk_size=1024,
        chunk_overlap=256
    )

    total_import = len(files_to_import_to_rag)
    
    if total_import > 0:
        print(f"\nTriggering embedding for {total_import} files...")
        
    batch_size = 10
    files_to_import = files_to_import_to_rag.copy()
    max_passes = 10
    pass_num = 1

    while files_to_import and pass_num <= max_passes:
        print(f"\n--- PASS {pass_num}: Importing {len(files_to_import)} files in batches of {batch_size} ---")
        failed_in_this_pass = []
        
        gcs_uris = [f"gs://{bucket_name}/{f}" for f in files_to_import]
        
        for i in range(0, len(gcs_uris), batch_size):
            batch_uris = gcs_uris[i:i + batch_size]
            batch_filenames = files_to_import[i:i + batch_size]
            
            print(f"Importing batch of {len(batch_uris)} files (starting with {batch_filenames[0]})...")
            
            gcs_source = aiplatform_beta.GcsSource(uris=batch_uris)
            import_config = aiplatform_beta.ImportRagFilesConfig(gcs_source=gcs_source)
            import_request = aiplatform_beta.ImportRagFilesRequest(parent=parent, import_rag_files_config=import_config)

            try:
                response = rag_client.import_rag_files(request=import_request).result()
                if response.failed_rag_files_count > 0:
                    print(f" -> Partial failure detected in batch. Will verify later.")
                    failed_in_this_pass.extend(batch_filenames)
                else:
                    print(f" -> Batch succeeded.")
            except Exception as e:
                print(f" -> Batch failed with API limit/error. Will retry. Error snippet: {str(e)[:100]}...")
                failed_in_this_pass.extend(batch_filenames)
                
            time.sleep(3) # Nghỉ 3s giữa các batch
            
        if failed_in_this_pass:
            print("\nVerifying which files actually failed by checking Vertex RAG Corpus...")
            # Fetch the latest RAG corpus state
            current_rag_files = []
            for rag_file in rag_client.list_rag_files(request=aiplatform_beta.ListRagFilesRequest(parent=parent)):
                current_rag_files.append(rag_file.display_name)
                
            # Keep only files that are still missing
            files_to_import = [f for f in failed_in_this_pass if f not in current_rag_files]
            
            if files_to_import:
                print(f"Confirmed: {len(files_to_import)} files failed. Retrying them in the next pass.")
                time.sleep(5) # Nghỉ 5s trước khi chạy pass tiếp theo
            else:
                print("Verification complete: All files in this pass actually succeeded!")
        else:
            files_to_import = [] # Everything succeeded
            
        pass_num += 1

    failed_import_count = len(files_to_import)
    success_import_count = total_import - failed_import_count

    if total_import > 0:
        print(f"\nEMBEDDING COMPLETE: {success_import_count} succeeded, {failed_import_count} failed out of {total_import} submitted.")
        
        if failed_import_count > 0:
            print("\n--- Identifying Failed Files ---")
            print("The following files failed to import after all retries:")
            for f in files_to_import:
                print(f"  - {f}")

    print(f"\n================ FINAL SYNC REPORT ================")
    print(f"   - Added  : {added_count} (Successfully Embedded: {success_import_count}/{total_import})")
    print(f"   - Updated: {updated_count}")
    print(f"   - Skipped: {skipped_count}")
    print(f"   - Deleted: {len(gcs_to_delete)} (from GCS), {len(rag_to_delete)} (from RAG)")
    print(f"===================================================\n")