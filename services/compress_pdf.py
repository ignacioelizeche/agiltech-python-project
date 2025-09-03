import base64
import pypdfium2 as pdfium
from pathlib import Path
from PIL import Image, ImageEnhance
import img2pdf
import tempfile
import numpy as np
from skimage.metrics import structural_similarity as ssim
import cv2

def compress_pdf_base64(pdf_base64: str) -> str:
    """
    Comprime el PDF y devuelve automáticamente la mejor opción
    basada en un balance entre calidad (SSIM) y tamaño.
    """

    try:
        tamaño_original = len(base64.b64decode(pdf_base64))
        imagen_original = _extraer_imagen_referencia(pdf_base64)

        # Detectar si el documento requiere más calidad
        documento_critico = _detectar_documento_critico(pdf_base64)

        # Configuraciones ampliadas para exploración
        configs = (
            [{'escala': 3, 'calidad': q} for q in [95, 90, 85, 80]] +
            [{'escala': 2, 'calidad': q} for q in [85, 80, 75, 70, 65]] +
            [{'escala': 1, 'calidad': q} for q in [70, 65, 60, 55]]
        )

        mejor_pdf = pdf_base64
        mejor_score = -1  # siempre será reemplazado

        for config in configs:
            try:
                pdf_comprimido = _comprimir_con_config(pdf_base64, config)

                # Ajuste dinámico del peso de calidad
                peso_calidad = 0.8 if documento_critico else 0.5

                score = _calcular_score_calidad_tamano(
                    imagen_original,
                    pdf_comprimido,
                    tamaño_original,
                    peso_calidad
                )

                if score > mejor_score:
                    mejor_score = score
                    mejor_pdf = pdf_comprimido

            except Exception:
                continue

        return mejor_pdf

    except Exception:
        return pdf_base64


def _calcular_score_calidad_tamano(imagen_original, pdf_comprimido_base64, tamaño_original, peso_calidad):
    """
    Calcula un score que combina calidad (SSIM) y reducción de tamaño.
    """
    try:
        tamaño_comprimido = len(base64.b64decode(pdf_comprimido_base64))
        reduccion = (tamaño_original - tamaño_comprimido) / tamaño_original
        reduccion = max(0.0, min(1.0, reduccion))  # normalizar entre 0 y 1

        if imagen_original is None:
            return reduccion * 100

        imagen_comprimida = _extraer_imagen_comprimida(pdf_comprimido_base64)
        if imagen_comprimida is None:
            return reduccion * 100

        # Calcular SSIM
        ssim_score = _calcular_ssim(imagen_original, imagen_comprimida)

        # Normalización para que calidad tenga más peso en documentos críticos
        score = (ssim_score * peso_calidad) + (reduccion * (1 - peso_calidad))

        return score * 100

    except Exception:
        return 0


def _extraer_imagen_comprimida(pdf_comprimido_base64):
    """Extrae imagen de la primera página del PDF comprimido"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            pdf_path = tmp_path / "temp.pdf"

            with open(pdf_path, "wb") as f:
                f.write(base64.b64decode(pdf_comprimido_base64))

            pdf = pdfium.PdfDocument(str(pdf_path))
            pagina = pdf.get_page(0)
            imagen = pagina.render(scale=2).to_pil()
            pdf.close()

            return imagen
    except Exception:
        return None


def _calcular_ssim(imagen1, imagen2):
    """Calcula SSIM entre dos imágenes"""
    try:
        if imagen1.size != imagen2.size:
            imagen2 = imagen2.resize(imagen1.size, Image.Resampling.LANCZOS)

        array1 = np.array(imagen1.convert('RGB'))
        array2 = np.array(imagen2.convert('RGB'))

        gray1 = cv2.cvtColor(array1, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(array2, cv2.COLOR_RGB2GRAY)

        return ssim(gray1, gray2, data_range=255)

    except Exception:
        return 0.5  # score neutro si falla


def _detectar_documento_critico(pdf_base64: str) -> bool:
    """Detecta si es un documento que requiere alta calidad"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_pdf_path = tmp_path / "temp.pdf"

            with open(input_pdf_path, "wb") as f:
                f.write(base64.b64decode(pdf_base64))

            pdf = pdfium.PdfDocument(str(input_pdf_path))
            pagina = pdf.get_page(0)
            imagen = pagina.render(scale=1).to_pil()
            pdf.close()

            if imagen.mode != 'RGB':
                imagen = imagen.convert('RGB')

            width, height = imagen.size
            colores_oficiales = 0
            texto_denso = 0
            total_muestras = 0

            for y in range(0, height, 15):
                for x in range(0, width, 15):
                    try:
                        r, g, b = imagen.getpixel((x, y))
                        total_muestras += 1

                        if (b > r + 30 and b > g + 10) or (g > r + 30 and g > b + 10):
                            colores_oficiales += 1

                        if x < width - 15 and y < height - 15:
                            r2, g2, b2 = imagen.getpixel((x + 15, y + 15))
                            if abs(r-r2) + abs(g-g2) + abs(b-b2) > 120:
                                texto_denso += 1
                    except:
                        continue

            if total_muestras == 0:
                return False

            prop_oficial = (colores_oficiales / total_muestras) * 100
            prop_texto = (texto_denso / total_muestras) * 100

            return prop_oficial > 8 or prop_texto > 12

    except Exception:
        return True  # asumimos crítico si falla


def _extraer_imagen_referencia(pdf_base64: str):
    """Extrae la primera página como imagen de referencia"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_pdf_path = tmp_path / "temp.pdf"

            with open(input_pdf_path, "wb") as f:
                f.write(base64.b64decode(pdf_base64))

            pdf = pdfium.PdfDocument(str(input_pdf_path))
            pagina = pdf.get_page(0)
            imagen = pagina.render(scale=2).to_pil()
            pdf.close()

            return imagen
    except Exception:
        return None


def _comprimir_con_config(pdf_base64: str, config: dict) -> str:
    """Comprime el PDF con una configuración específica"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_pdf_path = tmp_path / "original.pdf"
        output_pdf_path = tmp_path / "comprimido.pdf"

        with open(input_pdf_path, "wb") as f:
            f.write(base64.b64decode(pdf_base64))

        pdf = pdfium.PdfDocument(str(input_pdf_path))
        cantidad_paginas = len(pdf)
        imagenes_comprimidas = []

        for i in range(cantidad_paginas):
            pagina = pdf.get_page(i)
            imagen_pil = pagina.render(scale=config['escala']).to_pil()

            imagen_pil = _optimizar_imagen(imagen_pil, config['calidad'])
            nombre_imagen = tmp_path / f"pagina_{i+1}.jpg"

            save_kwargs = {
                'format': 'JPEG',
                'quality': config['calidad'],
                'optimize': True,
                'progressive': True
            }

            imagen_pil.save(nombre_imagen, **save_kwargs)
            imagenes_comprimidas.append(nombre_imagen)

        with open(output_pdf_path, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in imagenes_comprimidas]))

        with open(output_pdf_path, "rb") as f:
            pdf_final_base64 = base64.b64encode(f.read()).decode("utf-8")

        pdf.close()
        return pdf_final_base64


def _optimizar_imagen(imagen_pil, calidad):
    """Optimizaciones generales para cualquier imagen"""
    if calidad < 70:
        imagen_pil = imagen_pil.filter(Image.SMOOTH)
        enhancer = ImageEnhance.Color(imagen_pil)
        imagen_pil = enhancer.enhance(0.95)
    else:
        enhancer = ImageEnhance.Contrast(imagen_pil)
        imagen_pil = enhancer.enhance(1.02)

    return imagen_pil
