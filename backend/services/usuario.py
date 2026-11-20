
from pydantic import BaseModel, EmailStr, Field


# Datos que recibimos al registrar un usuario
class UsuarioRegistro(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    apellido: str = Field(min_length=2, max_length=120)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=20)


# Datos que devolvemos al registrar un usuario
class UsuarioRespuesta(BaseModel):
    mensaje: str
    id_usuario: int
    nombre: str
    apellido: str
    correo: EmailStr
    telefono: str | None
    activo: bool


# Datos para consultar un usuario
class UsuarioConsulta(BaseModel):
    id_usuario: int
    nombre: str
    apellido: str
    correo: EmailStr
    telefono: str | None
    activo: bool
