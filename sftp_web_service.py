from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import paramiko
import os
from typing import List

app = FastAPI()

class SFTPRequest(BaseModel):
    host: str
    username: str
    password: str
    directory: str

DOWNLOAD_PATH = "./downloads"
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

@app.post("/download")
async def download_files(request: SFTPRequest):
    try:
        # Iniciar conexión SFTP
        transport = paramiko.Transport((request.host, 22))
        transport.connect(username=request.username, password=request.password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Obtener lista de archivos
        try:
            files = sftp.listdir(request.directory)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Directory not found")

        downloaded_files = []
        for file in files:
            remote_path = os.path.join(request.directory, file)
            local_path = os.path.join(DOWNLOAD_PATH, file)
            try:
                sftp.get(remote_path, local_path)
                downloaded_files.append(file)
            except Exception as e:
                print(f"Failed to download {file}: {e}")

        sftp.close()
        transport.close()

        return {"downloaded_files": downloaded_files}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

