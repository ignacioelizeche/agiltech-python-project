# services/compress_pdf.py
import subprocess
import tempfile
import base64
import os


def compress_pdf(pdf_base64: str) -> str:
    pdf_bytes = base64.b64decode(pdf_base64)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_file:
        input_file.write(pdf_bytes)
        input_file_path = input_file.name

    output_file_path = input_file_path.replace(".pdf", "_compressed.pdf")

    gs_command = [
        "gs",  # En Windows puede ser "gswin64c" o el path completo a ghostscript
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/ebook",  # /screen, /ebook, /printer, /prepress
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_file_path}",
        input_file_path,
    ]

    subprocess.run(gs_command, check=True)

    # Borramos el archivo original
    os.remove(input_file_path)

    return output_file_path