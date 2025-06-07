from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import base64
import os

from services.merge_pdf import validate_and_merge_pdfs
from services.compress_pdf import compress_pdf
from services.mergencompress import validate_merge_and_compress_pdfs

app = FastAPI(
    title="PDF Tools API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    servers=[
        {"url": "/pdftools", "description": "PDF Tools Server"}
    ]
)

class CompressRequest(BaseModel):
    file: str  # Base64

class PDFList(BaseModel):
    files: List[str]

@app.post("/mergepdf")
async def merge_pdfs(files: List[str]):
    try:
        output_path = validate_and_merge_pdfs(files, "./downloads")
        return FileResponse(
            output_path,
            media_type='application/pdf',
            headers={"Content-Disposition": "attachment; filename=merged.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compresspdf")
async def compress_pdf_endpoint(request: CompressRequest):
    try:
        compressed_pdf_path = compress_pdf(request.file)
        return FileResponse(
            compressed_pdf_path,
            media_type="application/pdf",
            filename="compressed.pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/merge-compress")
def merge_and_compress(data: PDFList):
    download_path = "/tmp"
    output_path = validate_merge_and_compress_pdfs(data.files, download_path)

    try:
        with open(output_path, "rb") as f:
            encoded_pdf = base64.b64encode(f.read()).decode("utf-8")
        os.remove(output_path)
        return {"compressed_pdf_base64": encoded_pdf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo retornar el archivo: {str(e)}")

