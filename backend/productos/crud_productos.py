import pymysql
from database.conexion import conectar


def obtener_productos():

    conexion = conectar()

    if conexion is None:
        raise ConnectionError("No se pudo conectar con MariaDB")

    try:

        with conexion.cursor() as cursor:

            sql = """
                SELECT
                    p.id_producto,
                    p.nombre,
                    p.presentacion,
                    p.codigo_barras,
                    p.unidad,
                    p.stock_actual,
                    p.stock_minimo,
                    p.precio_venta,

                    pr.id_proveedor,
                    pr.nombre AS proveedor,

                    c.id_categoria,
                    c.nombre AS categoria

                FROM productos p

                INNER JOIN proveedores pr
                    ON p.id_proveedor = pr.id_proveedor

                INNER JOIN categorias c
                    ON p.id_categoria = c.id_categoria

                WHERE p.activo = TRUE

                ORDER BY p.nombre ASC
            """

            cursor.execute(sql)

            productos = cursor.fetchall()

            return productos

    except pymysql.MySQLError as error:

        print("Error al consultar productos:", error)
        raise

    finally:

        conexion.close()