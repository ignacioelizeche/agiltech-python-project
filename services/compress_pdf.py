import requests
import base64
from pathlib import Path
from PIL import Image
import tempfile
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim

STIRLING_URL = "http://192.168.2.33:30124/api/v1/misc/compress-pdf"
API_KEY = "tu-api-key"  # si es necesario

def compress_pdf_base64(pdf_path, configs=None):
    """
    Prueba varias configuraciones de compresión en Stirling PDF
    y devuelve el PDF con mejor calidad/tamaño.
    Retorna: (pdf_base64, tamaño_kb)
    """
    if configs is None:
        # Definir niveles de compresión a probar
        configs = [
            {"level": 1},  # leve
            {"level": 3},  # media
            {"level": 5},  # fuerte
            {"level": 7},  # muy fuerte
        ]
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Extraer imagen de referencia de la primera página
    imagen_ref = extraer_imagen_pdf(pdf_bytes)

    mejor_pdf = pdf_bytes
    mejor_score = -1
    mejor_tamano = len(pdf_bytes)

    for cfg in configs:
        try:
            # Enviar a Stirling PDF
            files = {"file": ("archivo.pdf", pdf_bytes, "application/pdf")}
            headers = {"X-API-KEY": API_KEY}  # si aplica
            params = {"level": cfg["level"]}
            resp = requests.post(STIRLING_URL, files=files, headers=headers, params=params)
            resp.raise_for_status()

            pdf_comprimido = resp.content
            tamano = len(pdf_comprimido)

            # Extraer imagen primera página
            imagen_comprimida = extraer_imagen_pdf(pdf_comprimido)
            score = calcular_score_ssim(imagen_ref, imagen_comprimida, len(pdf_bytes), tamano)

            if score > mejor_score:
                mejor_score = score
                mejor_pdf = pdf_comprimido
                mejor_tamano = tamano

        except Exception as e:
            print(f"Error con nivel {cfg['level']}: {e}")
            continue

    # Retornar como base64 y tamaño en KB
    return base64.b64encode(mejor_pdf).decode("utf-8"), round(mejor_tamano / 1024, 2)


# ---------------- FUNCIONES AUXILIARES ---------------- #

def extraer_imagen_pdf(pdf_bytes):
    """Extrae la primera página del PDF como imagen PIL"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "temp.pdf"
            with open(tmp_path, "wb") as f:
                f.write(pdf_bytes)
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(str(tmp_path))
            pagina = pdf.get_page(0)
            imagen = pagina.render(scale=2).to_pil()
            pdf.close()
            return imagen
    except Exception:
        return None

def calcular_score_ssim(img1, img2, size_original, size_comprimido):
    """Score combinado: SSIM y reducción de tamaño"""
    if img1 is None or img2 is None:
        return 0
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)
    arr1 = np.array(img1.convert("RGB"))
    arr2 = np.array(img2.convert("RGB"))
    gray1 = cv2.cvtColor(arr1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(arr2, cv2.COLOR_RGB2GRAY)
    ssim_score = ssim(gray1, gray2, data_range=255)

    reduccion = (size_original - size_comprimido) / size_original
    # combinar: 70% SSIM, 30% reducción tamaño
    score = ssim_score * 0.7 + reduccion * 0.3
    return score
