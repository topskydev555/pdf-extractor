#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
import dropbox
from dropbox.files import WriteMode, UploadSessionCursor, CommitInfo
from dropbox.exceptions import ApiError, AuthError

load_dotenv()

# 8 MB chunks for large files; Dropbox requires chunked upload >150 MB
CHUNK_SIZE = 8 * 1024 * 1024
LARGE_FILE_THRESHOLD = 150 * 1024 * 1024

def upload_small_file(dbx: dropbox.Dropbox, local_path: Path, dropbox_path: str):
    """Upload small file (<150MB) in one request."""
    with local_path.open("rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=WriteMode("overwrite"))

def upload_large_file(dbx: dropbox.Dropbox, local_path: Path, dropbox_path: str):
    """Upload large file (>150MB) using chunked upload."""
    size = local_path.stat().st_size
    with local_path.open("rb") as f:
        # Start upload session
        session_start = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
        cursor = UploadSessionCursor(session_id=session_start.session_id, offset=f.tell())
        commit = CommitInfo(path=dropbox_path, mode=WriteMode("overwrite"))

        while f.tell() < size:
            if (size - f.tell()) <= CHUNK_SIZE:
                dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                break
            dbx.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
            cursor.offset = f.tell()

def create_shared_link(dbx: dropbox.Dropbox, dropbox_path: str):
    """Create or get existing shared link for a path."""
    try:
        # Try to create a new shared link with public visibility
        from dropbox.sharing import SharedLinkSettings, RequestedVisibility
        
        settings = SharedLinkSettings(
            requested_visibility=RequestedVisibility.public,
            audience=dropbox.sharing.LinkAudience.public,
            access=dropbox.sharing.RequestedLinkAccessLevel.viewer
        )
        
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(
            path=dropbox_path,
            settings=settings
        )
        return shared_link_metadata.url
        
    except ApiError as e:
        if e.error.is_shared_link_already_exists():
            # Get existing shared link
            try:
                links = dbx.sharing_list_shared_links(path=dropbox_path)
                if links.links:
                    return links.links[0].url
            except:
                pass
        
        # Fallback: try creating a simple shared link without special settings
        try:
            shared_link_metadata = dbx.sharing_create_shared_link(path=dropbox_path)
            return shared_link_metadata.url
        except:
            pass
    
    return None

def upload_folder_to_dropbox(folder_path):
    """
    Upload a folder and all its contents to Dropbox using official SDK.
    
    Args:
        folder_path (str): Path to the local folder to upload
        
    Returns:
        dict: Upload result information
    """
    token = os.getenv("DROPBOX_TOKEN")
    if not token:
        raise ValueError("Missing DROPBOX_TOKEN in environment variables")
    
    folder_path = Path(folder_path).resolve()
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    
    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    try:
        dbx = dropbox.Dropbox(token)
        # Verify connection
        dbx.users_get_current_account()
    except AuthError:
        raise ValueError("Invalid Dropbox token")
    except Exception as e:
        raise Exception(f"Failed to connect to Dropbox: {str(e)}")
    
    # Generate Dropbox destination path
    folder_name = folder_path.name
    dropbox_dest_root = f"/pdf_extractions/{folder_name}"
    
    # Ensure root folder exists
    try:
        dbx.files_create_folder_v2(dropbox_dest_root)
    except ApiError:
        pass  # Folder already exists
    
    uploaded_files = []
    
    try:
        # Upload all files in the folder recursively
        for file_path in folder_path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(folder_path).as_posix()
                dropbox_file_path = f"{dropbox_dest_root}/{relative_path}"
                file_size = file_path.stat().st_size
                
                print(f"Uploading: {file_path} -> {dropbox_file_path} ({file_size} bytes)")
                
                if file_size > LARGE_FILE_THRESHOLD:
                    upload_large_file(dbx, file_path, dropbox_file_path)
                else:
                    upload_small_file(dbx, file_path, dropbox_file_path)
                
                uploaded_files.append(dropbox_file_path)
        
        # Create shared link for the folder
        shared_link = create_shared_link(dbx, dropbox_dest_root)
        
        # Generate direct view link (converts share link to direct view)
        view_link = None
        if shared_link:
            # Convert Dropbox share link to direct view link
            if "dropbox.com" in shared_link:
                view_link = shared_link.replace("?dl=0", "?dl=1") if "?dl=0" in shared_link else shared_link
                # Ensure it's a view link, not download
                if "?dl=1" in view_link:
                    view_link = view_link.replace("?dl=1", "?dl=0")
        
        return {
            "dropbox_folder_path": dropbox_dest_root,
            "uploaded_files": uploaded_files,
            "shared_link": shared_link,
            "view_link": view_link or shared_link,
            "total_files": len(uploaded_files),
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_files)} files to Dropbox"
        }
        
    except Exception as e:
        raise Exception(f"Dropbox upload failed: {str(e)}")

def upload_single_file_to_dropbox(file_path, dropbox_path=None):
    """
    Upload a single file to Dropbox using official SDK.
    
    Args:
        file_path (str): Path to the local file to upload
        dropbox_path (str, optional): Dropbox path where to upload the file
        
    Returns:
        dict: Upload result information
    """
    token = os.getenv("DROPBOX_TOKEN")
    if not token:
        raise ValueError("Missing DROPBOX_TOKEN in environment variables")
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    if not dropbox_path:
        dropbox_path = f"/pdf_extractions/{file_path.name}"
    
    try:
        dbx = dropbox.Dropbox(token)
        dbx.users_get_current_account()
    except AuthError:
        raise ValueError("Invalid Dropbox token")
    
    file_size = file_path.stat().st_size
    
    try:
        if file_size > LARGE_FILE_THRESHOLD:
            upload_large_file(dbx, file_path, dropbox_path)
        else:
            upload_small_file(dbx, file_path, dropbox_path)
        
        return {
            "status": "success",
            "dropbox_path": dropbox_path,
            "file_size": file_size
        }
    except Exception as e:
        raise Exception(f"Upload failed: {str(e)}")

if __name__ == "__main__":
    # Test the function
    test_folder = "generated"
    if Path(test_folder).exists():
        # Find first subfolder for testing
        subfolders = [d for d in Path(test_folder).iterdir() if d.is_dir()]
        if subfolders:
            test_path = subfolders[0]
            try:
                result = upload_folder_to_dropbox(str(test_path))
                print("Upload successful!")
                print(f"Dropbox folder: {result['dropbox_folder_path']}")
                print(f"Files uploaded: {result['total_files']}")
                if result.get('shared_link'):
                    print(f"Shared link: {result['shared_link']}")
                if result.get('view_link'):
                    print(f"View link: {result['view_link']}")
                    print(f"Click here to view: {result['view_link']}")
            except Exception as e:
                print(f"Upload failed: {e}")
        else:
            print(f"No subfolders found in '{test_folder}'")
    else:
        print(f"Test folder '{test_folder}' not found")
