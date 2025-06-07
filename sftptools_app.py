from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.sftp_service import download_from_sftp

app = FastAPI(
    title="SFTP Tools API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    servers=[
        {"url": "/sftptools", "description": "SFTP Tools Server"}
    ]
)

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

