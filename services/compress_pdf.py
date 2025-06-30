import base64
import pypdfium2 as pdfium
from pathlib import Path
from PIL import Image
import img2pdf
import os
import tempfile

def compress_pdf_base64(pdf_base64: str, escala: int = 2, calidad: int = 70) -> str:
    """
    Comprime un archivo PDF recibido en base64 y retorna el PDF comprimido también en base64.

    Parámetros:
    - pdf_base64: PDF original como string base64
    - escala: factor de escala para renderizar imágenes desde el PDF
    - calidad: calidad JPEG de compresión (1-100)

    Retorna:
    - PDF comprimido como string en base64
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_pdf_path = tmp_path / "original.pdf"
        output_pdf_path = tmp_path / "comprimido.pdf"

        # Guardar el PDF original desde base64
        with open(input_pdf_path, "wb") as f:
            f.write(base64.b64decode(pdf_base64))

        nombre_pdf_sin_extension = input_pdf_path.stem
        pdf = pdfium.PdfDocument(str(input_pdf_path))
        cantidad_paginas = len(pdf)
        imagenes = []

        # Extraer cada página como imagen
        for i in range(cantidad_paginas):
            nombre_imagen = tmp_path / f"{nombre_pdf_sin_extension}_{i+1}.jpg"
            pagina = pdf.get_page(i)
            imagen_pil = pagina.render(scale=escala).to_pil()
            imagen_pil.save(nombre_imagen)
            imagenes.append(nombre_imagen)

        # Comprimir las imágenes
        imagenes_comprimidas = []
        for img_path in imagenes:
            salida = img_path.with_stem(img_path.stem + "_comprimida")
            imagen = Image.open(img_path)
            imagen.save(salida, optimize=True, quality=calidad)
            imagenes_comprimidas.append(salida)

        # Crear PDF comprimido desde imágenes comprimidas
        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in imagenes_comprimidas]))

        # Leer el PDF final y convertir a base64
        with open(output_pdf_path, "rb") as f:
            pdf_final_base64 = base64.b64encode(f.read()).decode("utf-8")

        return pdf_final_base64
