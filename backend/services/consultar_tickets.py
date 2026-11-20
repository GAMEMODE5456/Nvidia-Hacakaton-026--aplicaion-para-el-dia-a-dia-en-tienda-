
from database.conexion import conectar


# =====================================
# CONVERSIÓN SEGURA DE VALORES
# =====================================

def convertir_float(valor):

    if valor is None:
        return None

    return float(valor)


# =====================================
# CONVERTIR FECHA
# =====================================

def convertir_fecha(fecha):

    if fecha is None:
        return None

    return fecha.isoformat()


# =====================================
# CONSULTAR TICKETS
# =====================================

def consultar_tickets(id_ticket=None):

    conexion = conectar()

    if conexion is None:
        raise ConnectionError(
            "No se pudo conectar con MariaDB"
        )

    try:

        with conexion.cursor() as cursor:

            # =====================================
            # 1. CONSULTAR TICKETS Y PRODUCTOS
            # =====================================

            sql = """
                SELECT

                    -- DATOS DEL TICKET
                    t.id_ticket,
                    t.id_usuario,
                    t.folio,
                    t.fecha_compra,
                    t.total,
                    t.ruta_imagen,

                    -- PROVEEDOR
                    pr.nombre AS proveedor,

                    -- PRODUCTO
                    p.id_producto,
                    p.nombre AS nombre_producto,
                    p.presentacion,
                    p.codigo_barras,
                    p.unidad,
                    p.precio_venta,
                    p.stock_minimo,

                    -- CATEGORIA
                    c.nombre AS categoria,

                    -- DETALLE DEL TICKET
                    dt.cantidad,
                    dt.precio_unitario,
                    dt.subtotal AS subtotal_producto

                FROM tickets t

                INNER JOIN proveedores pr
                    ON t.id_proveedor = pr.id_proveedor

                LEFT JOIN detalle_ticket dt
                    ON t.id_ticket = dt.id_ticket

                LEFT JOIN productos p
                    ON dt.id_producto = p.id_producto

                LEFT JOIN categorias c
                    ON p.id_categoria = c.id_categoria
            """

            parametros = ()

            # =====================================
            # 2. FILTRAR POR ID SI ES NECESARIO
            # =====================================

            if id_ticket is not None:

                sql += """
                    WHERE t.id_ticket = %s
                """

                parametros = (id_ticket,)

            sql += """
                ORDER BY
                    t.id_ticket DESC,
                    dt.id_detalle ASC
            """

            cursor.execute(sql, parametros)

            registros = cursor.fetchall()

        # =====================================
        # 3. AGRUPAR TICKETS
        # =====================================

        tickets = {}

        for fila in registros:

            id_actual = fila["id_ticket"]

            # ---------------------------------
            # CREAR ENCABEZADO DEL TICKET
            # ---------------------------------

            if id_actual not in tickets:

                tickets[id_actual] = {

                    "id_ticket": id_actual,

                    "id_usuario": fila["id_usuario"],

                    "ticket": {

                        "proveedor": fila["proveedor"],

                        "folio": fila["folio"],

                        "fecha_compra": convertir_fecha(
                            fila["fecha_compra"]
                        ),

                        "total": convertir_float(
                            fila["total"]
                        ),

                        "ruta_imagen": fila["ruta_imagen"],

                        "productos": []
                    }
                }

            # =====================================
            # 4. AGREGAR PRODUCTOS AL TICKET
            # =====================================

            if fila["id_producto"] is not None:

                producto = {

                    "nombre": fila["nombre_producto"],

                    "presentacion": fila["presentacion"],

                    "codigo_barras": fila["codigo_barras"],

                    "unidad": fila["unidad"],

                    "cantidad": convertir_float(
                        fila["cantidad"]
                    ),

                    "precio_unitario": convertir_float(
                        fila["precio_unitario"]
                    ),

                    "precio_venta": convertir_float(
                        fila["precio_venta"]
                    ),

                    "stock_minimo": convertir_float(
                        fila["stock_minimo"]
                    ),

                    "categoria": fila["categoria"]
                }

                tickets[id_actual]["ticket"]["productos"].append(
                    producto
                )

        # =====================================
        # 5. DEVOLVER RESULTADOS
        # =====================================

        return list(tickets.values())

    except Exception as error:

        print(
            "Error al consultar tickets:",
            error
        )

        raise

    finally:

        conexion.close()
