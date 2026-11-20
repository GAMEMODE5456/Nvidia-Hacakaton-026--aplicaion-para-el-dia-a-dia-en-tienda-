
from fastapi import APIRouter, HTTPException, status
from pymysql.err import IntegrityError

from database.conexion import conectar as obtener_conexion
from services.usuario import (
    UsuarioRegistro,
    UsuarioRespuesta,
    UsuarioConsulta
)
from security import generar_hash


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)


# ==========================================
# REGISTRAR USUARIO
# ==========================================

@router.post(
    "/registro",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED
)
def registrar_usuario(usuario: UsuarioRegistro):

    conexion = None

    try:
        conexion = obtener_conexion()

        with conexion.cursor() as cursor:

            # Verificar si el correo ya existe
            sql_verificar = """
                SELECT id_usuario
                FROM USUARIOS
                WHERE correo = %s
                LIMIT 1
            """

            cursor.execute(sql_verificar, (usuario.correo,))
            usuario_existente = cursor.fetchone()

            if usuario_existente:
                raise HTTPException(
                    status_code=409,
                    detail="El correo electrónico ya está registrado"
                )

            # Generar hash de la contraseña
            password_hash = generar_hash(usuario.password)

            # Insertar usuario
            sql_insertar = """
                INSERT INTO USUARIOS (
                    nombre,
                    apellido,
                    correo,
                    password_hash,
                    telefono,
                    activo,
                    fecha_registro
                )
                VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            """

            cursor.execute(
                sql_insertar,
                (
                    usuario.nombre.strip(),
                    usuario.apellido.strip(),
                    str(usuario.correo).lower(),
                    password_hash,
                    usuario.telefono
                )
            )

            id_usuario = cursor.lastrowid

        conexion.commit()

        return UsuarioRespuesta(
            mensaje="Cuenta creada correctamente",
            id_usuario=id_usuario,
            nombre=usuario.nombre.strip(),
            apellido=usuario.apellido.strip(),
            correo=str(usuario.correo).lower(),
            telefono=usuario.telefono,
            activo=True
        )

    except HTTPException:
        if conexion:
            conexion.rollback()
        raise

    except IntegrityError:
        if conexion:
            conexion.rollback()

        raise HTTPException(
            status_code=409,
            detail="El correo electrónico ya está registrado"
        )

    except Exception:
        if conexion:
            conexion.rollback()

        raise HTTPException(
            status_code=500,
            detail="Error interno al registrar el usuario"
        )

    finally:
        if conexion:
            conexion.close()


# ==========================================
# CONSULTAR TODOS LOS USUARIOS
# ==========================================

@router.get("/", response_model=list[UsuarioConsulta])
def consultar_usuarios():

    conexion = None

    try:
        conexion = obtener_conexion()

        with conexion.cursor() as cursor:

            sql = """
                SELECT
                    id_usuario,
                    nombre,
                    apellido,
                    correo,
                    telefono,
                    activo
                FROM USUARIOS
                ORDER BY id_usuario DESC
            """

            cursor.execute(sql)
            usuarios = cursor.fetchall()

        return usuarios

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error al consultar los usuarios"
        )

    finally:
        if conexion:
            conexion.close()


# ==========================================
# CONSULTAR UN USUARIO POR ID
# ==========================================

@router.get("/{id_usuario}", response_model=UsuarioConsulta)
def consultar_usuario(id_usuario: int):

    conexion = None

    try:
        conexion = obtener_conexion()

        with conexion.cursor() as cursor:

            sql = """
                SELECT
                    id_usuario,
                    nombre,
                    apellido,
                    correo,
                    telefono,
                    activo
                FROM USUARIOS
                WHERE id_usuario = %s
                LIMIT 1
            """

            cursor.execute(sql, (id_usuario,))
            usuario = cursor.fetchone()

        if not usuario:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado"
            )

        return usuario

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error al consultar el usuario"
        )

    finally:
        if conexion:
            conexion.close()
