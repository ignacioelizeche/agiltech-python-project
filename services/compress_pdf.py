import base64
import pypdfium2 as pdfium
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import img2pdf
import tempfile
import numpy as np
from skimage.metrics import structural_similarity as ssim
import cv2

def compress_pdf_base64(pdf_base64: str, max_ratio: float = 0.35):
    """
    Simula la compresión adaptativa estilo ILovePDF.
    Intenta acercarse al max_ratio sin sacrificar calidad.
    """
    tamaño_original = len(base64.b64decode(pdf_base64))
    imagen_original = _extraer_imagen_referencia(pdf_base64)
    documento_critico = _detectar_documento_critico(pdf_base64)

    # Configuración inicial
    escala = 3
    calidad = 95
    min_ssim = 0.95 if documento_critico else 0.92

    mejor_pdf = pdf_base64
    mejor_tamaño = tamaño_original
    mejor_score = -1

    while True:
        pdf_comprimido = _comprimir_con_config(pdf_base64, {'escala': escala, 'calidad': calidad})
        tamaño_comprimido = len(base64.b64decode(pdf_comprimido))
        ratio = tamaño_comprimido / tamaño_original

        score = _calcular_score_calidad_tamano(imagen_original, pdf_comprimido, tamaño_original, 0.5)
        ssim_score = score / 100

        # Guardar si cumple SSIM y mejora score
        if ssim_score >= min_ssim and score > mejor_score:
            mejor_pdf = pdf_comprimido
            mejor_score = score
            mejor_tamaño = tamaño_comprimido

        # Detener si llegamos al ratio máximo o la calidad cae demasiado
        if ratio <= max_ratio or ssim_score < min_ssim:
            break

        # Reducir gradualmente calidad y/o escala
        if calidad > 70:
            calidad -= 5
        elif escala > 1:
            escala -= 1
            calidad = 85
        else:
            break

    return mejor_pdf, round(mejor_tamaño / 1024, 2)


# ---------------- FUNCIONES AUXILIARES ---------------- #

def _calcular_score_calidad_tamano(imagen_original, pdf_comprimido_base64, tamaño_original, peso_calidad):
    try:
        tamaño_comprimido = len(base64.b64decode(pdf_comprimido_base64))
        reduccion = (tamaño_original - tamaño_comprimido) / tamaño_original
        reduccion = max(0.0, min(1.0, reduccion))

        if imagen_original is None:
            return reduccion * 100

        imagen_comprimida = _extraer_imagen_comprimida(pdf_comprimido_base64)
        if imagen_comprimida is None:
            return reduccion * 100

        ssim_score = _calcular_ssim(imagen_original, imagen_comprimida)

        score = (ssim_score * peso_calidad) + (reduccion * (1 - peso_calidad))
        return score * 100

    except Exception:
        return 0


def _extraer_imagen_comprimida(pdf_comprimido_base64):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "temp.pdf"
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
    try:
        if imagen1.size != imagen2.size:
            imagen2 = imagen2.resize(imagen1.size, Image.Resampling.LANCZOS)
        array1 = np.array(imagen1.convert('RGB'))
        array2 = np.array(imagen2.convert('RGB'))
        gray1 = cv2.cvtColor(array1, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(array2, cv2.COLOR_RGB2GRAY)
        return ssim(gray1, gray2, data_range=255)
    except Exception:
        return 0.5


def _detectar_documento_critico(pdf_base64: str) -> bool:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "temp.pdf"
            with open(pdf_path, "wb") as f:
                f.write(base64.b64decode(pdf_base64))
            pdf = pdfium.PdfDocument(str(pdf_path))
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
        return True


def _extraer_imagen_referencia(pdf_base64: str):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "temp.pdf"
            with open(pdf_path, "wb") as f:
                f.write(base64.b64decode(pdf_base64))
            pdf = pdfium.PdfDocument(str(pdf_path))
            pagina = pdf.get_page(0)
            imagen = pagina.render(scale=2).to_pil()
            pdf.close()
            return imagen
    except Exception:
        return None


def _comprimir_con_config(pdf_base64: str, config: dict) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_pdf = tmp_path / "original.pdf"
        output_pdf = tmp_path / "comprimido.pdf"
        with open(input_pdf, "wb") as f:
            f.write(base64.b64decode(pdf_base64))
        pdf = pdfium.PdfDocument(str(input_pdf))
        cantidad_paginas = len(pdf)
        imagenes_comprimidas = []

        for i in range(cantidad_paginas):
            pagina = pdf.get_page(i)
            imagen = pagina.render(scale=config['escala']).to_pil()
            imagen = _optimizar_imagen(imagen, config['calidad'])
            nombre_imagen = tmp_path / f"pagina_{i+1}.jpg"
            imagen.save(nombre_imagen, format='JPEG', quality=config['calidad'], optimize=True, progressive=True)
            imagenes_comprimidas.append(nombre_imagen)

        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in imagenes_comprimidas]))
        pdf.close()

        with open(output_pdf, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


def _optimizar_imagen(imagen, calidad):
    if calidad < 70:
        imagen = imagen.filter(ImageFilter.SMOOTH)
        enhancer = ImageEnhance.Color(imagen)
        imagen = enhancer.enhance(0.95)
    else:
        enhancer = ImageEnhance.Contrast(imagen)
        imagen = enhancer.enhance(1.02)
    return imagen
