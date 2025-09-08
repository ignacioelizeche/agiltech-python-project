import requests
import base64
from pathlib import Path
from PIL import Image
import tempfile
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
import logging

# --- Configuración (sin cambios) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
STIRLING_URL = "http://192.168.2.33:30124/api/v1/misc/compress-pdf"
API_KEY = "tu-api-key"

# --- Funciones Auxiliares (sin cambios) ---
def extract_image_from_pdf(pdf_bytes: bytes, page_number: int = 0, dpi: int = 150) -> Image.Image | None:
    # (Esta función no necesita cambios, ya que trabaja con bytes)
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_bytes)
        if page_number >= len(pdf):
            logging.warning(f"El PDF tiene menos de {page_number + 1} páginas. Usando la primera.")
            page_number = 0
        renderer = pdf.render(
            pdfium.PdfBitmap.to_pil,
            page_indices=[page_number],
            scale=dpi/72,
        )
        return next(renderer)
    except Exception as e:
        logging.error(f"Error al extraer la imagen del PDF: {e}")
        return None

def calculate_quality_score(
    original_image: Image.Image,
    compressed_image: Image.Image,
    original_size: int,
    compressed_size: int,
    quality_weight: float = 0.7,
    size_weight: float = 0.3
) -> float:
    # (Esta función no necesita cambios)
    if original_image is None or compressed_image is None: return -1.0
    if original_image.size != compressed_image.size:
        compressed_image = compressed_image.resize(original_image.size, Image.Resampling.LANCZOS)
    gray_orig = cv2.cvtColor(np.array(original_image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    gray_comp = cv2.cvtColor(np.array(compressed_image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    ssim_score = ssim(gray_orig, gray_comp, data_range=255)
    size_reduction_score = (original_size - compressed_size) / original_size if original_size > 0 else 0.0
    if size_reduction_score < 0: return -1.0
    return (ssim_score * quality_weight) + (size_reduction_score * size_weight)

# --- Función Principal Modificada ---
def find_best_pdf_compression(
    pdf_path: str | None = None,
    pdf_base64: str | None = None,
    stirling_url: str = STIRLING_URL,
    api_key: str = API_KEY,
    min_ssim_threshold: float = 0.98,  # Increased to ensure higher quality
    quality_weight: float = 0.8,       # Increased to prioritize quality
    size_weight: float = 0.2           # Decreased to de-prioritize size reduction
) -> tuple[str, float] | None:
    """
    Comprime un PDF (desde una ruta o Base64) y elige la mejor versión.

    Args:
        pdf_path: La ruta al archivo PDF (opcional).
        pdf_base64: El contenido del PDF como cadena Base64 (opcional).
                      Tendrá prioridad sobre pdf_path si ambos son provistos.
        stirling_url: URL del endpoint de la API de Stirling PDF.
        ... (resto de parámetros sin cambios)
    """
    original_pdf_bytes = None
    
    # --- LÓGICA DE ENTRADA MODIFICADA ---
    if pdf_base64:
        try:
            original_pdf_bytes = base64.b64decode(pdf_base64)
        except (base64.binascii.Error, ValueError) as e:
            logging.error(f"La cadena Base64 proporcionada no es válida: {e}")
            return None
    elif pdf_path:
        try:
            with open(pdf_path, "rb") as f:
                original_pdf_bytes = f.read()
        except FileNotFoundError:
            logging.error(f"El archivo no fue encontrado: {pdf_path}")
            return None
    else:
        logging.error("Debe proporcionar 'pdf_path' o 'pdf_base64'.")
        return None
    # --- FIN DE LA LÓGICA DE ENTRADA ---

    # El resto de la función sigue exactamente igual, ya que opera sobre 'original_pdf_bytes'
    original_size = len(original_pdf_bytes)
    original_image = extract_image_from_pdf(original_pdf_bytes)

    if not original_image:
        logging.error("No se pudo extraer una imagen del PDF original para la comparación.")
        return None

    best_pdf_bytes = original_pdf_bytes
    best_size = original_size
    best_score = calculate_quality_score(original_image, original_image, original_size, original_size, quality_weight, size_weight)
    logging.info(f"PDF Original: Tamaño={round(original_size / 1024, 2)} KB, Puntaje base={round(best_score, 4)}")

    compression_levels = [1, 3, 5, 7]
    for level in compression_levels:
        logging.info(f"--- Probando Nivel de Compresión: {level} ---")
        try:
            files = {"file": ("input.pdf", original_pdf_bytes, "application/pdf")}
            headers = {"X-API-KEY": api_key}
            params = {"level": level}
            response = requests.post(stirling_url, files=files, headers=headers, params=params, timeout=60)
            response.raise_for_status()

            compressed_pdf_bytes = response.content
            compressed_size = len(compressed_pdf_bytes)
            
            if compressed_size >= best_size:
                logging.warning(f"Nivel {level}: Descartado. El tamaño ({round(compressed_size/1024,2)} KB) no mejora.")
                continue

            compressed_image = extract_image_from_pdf(compressed_pdf_bytes)
            if not compressed_image: continue

            gray_orig = cv2.cvtColor(np.array(original_image.convert("RGB")), cv2.COLOR_RGB2GRAY)
            gray_comp = cv2.cvtColor(np.array(compressed_image.resize(original_image.size, Image.Resampling.LANCZOS)).convert("RGB"), cv2.COLOR_RGB2GRAY)
            ssim_value = ssim(gray_orig, gray_comp, data_range=255)
            logging.info(f"Nivel {level}: Tamaño={round(compressed_size / 1024, 2)} KB, SSIM={round(ssim_value, 4)}")

            if ssim_value < min_ssim_threshold:
                logging.warning(f"Nivel {level}: Descartado por baja calidad (SSIM < {min_ssim_threshold}).")
                continue

            current_score = calculate_quality_score(original_image, compressed_image, original_size, compressed_size, quality_weight, size_weight)
            logging.info(f"Nivel {level}: Puntaje final={round(current_score, 4)}")
            
            if current_score > best_score:
                logging.info(f"¡Nuevo mejor resultado encontrado en el Nivel {level}!")
                best_score = current_score
                best_pdf_bytes = compressed_pdf_bytes
                best_size = compressed_size
        except requests.exceptions.RequestException as e:
            logging.error(f"Error de red con nivel {level}: {e}")
        except Exception as e:
            logging.error(f"Error inesperado procesando el nivel {level}: {e}")

    final_base64 = base64.b64encode(best_pdf_bytes).decode("utf-8")
    final_size_kb = round(best_size / 1024, 2)
    logging.info(f"\n--- Decisión Final: Tamaño={final_size_kb} KB, Puntaje={round(best_score, 4)} ---")
    return final_base64, final_size_kb

# --- Ejemplo de Uso con Base64 ---
if __name__ == "__main__":
    
    # Simula que tienes un PDF y lo conviertes a Base64 primero.
    # En tu aplicación, ya tendrías esta cadena Base64.
    pdf_file_path = "documento_de_prueba.pdf"
    
    try:
        with open(pdf_file_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Este es el input que usarías en tu caso
        mi_pdf_en_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        
        print("\n--- Ejecutando compresión desde una cadena Base64 ---")
        
        # Llama a la función usando el nuevo parámetro 'pdf_base64'
        result = find_best_pdf_compression(pdf_base64=mi_pdf_en_base64)

        if result:
            pdf_b64_comprimido, size_kb = result
            print(f"Compresión desde Base64 exitosa. Tamaño final: {size_kb} KB.")

    except FileNotFoundError:
        print(f"Error: El archivo de prueba '{pdf_file_path}' no se encontró.")
        print("Por favor, crea un archivo con ese nombre o cambia la ruta para ejecutar el ejemplo.")
