from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from services.sftp_service import download_from_sftp

app = FastAPI(
    title="SFTP Tools API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    servers=[{"url": "/sftptools", "description": "SFTP Tools Server"}]
)

class SFTPRequest(BaseModel):
    host: str
    username: str
    password: str
    directory: str

@app.post("/sftpcopy")
async def sftp_copy(request: SFTPRequest):
    try:
        zip_buffer = download_from_sftp(
            host=request.host,
            username=request.username,
            password=request.password,
            directory=request.directory,
            download_path="../opt/procard"
        )

        headers = {"Content-Disposition": "attachment; filename=archivos_descargados.zip"}
        return Response(content=zip_buffer.read(), media_type="application/zip", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
