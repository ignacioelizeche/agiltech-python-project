from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import base64
import os

from services.sftp_service import download_from_sftp
from services.merge_pdf import validate_and_merge_pdfs
from services.compress_pdf import compress_pdf
from services.mergencompress import validate_merge_and_compress_pdfs

app = FastAPI()

class SFTPRequest(BaseModel):
    host: str
    username: str
    password: str
    directory: str

@app.post("/sftpcopy")
async def sftp_copy(request: SFTPRequest):
    try:
        download_from_sftp(
            host=request.host,
            username=request.username,
            password=request.password,
            directory=request.directory,
            download_path="./downloads"
        )
        return {"message": "Files downloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


class CompressRequest(BaseModel):
    file: str  # Base64

@app.post("/compresspdf")
async def compress_pdf_endpoint(request: CompressRequest):
    try:
        compressed_pdf_path = compress_pdf(request.file)
        return FileResponse(
            compressed_pdf_path,
            media_type="application/pdf",
            filename="compressed.pdf",
            background=None,  # Podés usar BackgroundTasks para borrar el archivo luego si querés
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PDFList(BaseModel):
    files: List[str]

@app.post("/merge-compress")
def merge_and_compress(data: PDFList):
    download_path = "/tmp"  # o cualquier otra ruta temporal válida

    output_path = validate_merge_and_compress_pdfs(data.files, download_path)

    try:
        with open(output_path, "rb") as f:
            encoded_pdf = base64.b64encode(f.read()).decode("utf-8")
        os.remove(output_path)
        return {"compressed_pdf_base64": encoded_pdf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo retornar el archivo: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
