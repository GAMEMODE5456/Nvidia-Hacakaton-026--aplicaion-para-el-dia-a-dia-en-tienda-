
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from datetime import datetime, timedelta, timezone
from jose import jwt
import os

# =====================================
# CONFIGURACIÓN DE CONTRASEÑAS
# =====================================

password_hasher = PasswordHash.recommended()


def generar_hash(password: str) -> str:
    """Genera un hash seguro utilizando Argon2."""
    return password_hasher.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """Verifica la contraseña contra el hash almacenado."""

    try:
        return password_hasher.verify(password, password_hash)

    except UnknownHashError:
        return False


# =====================================
# CONFIGURACIÓN JWT
# =====================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "CLAVE_TEMPORAL-SOLO-PARA-DESARROLLO-CAMBIAR"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


def crear_access_token(data: dict) -> str:

    datos = data.copy()

    expiracion = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    datos.update({"exp": expiracion})

    return jwt.encode(
        datos,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
