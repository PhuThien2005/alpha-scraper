import os
import time
from google.cloud import storage
from google.cloud import aiplatform_v1beta1 as aiplatform_beta
from dotenv import load_dotenv
from google.api_core.client_options import ClientOptions

load_dotenv()

def upload_to_gcs(source_folder, bucket_name):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    files = [f for f in os.listdir(source_folder) if f.endswith('.md')]
    uploaded_count = 0

    print(f"Upload {len(files)} files lên GCS Bucket: '{bucket_name}'...")
    
    for file_name in files:
        local_path = os.path.join(source_folder, file_name)
        blob = bucket.blob(file_name) 
        
        blob.upload_from_filename(local_path)
        uploaded_count += 1
    
    print(f"Upload xong {uploaded_count} files lên GCS.\n")
    return files  

def trigger_vertex_rag_import(files, bucket_name):

    project_id = os.getenv("GCP_PROJECT_ID")
    location = "us-central1"
    corpus_id = os.getenv("VERTEX_CORPUS_ID")

    client_options = ClientOptions(api_endpoint="us-central1-aiplatform.googleapis.com")
    client = aiplatform_beta.VertexRagDataServiceClient(client_options=client_options)

    parent = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
    
    print("Import & Embedding vào Vertex AI RAG...\n")
    
    success_count = 0
    max_retries = 3

    for file_name in files:
        gcs_uri = f"gs://{bucket_name}/{file_name}"

        print(f"{success_count + 1}. Chunking & Embedding file: {file_name}")
        
        gcs_source = aiplatform_beta.GcsSource(uris=[gcs_uri])
        import_config = aiplatform_beta.ImportRagFilesConfig(gcs_source=gcs_source)
        request = aiplatform_beta.ImportRagFilesRequest(
            parent=parent,
            import_rag_files_config=import_config
        )
        
    
        for attempt in range(max_retries):
            try:
                client.import_rag_files(request=request).result()
                success_count += 1
                
                time.sleep(0.1) 
                
                break 
                
            except Exception as e:
                print(f"Lỗi lần {attempt + 1}/{max_retries} cho file {file_name}: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    print(f"Đang đợi {wait_time}s để thử lại...")
                    time.sleep(wait_time)
                else:
                    print(f"Bỏ qua file {file_name}.")
   

    print(f"\nUPLOAD thành công {len(files)} files lên Cloud Storage.")
    print(f"EMBEDDING {success_count}/{len(files)} files vào Vector Store.")

if __name__ == "__main__":
    MARKDOWN_FOLDER = "./articles" 
    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    

    if os.path.exists(MARKDOWN_FOLDER):
        

        uploaded_files = upload_to_gcs(MARKDOWN_FOLDER, BUCKET_NAME)
        

        trigger_vertex_rag_import(uploaded_files, BUCKET_NAME)
        
    else:
        print(f"Lỗi: Không tìm thấy thư mục '{MARKDOWN_FOLDER}'")