import os, zipfile
from io import BytesIO
from ftplib import FTP_TLS
from datetime import datetime
from typing import List

def download_from_sftp(host: str, username: str, password: str, directory: str,
                       download_path: str, filename_startswith: List[str] = [],
                       from_date: str = "") -> BytesIO:
    os.makedirs(download_path, exist_ok=True)

    ftps = FTP_TLS()
    ftps.connect(host, 990, timeout=15)
    ftps.auth()
    ftps.login(username, password)
    ftps.prot_p()
    ftps.cwd(directory)

    archivos = ftps.nlst()
    seleccionados = []

    for archivo in archivos:
        # Filtrado por prefijo
        if filename_startswith and not any(archivo.startswith(p) for p in filename_startswith):
            continue

        # Filtrado por fecha
        if from_date:
            mdtm = ftps.sendcmd(f"MDTM {archivo}")
            mod_time = datetime.strptime(mdtm[4:], "%Y%m%d%H%M%S")
            if mod_time < datetime.fromisoformat(from_date):
                continue

        seleccionados.append(archivo)

    if not seleccionados:
        ftps.quit()
        raise Exception("No se encontraron archivos con los criterios dados")

    # Descargar archivos
    for archivo in seleccionados:
        local_path = os.path.join(download_path, archivo)
        with open(local_path, "wb") as f:
            ftps.retrbinary(f"RETR " + archivo, f.write)

    ftps.quit()

    # Generar ZIP en memoria
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for archivo in seleccionados:
            zipf.write(os.path.join(download_path, archivo), arcname=archivo)

    zip_buffer.seek(0)
    return zip_buffer
