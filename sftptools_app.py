from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.sftp_service import download_from_sftp
from fastapi.responses import Response
from typing import List, Optional
import os

app = FastAPI(title="SFTP Tools API")

BASE_DOWNLOAD_PATH = "/opt/agiltech-python-project/downloads"

class SFTPRequest(BaseModel):
    host: str
    directory: str
    destination_folder: str           # nombre de carpeta que creará bajo downloads
    username: str
    password: str
    filename_startswith: Optional[List[str]] = []  # array de prefijos
    from_date: Optional[str] = ""                  # fecha mínima YYYY-MM-DD

@app.post("/sftpcopy")
async def sftp_copy(request: SFTPRequest):
    try:
        download_path = os.path.join(BASE_DOWNLOAD_PATH, request.destination_folder)

        zip_buffer = download_from_sftp(
            host=request.host,
            username=request.username,
            password=request.password,
            directory=request.directory,
            download_path=download_path,
            filename_startswith=request.filename_startswith,
            from_date=request.from_date
        )

        headers = {"Content-Disposition": f"attachment; filename={request.destination_folder}_archivos.zip"}
        return Response(content=zip_buffer.read(), media_type="application/zip", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
