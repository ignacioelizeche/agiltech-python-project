import os
import base64
import tempfile
from typing import List
from io import BytesIO
from PyPDF2 import PdfMerger, PdfReader
import fitz  # PyMuPDF
from fastapi import HTTPException


def is_blank_page(page, margin_ratio=0.2, min_chars=10):
    height = page.rect.height
    header_limit = height * margin_ratio
    footer_limit = height * (1 - margin_ratio)

    def is_central(y): return header_limit < y < footer_limit

    blocks = page.get_text("dict")["blocks"]
    for b in blocks:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                y = span["bbox"][1]
                if is_central(y) and len(span["text"].strip()) >= min_chars:
                    return False

    for d in page.get_drawings():
        yc = (d["rect"].y0 + d["rect"].y1) / 2
        if is_central(yc):
            return False

    for img in page.get_images(full=True):
        xref = img[0]
        for r in page.get_image_rects(xref):
            yc = (r.y0 + r.y1) / 2
            if is_central(yc):
                return False

    return True


def validate_merge_and_compress_pdfs(files: List[str], download_path: str) -> str:
    pdf_paths = []
    for idx, file_base64 in enumerate(files):
        try:
            pdf_data = base64.b64decode(file_base64)
            PdfReader(BytesIO(pdf_data))
        except Exception:
            raise HTTPException(status_code=400, detail=f"El archivo {idx+1} no es un PDF valido.")

        pdf_path = os.path.join(download_path, f"file_{idx + 1}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_data)
        pdf_paths.append(pdf_path)

    merged_path = os.path.join(download_path, "merged.pdf")
    merger = PdfMerger()
    for pdf_path in pdf_paths:
        merger.append(pdf_path)
    merger.write(merged_path)
    merger.close()

    for pdf_path in pdf_paths:
        os.remove(pdf_path)

    # Comprimir PDF resultante
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            compressed_path = tmp_out.name

        doc = fitz.open(merged_path)
        new_doc = fitz.open()

        for page in doc:
            if is_blank_page(page):
                continue
            pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7), alpha=False)
            img_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            img_page.insert_image(page.rect, pixmap=pix)

        if len(new_doc) == 0:
            raise HTTPException(status_code=400, detail="El PDF resultante esta vacio despues de la compresion.")

        new_doc.save(compressed_path, garbage=4, deflate=True, clean=True)
        new_doc.close()
        doc.close()
        os.remove(merged_path)

        return compressed_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al comprimir el PDF: {str(e)}")

