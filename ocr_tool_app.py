import base64
import tempfile
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.ocrtext import ocr_pdf_and_return_base64

app = FastAPI(
    title="OCR Tools API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    servers=[
        {"url": "/ocrtools", "description": "OCR Tools Server"}
    ]
)

class OCRRequest(BaseModel):
    filebase64: str

@app.post("/ocrpdf")
async def ocr_pdf_endpoint(request: OCRRequest):
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
