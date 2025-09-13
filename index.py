import os
from pathlib import Path
import json
import zipfile
import tempfile
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
INPUT_PDF = Path("input.pdf")
OUT_DIR = Path("out_demo")

if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit("Missing CLIENT_ID / CLIENT_SECRET")
if not INPUT_PDF.exists():
    raise SystemExit(f"Missing {INPUT_PDF}")

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "figures").mkdir(exist_ok=True)
(OUT_DIR / "tables").mkdir(exist_ok=True)

creds = ServicePrincipalCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
svc = PDFServices(credentials=creds)

with INPUT_PDF.open("rb") as f:
    asset = svc.upload(input_stream=f.read(), mime_type=MediaType.PDF)

params = ExtractPDFParams(
    elements_to_extract=[ExtractElementType.TEXT, ExtractElementType.TABLES],
    elements_to_extract_renditions=[ExtractRenditionsElementType.TABLES, ExtractRenditionsElementType.FIGURES],
    table_structure_type=TableStructureType.CSV
)

job = ExtractPDFJob(input_asset=asset, extract_pdf_params=params)
location = svc.submit(job)
resp = svc.get_job_result(location, ExtractPDFResult)
cloud_asset = resp.get_result().get_resource()
stream_asset = svc.get_content(cloud_asset)

with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
    temp_zip.write(stream_asset.get_input_stream())
    temp_zip_path = temp_zip.name

with zipfile.ZipFile(temp_zip_path, "r") as z:
    print("Files in ZIP:")
    for file_info in z.infolist():
        print(f"  {file_info.filename}")
    
    for file_info in z.infolist():
        if file_info.filename == "structuredData.json":
            data = json.loads(z.read(file_info).decode("utf-8"))
            (OUT_DIR / "structuredData.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
            
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
            (OUT_DIR / "text.txt").write_text("\n".join(unique_text), encoding="utf-8")
        
        elif "figure" in file_info.filename.lower() and file_info.filename.endswith((".png", ".jpg", ".jpeg")):
            filename = Path(file_info.filename).name
            print(f"Extracting figure: {filename}")
            (OUT_DIR / "figures" / filename).write_bytes(z.read(file_info))
        
        elif "table" in file_info.filename.lower() and file_info.filename.endswith((".png", ".csv", ".jpg", ".jpeg")):
            filename = Path(file_info.filename).name
            print(f"Extracting table: {filename}")
            if filename:
                (OUT_DIR / "tables" / filename).write_bytes(z.read(file_info))

os.unlink(temp_zip_path)
print(f"Done. Check {OUT_DIR} folder.")