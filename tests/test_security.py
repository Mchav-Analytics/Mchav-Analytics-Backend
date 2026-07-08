from app.core.security import sign_session_id, verify_session_id

def test_sign_session_id_format():
    """Prueba que la firma generada tenga el formato correcto: ID.FirmaSHA256"""
    user_id = 5
    signed = sign_session_id(user_id)
    
    # Debe empezar con el ID y un punto
    assert signed.startswith("5.")
    
    # La firma (después del punto) debe ser un hash SHA-256 de 64 caracteres
    signature = signed.split(".")[1]
    assert len(signature) == 64

def test_verify_session_id_valid():
    """Prueba que una firma auténtica se decodifique y valide correctamente"""
    user_id = 5
    signed = sign_session_id(user_id)
    
    verified_id = verify_session_id(signed)
    assert verified_id == 5

def test_verify_session_id_tampered_hash():
    """Prueba que el sistema rechace el acceso si un hacker cambia un dígito de la firma"""
    user_id = 5
    signed = sign_session_id(user_id)
    
    # Simulamos que un hacker altera el último caracter de la firma
    ultimo_caracter = "0" if signed[-1] != "0" else "1"
    tampered_signed = signed[:-1] + ultimo_caracter
    
    verified_id = verify_session_id(tampered_signed)
    assert verified_id is None  # Debe rechazar el acceso

def test_verify_session_id_tampered_id():
    """Prueba que el sistema rechace si alguien intenta cambiar su ID de usuario pero deja la firma intacta"""
    user_id = 5
    signed = sign_session_id(user_id)
    
    # Simulamos que el usuario intenta hacerse pasar por el ID 6
    tampered_signed = "6" + signed[1:]
    
    verified_id = verify_session_id(tampered_signed)
    assert verified_id is None  # Debe rechazar el acceso

def test_verify_session_id_empty():
    """Prueba que el sistema rechace un token vacío o nulo sin generar un error interno (500)"""
    assert verify_session_id("") is None
    assert verify_session_id(None) is None

def test_verify_session_id_malformed_no_dot():
    """Prueba que el sistema no se caiga si envían basura sin el formato esperado (sin el punto separador)"""
    basura = "un_texto_aleatorio_sin_sentido_alguno"
    assert verify_session_id(basura) is None

def test_verify_session_id_malformed_invalid_id():
    """Prueba que el sistema no se caiga si el ID provisto no se puede convertir a número entero"""
    # Intentamos pasar 'abc' como ID del usuario
    signed_bad_id = "abc.a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
    assert verify_session_id(signed_bad_id) is None
