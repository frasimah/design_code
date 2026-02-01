import google.generativeai as genai
import os
import time

# Configure API key (assumes GEMINI_API_KEY is in env or accessible)
# genai.configure(api_key=os.environ["GEMINI_API_KEY"])

class KnowledgeBase:
    def __init__(self, api_key=None):
        if api_key:
            genai.configure(api_key=api_key, transport="rest")
        self.model_name = "models/gemini-3-flash-preview" # Or updated version

    def upload_document(self, file_path, display_name=None):
        """
        Uploads a file to Gemini Files API.
        """
        try:
            print(f"Uploading {file_path}...")
            file_ref = genai.upload_file(
                path=file_path,
                display_name=display_name or os.path.basename(file_path)
            )
            print(f"Uploaded file '{file_ref.display_name}' URI: {file_ref.uri}")
            
            # Wait for processing to complete
            while file_ref.state.name == "PROCESSING":
                print('.', end='', flush=True)
                time.sleep(2)
                file_ref = genai.get_file(file_ref.name)
                
            if file_ref.state.name == "FAILED":
                raise ValueError(f"File processing failed: {file_ref.name}")
                
            print(f"File ready: {file_ref.name}")
            return file_ref
        except Exception as e:
            print(f"Error uploading file: {e}")
            return None

    def list_files(self):
        """List all uploaded files."""
        return list(genai.list_files())

    def get_all_active_files(self):
        """Returns a list of all active File objects ready for context."""
        all_files = self.list_files()
        active_files = [f for f in all_files if f.state.name == "ACTIVE"]
        print(f"KnowledgeBase: Found {len(active_files)} active files.")
        return active_files

    def create_chat_with_files(self, file_uris):
        """
        Creates a chat session with File Search enabled for the given files.
        Note: For standard flash model we usually pass files directly to generation request or create a cache.
        """
        # For 'gemini-1.5-flash' and newer, we can pass file URIs directly in history or system instruction
        # to effectively use them as context (Long Context).
        
        # Or use managed "tools" if "retrieval" tool is available (Semantic Retrieval).
        # Currently, simplest "File Search" is putting files in context.
        
        print(f"Initializing chat with {len(file_uris)} files...")
        
        # We assume file_uris are valid 'files/...' names from upload_file
        # Construct the history or system prompt
        
        # Note: Gemini 1.5+ handles 'file' objects in contents.
        # We need to fetch the file objects or construct parts with file_data/file_uri
        
        pass 
        # Implementation depends on exact method (Context Caching vs Direct Context)
        # For < 200 files, direct context is fine. For > 200, context caching is standard.

    def delete_file(self, file_name):
        """Deletes a file from Gemini storage."""
        try:
            genai.delete_file(file_name)
            print(f"Deleted {file_name}")
        except Exception as e:
            print(f"Error deleting file: {e}")

if __name__ == "__main__":
    # Batch upload execution
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY env var")
        exit(1)

    kb = KnowledgeBase(api_key=api_key)
    
    # Get current files to skip duplicates
    print("Checking existing files in Gemini...")
    existing_files = {f.display_name for f in kb.list_files()}
    print(f"Found {len(existing_files)} files already in Gemini.")
    
    docs_dir = "rag_documents"
    if os.path.exists(docs_dir):
        files = [f for f in os.listdir(docs_dir) if f.endswith('.txt')]
        print(f"Found {len(files)} total documents locally.")
        
        to_upload = [f for f in files if f not in existing_files]
        print(f"Will upload {len(to_upload)} new documents.")
        
        uploaded_uris = []
        for i, filename in enumerate(to_upload):
            file_path = os.path.join(docs_dir, filename)
            
            print(f"[{i+1}/{len(to_upload)}] ", end='')
            try:
                ref = kb.upload_document(file_path)
                if ref:
                    uploaded_uris.append(ref.uri)
                # Small delay to be gentle on API
                time.sleep(0.5)
            except Exception as e:
                print(f"Failed to upload {filename}: {e}")
                
        print(f"\nSuccessfully uploaded {len(uploaded_uris)} new files.")
    else:
        print(f"{docs_dir} does not exist. Run data_prep.py first.")
