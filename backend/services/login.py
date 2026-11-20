
from database.conexion import conectar as obtener_conexion
from security import verificar_password, crear_access_token


def autenticar_usuario(correo: str, password: str):

    conexion = obtener_conexion()

    if conexion is None:
        raise Exception("No se pudo conectar con MariaDB")

    cursor = None

    try:
        cursor = conexion.cursor()

        consulta = """
            SELECT
                id_usuario,
                nombre,
                apellido,
                correo,
                password_hash,
                telefono,
                activo
            FROM usuarios
            WHERE correo = %s
            LIMIT 1
        """

        cursor.execute(consulta, (correo,))
        resultado = cursor.fetchone()

        if not resultado:
            return None

        # Convertir resultado a diccionario
        if isinstance(resultado, dict):
            usuario = resultado
        else:
            columnas = [
                columna[0] for columna in cursor.description
            ]
            usuario = dict(zip(columnas, resultado))

        # Verificar cuenta activa
        if not usuario["activo"]:
            return None

        # Verificar contraseña Argon2
        if not verificar_password(
            password,
            usuario["password_hash"]
        ):
            return None

        # Generar JWT
        token = crear_access_token({
            "sub": str(usuario["id_usuario"])
        })

        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": {
                "id_usuario": usuario["id_usuario"],
                "nombre": usuario["nombre"],
                "apellido": usuario["apellido"],
                "correo": usuario["correo"],
                "telefono": usuario["telefono"]
            }
        }

    finally:
        if cursor:
            cursor.close()

        conexion.close()
