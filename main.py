from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import base64
import os

from services.sftp_service import download_from_sftp
from services.merge_pdf import validate_and_merge_pdfs
from services.compress_pdf import compress_pdf


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
        output_path = compress_pdf(request.file, download_path="./downloads")
        return FileResponse(
            output_path,
            media_type='application/pdf',
            headers={"Content-Disposition": "attachment; filename=compressed.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

