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
    Comprime un PDF recibido en base64 usando el servicio externo y retorna el resultado en base64.
    Calcula automáticamente el tamaño de salida esperado entre 50% y 75% del tamaño original y usa un nivel de optimización alto.
    Args:
        pdf_base64 (str): PDF en base64
    Returns:
        str: PDF comprimido codificado en base64
    Raises:
        Exception: Si el proceso de compresión falla
    """
    import tempfile
    import subprocess
    import os
    import base64

    input_file = None
    output_file = None
    try:
        # Guardar el PDF base64 en un archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_input:
            input_file = temp_input.name
            pdf_bytes = base64.b64decode(pdf_base64)
            temp_input.write(pdf_bytes)
        optimize_level = 4  # compresión moderada para mejor calidad
        # Crear archivo temporal para la respuesta
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_output:
            output_file = temp_output.name
        # Construir comando curl (flags por defecto: linearize, normalize, grayscale en false)
        curl_command = [
            'curl',
            '-X', 'POST',
            '--connect-timeout', '10',
            '--max-time', '300',
            'http://192.168.2.33:30124/api/v1/misc/compress-pdf',
            '-F', f'fileInput=@{input_file};type=application/pdf',
            '-F', f'optimizeLevel={optimize_level}',
            '-F', 'linearize=false',
            '-F', 'normalize=false',
            '-F', 'grayscale=false',
            '-o', output_file
        ]
        result = subprocess.run(
            curl_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        # Verificar que el archivo de salida existe y tiene contenido
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            raise Exception("Compress service returned empty response")
        # Verificar si la respuesta es un PDF válido
        with open(output_file, 'rb') as f:
            file_content = f.read()
            if len(file_content) >= 4 and file_content.startswith(b'%PDF') and b'%%EOF' in file_content:
                return base64.b64encode(file_content).decode('utf-8')
            else:
                try:
                    error_message = file_content.decode('utf-8').strip()
                    raise Exception(f"Compress service error: {error_message}")
                except UnicodeDecodeError:
                    if b'<html' in file_content[:100].lower() or b'<!doctype' in file_content[:100].lower():
                        raise Exception("Compress service returned HTML error page (service may be down)")
                    else:
                        raise Exception("Compress service returned invalid response (not a PDF or readable error)")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else "Unknown curl error"
        raise Exception(f"Compress service request failed: {error_msg}")
    except Exception as e:
        raise Exception(f"Compress processing error: {str(e)}")
    finally:
        if input_file and os.path.exists(input_file):
            os.unlink(input_file)
        if output_file and os.path.exists(output_file):
            os.unlink(output_file)

