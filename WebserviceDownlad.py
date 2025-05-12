from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import base64
from PyPDF2 import PdfMerger
import paramiko
import os

app = FastAPI()

class SFTPRequest(BaseModel):
    host: str
    username: str
    password: str
    directory: str

@app.post("/sftpcopy")
async def sftp_copy(request: SFTPRequest):
    host = request.host
    username = request.username
    password = request.password
    directory = request.directory

    download_path = "./downloads"

    if not os.path.exists(download_path):
        os.makedirs(download_path)

    try:
        transport = paramiko.Transport((host, 22))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        for file in sftp.listdir(directory):
            local_path = os.path.join(download_path, file)
            remote_path = os.path.join(directory, file)
            sftp.get(remote_path, local_path)

        sftp.close()
        transport.close()

        return {"message": "Files downloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mergepdf")
async def merge_pdfs(files: List[str]):
    try:
        # Decodificar y guardar los PDFs
        pdf_paths = []
        for idx, file_base64 in enumerate(files):
            pdf_data = base64.b64decode(file_base64)
            pdf_path = f"./downloads/file_{idx + 1}.pdf"
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(pdf_data)
            pdf_paths.append(pdf_path)

        # Combinar los PDFs
        output_path = "./downloads/merged.pdf"
        merger = PdfMerger()
        for pdf_path in pdf_paths:
            merger.append(pdf_path)
        merger.write(output_path)
        merger.close()

        # Retornar el archivo PDF combinado como una descarga
        return FileResponse(output_path, media_type='application/pdf', headers={"Content-Disposition": "attachment; filename=merged.pdf"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("WebserviceDownlad:app", host="127.0.0.1", port=8000, reload=True)
