import fitz  # PyMuPDF
import tempfile
import base64
from fastapi import HTTPException

def compress_pdf(base64_pdf: str, download_path: str) -> str:
    try:
        # Crear archivo temporal del PDF original
        pdf_data = base64.b64decode(base64_pdf)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_in:
            tmp_in.write(pdf_data)
            input_path = tmp_in.name

        # Crear archivo de salida temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            output_path = tmp_out.name

        doc = fitz.open(input_path)
        new_doc = fitz.open()

        for page in doc:
            text = page.get_text().strip()
            if len(text) > 0 or len(page.get_images(full=True)) > 0:
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.show_pdf_page(page.rect, doc, page.number)
                
                # Comprimir imágenes
                for img in page.get_images(full=True):
                    xref = img[0]
                    doc._delete_object(xref)  # Eliminar imagen original (opcional)
                # No recomprime en este paso, solo limpia si es necesario

        new_doc.save(output_path, garbage=4, deflate=True, clean=True)
        new_doc.close()
        doc.close()

        return output_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al comprimir el PDF: {str(e)}")