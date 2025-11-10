from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.sftp_service import download_from_sftp
from fastapi.responses import Response
from typing import List, Optional

app = FastAPI(title="SFTP Tools API")

class SFTPRequest(BaseModel):
    host: str
    directory: str
    descarga_path: str
    username: str
    password: str
    filename_startswith: Optional[List[str]] = []  # array de prefijos
    from_date: Optional[str] = ""  # YYYY-MM-DD

@app.post("/sftpcopy")
async def sftp_copy(request: SFTPRequest):
    try:
        zip_buffer = download_from_sftp(
            host=request.host,
            username=request.username,
            password=request.password,
            directory=request.directory,
            download_path=request.descarga_path,
            filename_startswith=request.filename_startswith,
            from_date=request.from_date
        )

        headers = {"Content-Disposition": "attachment; filename=archivos_descargados.zip"}
        return Response(content=zip_buffer.read(), media_type="application/zip", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
