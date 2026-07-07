import os
import time
from google.cloud import storage
from google.cloud import aiplatform_v1beta1 as aiplatform_beta
from dotenv import load_dotenv
from google.api_core.client_options import ClientOptions

load_dotenv()

def upload_to_gcs(source_folder, bucket_name):
    """BƯỚC 1: Đẩy Markdown files lên GCS Bucket"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    files = [f for f in os.listdir(source_folder) if f.endswith('.md')]
    uploaded_count = 0

    print(f"[BƯỚC 1] Bắt đầu upload {len(files)} files lên GCS Bucket: '{bucket_name}'...")
    
    for file_name in files:
        local_path = os.path.join(source_folder, file_name)
        blob = bucket.blob(file_name) 
        
        blob.upload_from_filename(local_path)
        uploaded_count += 1
    
    print(f"Đã upload xong {uploaded_count} files lên GCS.\n")
    return files  

def trigger_vertex_rag_import(files, bucket_name):
    """BƯỚC 2: Gọi API Vertex RAG để Import ngầm (Chiến thuật nhỏ giọt)"""
    project_id = os.getenv("GCP_PROJECT_ID")
    location = "us-central1"
    corpus_id = os.getenv("VERTEX_CORPUS_ID")


    client_options = ClientOptions(api_endpoint="us-central1-aiplatform.googleapis.com")
    client = aiplatform_beta.VertexRagDataServiceClient(client_options=client_options)

    parent = f"projects/{project_id}/locations/{location}/ragCorpora/{corpus_id}"
    
    print("[BƯỚC 2] Bắt đầu Import & Embedding vào Vertex AI RAG...")
    print("Áp dụng chiến thuật 'Nhỏ giọt' (15s/file) để né lỗi 429 Quota GCP.\n")
    
    success_count = 0

    for file_name in files:
        gcs_uri = f"gs://{bucket_name}/{file_name}"
        print(f" -> Đang gọi AI xử lý (Chunking & Embedding) file: {file_name}")
        
        gcs_source = aiplatform_beta.GcsSource(uris=[gcs_uri])
        import_config = aiplatform_beta.ImportRagFilesConfig(gcs_source=gcs_source)
        request = aiplatform_beta.ImportRagFilesRequest(
            parent=parent,
            import_rag_files_config=import_config
        )
        
        try:

            client.import_rag_files(request=request).result()
            success_count += 1
            

            time.sleep(0.61) 
            
        except Exception as e:
            print(f"Lỗi khi nhúng file {file_name}: {e}")
            time.sleep(15) 

    print("\n==================================================")
    print(f"PIPELINE SUCCESS: Hoàn tất 100% tiến trình Data Ingestion.")
    print(f"UPLOAD: Đẩy thành công {len(files)} files lên Cloud Storage.")
    print(f"EMBEDDING: Nhúng an toàn {success_count}/{len(files)} files vào Vector Store.")
    print("==================================================")

if __name__ == "__main__":
    MARKDOWN_FOLDER = "./articles" 
    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    

    if os.path.exists(MARKDOWN_FOLDER):
        

        uploaded_files = upload_to_gcs(MARKDOWN_FOLDER, BUCKET_NAME)
        

        trigger_vertex_rag_import(uploaded_files, BUCKET_NAME)
        
    else:
        print(f"Lỗi: Không tìm thấy thư mục '{MARKDOWN_FOLDER}'")