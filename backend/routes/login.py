
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from services.login import autenticar_usuario

router = APIRouter(
    prefix="/login",
    tags=["Login"]
)


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str


@router.post("/")
def login(datos: LoginRequest):

    try:
        resultado = autenticar_usuario(
            str(datos.correo),
            datos.password
        )

        if resultado is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos"
            )

        return {
            "mensaje": "Inicio de sesión exitoso",
            **resultado
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"Error en login: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al iniciar sesión"
        )
