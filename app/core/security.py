import hmac
import hashlib
from app.core.config import SESSION_SECRET_KEY

def sign_session_id(user_id: int) -> str:
    user_id_str = str(user_id)
    signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
    return f"{user_id_str}.{signature}"

def verify_session_id(signed_value: str) -> int | None:
    if not signed_value:
        return None
    try:
        user_id_str, signature = signed_value.split(".", 1)
        expected_signature = hmac.new(SESSION_SECRET_KEY, user_id_str.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_signature):
            return int(user_id_str)
    except Exception:
        pass
    return None
