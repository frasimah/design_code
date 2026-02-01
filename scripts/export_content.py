
import zipfile
from pathlib import Path
import datetime

def export_content():
    # Define paths
    ROOT_DIR = Path(__file__).parent.parent
    DATA_DIR = ROOT_DIR / "data"
    OUTPUT_DIR = ROOT_DIR
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = OUTPUT_DIR / f"lick_brick_content_{timestamp}.zip"
    
    # Files/Dirs to include
    include_paths = [
        DATA_DIR / "processed" / "full_catalog.json",
        DATA_DIR / "embeddings"
    ]
    
    print("📦 Starting content export...")
    
    count = 0
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for path in include_paths:
            if not path.exists():
                print(f"⚠️ Warning: Path not found: {path}")
                continue
                
            if path.is_file():
                # Store relative to ROOT_DIR, effectively keeping "data/processed/..." structure
                arcname = path.relative_to(ROOT_DIR)
                zipf.write(path, arcname)
                print(f"  + {arcname}")
                count += 1
            elif path.is_dir():
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(ROOT_DIR)
                        zipf.write(file_path, arcname)
                        count += 1
                print(f"  + {path.relative_to(ROOT_DIR)}/ (recursive)")

    print("\n✅ Export complete!")
    print(f"📁 Archive: {zip_filename}")
    print(f"📄 Files included: {count}")
    print("\nTo restore on server, simply unzip this archive in the project root.")

if __name__ == "__main__":
    export_content()
