# services/compress_pdf.py
import subprocess
import tempfile
import base64
import os


def compress_pdf(pdf_base64: str) -> str:
    # Decodifica el PDF en base64 a bytes
    pdf_bytes = base64.b64decode(pdf_base64)

    # Crea un archivo temporal con el PDF original
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_file:
        input_file.write(pdf_bytes)
        input_file_path = input_file.name

    # Define el nombre del archivo de salida
    output_file_path = input_file_path.replace(".pdf", "_compressed.pdf")

    # Comando de Ghostscript
    gs_command = [
        "gs",  # En Windows puede que necesites "gswin64c"
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/ebook",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dColorImageDownsampleType=/Bicubic",
        "-dColorImageResolution=72",
        "-dGrayImageDownsampleType=/Bicubic",
        "-dGrayImageResolution=72",
        "-dMonoImageDownsampleType=/Subsample",
        "-dMonoImageResolution=72",
        f"-sOutputFile={output_file_path}",
        input_file_path,
    ]

    # Ejecuta la compresión
    subprocess.run(gs_command, check=True)

    # Lee el archivo comprimido como bytes
    with open(output_file_path, "rb") as f:
        compressed_pdf_bytes = f.read()

    # Limpieza de archivos temporales
    os.remove(input_file_path)
    os.remove(output_file_path)

    # Codifica el PDF comprimido a base64 y lo devuelve
    return base64.b64encode(compressed_pdf_bytes).decode("utf-8")
