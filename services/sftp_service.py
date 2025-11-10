import os
import zipfile
from io import BytesIO
import paramiko

# Prefijos a descargar
FILE_PREFIXES = ["e156f029", "EMAES029"]

def download_from_sftp(host: str, username: str, password: str, directory: str, download_path: str) -> BytesIO:
    """
    Se conecta al servidor SFTP, descarga los archivos que comiencen con los prefijos definidos,
    los guarda localmente y devuelve un ZIP en memoria.
    """
    os.makedirs(download_path, exist_ok=True)

    # Conexión SFTP (puerto 22 — si es FTPS, se debe cambiar de librería)
    transport = paramiko.Transport((host, 990))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # Cambiar al directorio raíz (o al indicado)
    sftp.chdir(directory)

    # Listar y filtrar archivos
    all_files = sftp.listdir()
    filtered_files = [f for f in all_files if any(f.startswith(pref) for pref in FILE_PREFIXES)]

    if not filtered_files:
        sftp.close()
        transport.close()
        raise Exception("No se encontraron archivos con los prefijos e156f029 o EMAES029")

    # Descargar archivos seleccionados
    for file_name in filtered_files:
        remote_path = os.path.join(directory, file_name)
        local_path = os.path.join(download_path, file_name)
        sftp.get(remote_path, local_path)

    sftp.close()
    transport.close()

    # Crear ZIP en memoria
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_name in filtered_files:
            local_path = os.path.join(download_path, file_name)
            zipf.write(local_path, arcname=file_name)

    zip_buffer.seek(0)
    return zip_buffer
