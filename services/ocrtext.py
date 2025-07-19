import base64
import subprocess
import tempfile
import os

def ocr_pdf_and_return_base64(pdf_path: str) -> str:
    """
    Aplica OCR a un PDF usando el servicio externo y retorna el resultado en base64.
    
    Args:
        pdf_path (str): Ruta al archivo PDF a procesar
        
    Returns:
        str: PDF procesado codificado en base64
        
    Raises:
        Exception: Si el proceso de OCR falla
    """
    output_file = None
    
    try:
        # Crear archivo temporal para la respuesta
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_output:
            output_file = temp_output.name
        
        # Construir comando curl con timeout
        curl_command = [
            'curl',
            '-X', 'POST',
            '--connect-timeout', '10',  # Timeout de conexión: 10 segundos
            '--max-time', '300',        # Timeout total: 5 minutos
            'http://192.168.2.33:30124/api/v1/misc/ocr-pdf',
            '-F', 'removeImagesAfter=false',
            '-F', 'clean=true',
            '-F', 'deskew=true',
            '-F', 'cleanFinal=true',
            '-F', 'ocrRenderType=hocr',
            '-F', f'fileInput=@{pdf_path};type=application/pdf',
            '-F', 'ocrType=Normal',
            '-F', 'languages=eng',
            '-F', 'sidecar=false',
            '-o', output_file
        ]
        
        # Ejecutar curl
        result = subprocess.run(
            curl_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        # Verificar que el archivo de salida existe y tiene contenido
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            raise Exception("OCR service returned empty response")
        
        # Verificar si la respuesta es un PDF válido o un mensaje de error
        with open(output_file, 'rb') as f:
            file_content = f.read()
            
            # Verificar si es un PDF válido
            if len(file_content) >= 4 and file_content.startswith(b'%PDF'):
                # Es un PDF válido, verificar que también termine correctamente
                if b'%%EOF' in file_content:
                    # PDF válido y completo, codificar en base64
                    base64_result = base64.b64encode(file_content).decode('utf-8')
                    return base64_result
                else:
                    # PDF incompleto o corrupto
                    raise Exception("OCR service returned incomplete PDF")
            else:
                # No es un PDF válido, probablemente es un mensaje de error
                try:
                    # Intentar decodificar como texto para obtener el mensaje de error
                    error_message = file_content.decode('utf-8').strip()
                    # Si es un mensaje de error común, manejarlo específicamente
                    if "already has OCR" in error_message.lower():
                        raise Exception("PDF already contains OCR text")
                    elif "unsupported" in error_message.lower():
                        raise Exception("Unsupported PDF format")
                    else:
                        raise Exception(f"OCR service error: {error_message}")
                except UnicodeDecodeError:
                    # Si no se puede decodificar como texto, verificar si es HTML (respuesta de error web)
                    if b'<html' in file_content[:100].lower() or b'<!doctype' in file_content[:100].lower():
                        raise Exception("OCR service returned HTML error page (service may be down)")
                    else:
                        raise Exception("OCR service returned invalid response (not a PDF or readable error)")
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else "Unknown curl error"
        raise Exception(f"OCR service request failed: {error_msg}")
    except Exception as e:
        raise Exception(f"OCR processing error: {str(e)}")
    finally:
        # Limpiar archivo temporal de salida
        if output_file and os.path.exists(output_file):
            os.unlink(output_file)
        
        # Verificar que el archivo de salida existe y tiene contenido
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            raise Exception("OCR service returned empty response")
        
        # Leer el archivo procesado y codificarlo en base64
        with open(output_file, 'rb') as f:
            pdf_data = f.read()
            base64_result = base64.b64encode(pdf_data).decode('utf-8')
        
        return base64_result
    
def compress_pdf_base64(pdf_base64: str) -> str:
    """
    Comprime un PDF recibido en base64 usando el servicio externo y elige el mejor resultado según calidad visual y tamaño.
    """
    import tempfile
    import subprocess
    import os
    import base64
    from PIL import Image

    def extract_first_page_image(pdf_bytes):
        try:
            import fitz  # PyMuPDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                temp_pdf.write(pdf_bytes)
                temp_pdf_path = temp_pdf.name
            doc = fitz.open(temp_pdf_path)
            page = doc.load_page(0)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            os.unlink(temp_pdf_path)
            return img
        except Exception:
            return None

    def ssim_score(img1, img2):
        try:
            from skimage.metrics import structural_similarity as ssim
            import numpy as np
            img1 = img1.convert('L').resize((400, 400))
            img2 = img2.convert('L').resize((400, 400))
            arr1 = np.array(img1)
            arr2 = np.array(img2)
            return ssim(arr1, arr2, data_range=255)
        except Exception:
            return 0.5

    pdf_bytes = base64.b64decode(pdf_base64)
    original_size = len(pdf_bytes)
    ref_img = extract_first_page_image(pdf_bytes)

    # --- Compresión externa (curl) ---
    curl_configs = [
        {'optimize_level': 1, 'target_ratio': 0.8},        
        {'optimize_level': 3, 'target_ratio': 0.5},
        {'optimize_level': 5, 'target_ratio': 0.5},    
        {'optimize_level': 9, 'target_ratio': 0.5}, 
    ]
    candidates = []
    for cfg in curl_configs:
        try:
            target_size = int(original_size * cfg['target_ratio'])
            if target_size >= 1024*1024:
                expected_output_size = f"{round(target_size/1024/1024)}MB"
            else:
                expected_output_size = f"{round(target_size/1024)}KB"
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
                temp_input.write(pdf_bytes)
                input_file = temp_input.name
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_output:
                output_file = temp_output.name
            curl_command = [
                'curl',
                '-X', 'POST',
                '--connect-timeout', '10',
                '--max-time', '300',
                'http://192.168.2.33:30124/api/v1/misc/compress-pdf',
                '-F', f'fileInput=@{input_file};type=application/pdf',
                '-F', f'optimizeLevel={cfg["optimize_level"]}',
                '-F', f'expectedOutputSize={expected_output_size}',
                '-F', 'linearize=false',
                '-F', 'normalize=false',
                '-F', 'grayscale=false',
                '-o', output_file
            ]
            subprocess.run(curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                continue
            with open(output_file, 'rb') as f:
                file_content = f.read()
            if len(file_content) < 4 or not file_content.startswith(b'%PDF') or b'%%EOF' not in file_content:
                continue
            comp_b64 = base64.b64encode(file_content).decode('utf-8')
            comp_img = extract_first_page_image(file_content) if ref_img else None
            if ref_img and comp_img:
                quality = ssim_score(ref_img, comp_img)
            else:
                quality = 1.0
            size_ratio = len(file_content) / original_size
            score = (quality * 0.7) + ((1-size_ratio) * 0.3)
            candidates.append({'b64': comp_b64, 'score': score})
            os.unlink(input_file)
            os.unlink(output_file)
        except Exception:
            try:
                os.unlink(input_file)
            except:
                pass
            try:
                os.unlink(output_file)
            except:
                pass
            continue

    # --- Compresión local (PyPDFium2/JPEG) ---
    try:
        import pypdfium2 as pdfium
        import img2pdf
        from pathlib import Path
        import numpy as np
        import cv2
        import shutil
        local_configs = [
            {'escala': 3, 'calidad': 90, 'peso_calidad': 0.8},
            {'escala': 2, 'calidad': 80, 'peso_calidad': 0.6},
            {'escala': 2, 'calidad': 70, 'peso_calidad': 0.4},
            {'escala': 1, 'calidad': 60, 'peso_calidad': 0.2},
        ]
        for config in local_configs:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                input_pdf_path = tmp_path / "original.pdf"
                output_pdf_path = tmp_path / "comprimido.pdf"
                with open(input_pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                pdf = pdfium.PdfDocument(str(input_pdf_path))
                cantidad_paginas = len(pdf)
                imagenes_comprimidas = []
                for i in range(cantidad_paginas):
                    pagina = pdf.get_page(i)
                    imagen_pil = pagina.render(scale=config['escala']).to_pil()
                    # Optimizar imagen
                    if config['calidad'] < 70:
                        imagen_pil = imagen_pil.filter(Image.SMOOTH)
                        from PIL import ImageEnhance
                        enhancer = ImageEnhance.Color(imagen_pil)
                        imagen_pil = enhancer.enhance(0.95)
                    else:
                        from PIL import ImageEnhance
                        enhancer = ImageEnhance.Contrast(imagen_pil)
                        imagen_pil = enhancer.enhance(1.02)
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
                    pdf_final_bytes = f.read()
                pdf.close()
                comp_b64 = base64.b64encode(pdf_final_bytes).decode("utf-8")
                comp_img = extract_first_page_image(pdf_final_bytes) if ref_img else None
                if ref_img and comp_img:
                    quality = ssim_score(ref_img, comp_img)
                else:
                    quality = 1.0
                size_ratio = len(pdf_final_bytes) / original_size
                score = (quality * config['peso_calidad']) + ((1-size_ratio) * (1-config['peso_calidad']))
                candidates.append({'b64': comp_b64, 'score': score})
    except Exception:
        pass

    # Agregar el original como candidato
    candidates.append({'b64': pdf_base64, 'score': 0.7})

    # Elegir el mejor
    best = max(candidates, key=lambda x: x['score'])
    return best['b64']
