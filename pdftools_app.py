from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import base64
import os
from typing import Optional
import tempfile

from services.ocrtext import ocr_pdf_and_return_base64
from services.merge_pdf import validate_and_merge_pdfs
from services.compress_pdf import compress_pdf_base64
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
    filebase64: str  # Base64 obligatorio

class PDFList(BaseModel):
    filesbase64: List[str]

@app.post("/mergepdf")
async def merge_pdfs(payload: PDFList):  # <--- receives JSON object
    try:
        output_path = validate_and_merge_pdfs(payload.filesbase64, "/tmp")
        # Read and encode to base64
        with open(output_path, "rb") as f:
            merged_pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            "success": True,
            "filebase64": merged_pdf_base64
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compresspdf")
async def compress_pdf_endpoint(request: CompressRequest):
    try:
        # Use the automatic best compression (ignores quality parameter)
        compressed_base64 = compress_pdf_base64(request.filebase64)
        return {"success": True, "filebase64": compressed_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/merge-compress")
def merge_and_compress(data: PDFList):
    download_path = "/tmp"
    output_path = validate_merge_and_compress_pdfs(data.filesbase64, download_path)

    try:
        with open(output_path, "rb") as f:
            encoded_pdf = base64.b64encode(f.read()).decode("utf-8")
        os.remove(output_path)
        return {"success":True, "filebase64": encoded_pdf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo retornar el archivo: {str(e)}")


@app.post("/ocrpdf")
async def ocr_pdf_endpoint(request: CompressRequest):
    """
    Endpoint para aplicar OCR a un PDF usando servicio externo.
    Recibe un PDF en base64 y retorna el PDF procesado en base64.
    """
    try:
        # Decodificar el archivo base64
        pdf_data = base64.b64decode(request.filebase64)

        # Crear archivo temporal para el PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf.write(pdf_data)
            temp_pdf_path = temp_pdf.name

        try:
            # Llamar al servicio OCR
            result_base64 = ocr_pdf_and_return_base64(temp_pdf_path)
            return {"success": True, "filebase64": result_base64}

        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)

    except base64.binascii.Error:
        raise HTTPException(status_code=400, detail="Invalid base64 format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")
