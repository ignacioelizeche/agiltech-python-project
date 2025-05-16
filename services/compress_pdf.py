import fitz  # PyMuPDF
import tempfile
import base64
from fastapi import HTTPException


def compress_pdf(base64_pdf: str, download_path: str) -> str:
    try:
        # Decodificar base64
        pdf_data = base64.b64decode(base64_pdf)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_in:
            tmp_in.write(pdf_data)
            input_path = tmp_in.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            output_path = tmp_out.name

        doc = fitz.open(input_path)
        new_doc = fitz.open()

        for page in doc:
            if is_blank_page(page):
                continue

            # Renderizar como imagen comprimida
            pix = page.get_pixmap(matrix=fitz.Matrix(0.7, 0.7), alpha=False)
            img_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            img_page.insert_image(page.rect, pixmap=pix)

        if len(new_doc) == 0:
            raise HTTPException(status_code=400)

        new_doc.save(output_path, garbage=4, deflate=True, clean=True)
        new_doc.close()
        doc.close()

        return output_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al comprimir el PDF: {str(e)}")


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
