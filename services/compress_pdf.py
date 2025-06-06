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
        "gs",  # En Windows: cambiar a "gswin64c" si hace falta
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/ebook",  # El más agresivo (puede pixelar imágenes)
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dColorImageDownsampleType=/Bicubic",
        "-dColorImageResolution=72",  # Baja resolución
        "-dGrayImageDownsampleType=/Bicubic",
        "-dGrayImageResolution=72",
        "-dMonoImageDownsampleType=/Subsample",
        "-dMonoImageResolution=72",
        f"-sOutputFile={output_file_path}",
        input_file_path,
    ]
# /screen, /ebook, /printer, /prepress


    subprocess.run(gs_command, check=True)

    # Borramos el archivo original
    os.remove(input_file_path)

    return output_file_path
