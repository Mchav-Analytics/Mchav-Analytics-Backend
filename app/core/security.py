# app/core/security.py
# Módulo de seguridad criptográfica y gestión de sesiones mediante firmas HMAC SHA-256

import hmac
import hashlib
from app.core.config import SESSION_SECRET_KEY

def sign_session_id(user_id: int) -> str:
    """
    Firma un ID de usuario utilizando HMAC con la llave secreta del sistema (SESSION_SECRET_KEY).
    Produce un valor legible de la forma 'user_id.signature_hex' para almacenar en cookies HTTP-Only.
    """
    user_id_str = str(user_id)  # Convertir el ID de usuario a texto
    # Generar firma HMAC con algoritmo SHA-256
    signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
    return f"{user_id_str}.{signature}"  # Concatenar ID con la firma resultante

def verify_session_id(signed_value: str) -> int | None:
    """
    Verifica la autenticidad e integridad de la cookie de sesión firmada.
    Utiliza comparación en tiempo constante (hmac.compare_digest) para evitar ataques de tiempo (Timing Attacks).
    Retorna el user_id como entero si la firma es válida, o None si ha sido alterada o es inválida.
    """
    if not signed_value:
        return None  # Retornar None si no hay valor de sesión
    try:
        # Separar el ID de usuario de la firma criptográfica por el punto delimitador
        user_id_str, signature = signed_value.split(".", 1)
        # Recalcular la firma esperada usando la llave secreta
        expected_signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
        # Comparación segura de la firma recibida contra la calculada
        if hmac.compare_digest(signature, expected_signature):
            return int(user_id_str)  # Retornar el ID del usuario verificado
    except Exception:
        pass  # Capturar cualquier error de parseo o formato incorrecto
    return None  # Retornar None si la validación falla
