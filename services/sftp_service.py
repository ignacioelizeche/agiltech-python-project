import os
import zipfile
from io import BytesIO
from ftplib import FTP_TLS

FILE_PREFIXES = ["E156F029", "EMAES029"]

def download_from_sftp(host: str, username: str, password: str, directory: str, download_path: str) -> BytesIO:
    os.makedirs(download_path, exist_ok=True)

    ftps = FTP_TLS()
    # conexión explícita TLS en el puerto 990
    ftps.connect(host, 990, timeout=15)
    ftps.auth()  # inicia TLS
    ftps.login(username, password)
    ftps.prot_p()  # protege canal de datos

    # cambiar al directorio solicitado
    ftps.cwd(directory)

    # listar y filtrar
    archivos = ftps.nlst()
    seleccionados = [f for f in archivos if any(f.startswith(p) for p in FILE_PREFIXES)]

    if not seleccionados:
        ftps.quit()
        raise Exception("No se encontraron archivos con los prefijos e156f029 o EMAES029")

    for archivo in seleccionados:
        local_path = os.path.join(download_path, archivo)
        with open(local_path, "wb") as f:
            ftps.retrbinary(f"RETR " + archivo, f.write)

    ftps.quit()

    # generar ZIP en memoria
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for archivo in seleccionados:
            ruta_local = os.path.join(download_path, archivo)
            zipf.write(ruta_local, arcname=archivo)

    zip_buffer.seek(0)
    return zip_buffer
