import os
import paramiko

def download_from_sftp(host: str, username: str, password: str, directory: str, download_path: str):
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    for file in sftp.listdir(directory):
        local_path = os.path.join(download_path, file)
        remote_path = os.path.join(directory, file)
        sftp.get(remote_path, local_path)

    sftp.close()
    transport.close()
