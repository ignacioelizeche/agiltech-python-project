import os
import base64
from typing import List
from io import BytesIO
from PyPDF2 import PdfMerger, PdfReader
from fastapi import HTTPException

def validate_and_merge_pdfs(files: List[str], download_path: str) -> str:
    pdf_paths = []
    for idx, file_base64 in enumerate(files):
        pdf_data = base64.b64decode(file_base64)

        # Validar PDF
        try:
            PdfReader(BytesIO(pdf_data))
        except Exception:
            raise HTTPException(status_code=400, detail=f"El archivo {idx+1} no es un PDF v�lido.")

        pdf_path = os.path.join(download_path, f"file_{idx + 1}.pdf")
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(pdf_data)
        pdf_paths.append(pdf_path)

    output_path = os.path.join(download_path, "merged.pdf")
    merger = PdfMerger()
    for pdf_path in pdf_paths:
        merger.append(pdf_path)
    merger.write(output_path)
    merger.close()

    # Eliminar los archivos individuales
    for pdf_path in pdf_paths:
        os.remove(pdf_path)

    return output_path

