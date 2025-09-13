import os
from pathlib import Path
import json
import zipfile
import tempfile
import uuid
from dotenv import load_dotenv
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType as MediaType
from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import ExtractPDFResult
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import ExtractPDFParams
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import ExtractElementType
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_renditions_element_type import ExtractRenditionsElementType
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.table_structure_type import TableStructureType

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

def extract_pdf(input_pdf_path):
    """
    Extract text, tables, and figures from a PDF file.
    
    Args:
        input_pdf_path (str): Path to the input PDF file
        
    Returns:
        str: Path to the generated output folder
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("Missing CLIENT_ID / CLIENT_SECRET")
    
    input_path = Path(input_pdf_path)
    if not input_path.exists():
        raise FileNotFoundError(f"PDF file not found: {input_pdf_path}")
    
    # Generate unique folder name using UUID
    unique_id = str(uuid.uuid4())
    output_dir = Path("generated") / unique_id
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)
    (output_dir / "tables").mkdir(exist_ok=True)
    
    try:
        # Initialize Adobe PDF Services
        creds = ServicePrincipalCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        svc = PDFServices(credentials=creds)
        
        # Upload PDF to Adobe
        with input_path.open("rb") as f:
            asset = svc.upload(input_stream=f.read(), mime_type=MediaType.PDF)
        
        # Configure extraction parameters
        params = ExtractPDFParams(
            elements_to_extract=[ExtractElementType.TEXT, ExtractElementType.TABLES],
            elements_to_extract_renditions=[ExtractRenditionsElementType.TABLES, ExtractRenditionsElementType.FIGURES],
            table_structure_type=TableStructureType.CSV
        )
        
        # Submit extraction job
        job = ExtractPDFJob(input_asset=asset, extract_pdf_params=params)
        location = svc.submit(job)
        resp = svc.get_job_result(location, ExtractPDFResult)
        cloud_asset = resp.get_result().get_resource()
        stream_asset = svc.get_content(cloud_asset)
        
        # Process ZIP result
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
            temp_zip.write(stream_asset.get_input_stream())
            temp_zip_path = temp_zip.name
        
        with zipfile.ZipFile(temp_zip_path, "r") as z:
            for file_info in z.infolist():
                if file_info.filename == "structuredData.json":
                    data = json.loads(z.read(file_info).decode("utf-8"))
                    (output_dir / "structuredData.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
                    
                    # Extract text content
                    text_lines = []
                    def extract_text(node):
                        if isinstance(node, dict):
                            for k in ("Text", "text", "content", "title", "altText"):
                                v = node.get(k)
                                if isinstance(v, str) and v.strip():
                                    text_lines.append(v.strip())
                            for v in node.values():
                                extract_text(v)
                        elif isinstance(node, list):
                            for v in node:
                                extract_text(v)
                    
                    extract_text(data)
                    unique_text = list(dict.fromkeys(text_lines))
                    (output_dir / "text.txt").write_text("\n".join(unique_text), encoding="utf-8")
                
                elif "figure" in file_info.filename.lower() and file_info.filename.endswith((".png", ".jpg", ".jpeg")):
                    filename = Path(file_info.filename).name
                    (output_dir / "figures" / filename).write_bytes(z.read(file_info))
                
                elif "table" in file_info.filename.lower() and file_info.filename.endswith((".png", ".csv", ".jpg", ".jpeg")):
                    filename = Path(file_info.filename).name
                    if filename:
                        (output_dir / "tables" / filename).write_bytes(z.read(file_info))
        
        # Clean up temporary file
        os.unlink(temp_zip_path)
        
        return str(output_dir)
        
    except Exception as e:
        # Clean up on error
        if 'output_dir' in locals():
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
        raise e

if __name__ == "__main__":
    # For testing purposes
    input_pdf = "input.pdf"
    if Path(input_pdf).exists():
        output_folder = extract_pdf(input_pdf)
        print(f"Extraction complete! Output folder: {output_folder}")
    else:
        print(f"Please place a PDF file named '{input_pdf}' in the current directory")