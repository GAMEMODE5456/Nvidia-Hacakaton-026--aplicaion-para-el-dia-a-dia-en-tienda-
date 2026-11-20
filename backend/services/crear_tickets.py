from database.conexion import conectar

from decimal import Decimal
import pymysql  

def crear_ticket(datos, id_usuario):

    conexion = conectar()
    if conexion is None:
        raise ConnectionError("No se pudo conectar con MariaDB")

    try:

        with conexion.cursor() as cursor:

            # =====================================
            # 1. VALIDAR USUARIO
            # =====================================

            cursor.execute("""
                SELECT id_usuario
                FROM usuarios
                WHERE id_usuario = %s
                AND activo = TRUE
            """, (id_usuario,))

            usuario = cursor.fetchone()

            if not usuario:
                raise ValueError("El usuario no existe o está inactivo")

            # =====================================
            # 2. OBTENER O CREAR PROVEEDOR
            # =====================================

            nombre_proveedor = datos["proveedor"].strip()

            if not nombre_proveedor:
                raise ValueError("El proveedor es obligatorio") #aqui si el tickets no tiene proveedor, se ejecta. es opcional
            cursor.execute("""
                INSERT INTO proveedores (nombre)
                VALUES (%s)

                ON DUPLICATE KEY UPDATE
                id_proveedor = LAST_INSERT_ID(id_proveedor)
            """, (nombre_proveedor,))

            id_proveedor = cursor.lastrowid

            cursor.execute("""
                SELECT id_proveedor, activo
                FROM proveedores
                WHERE id_proveedor = %s
            """, (id_proveedor,))

            proveedor = cursor.fetchone()

            if not proveedor or not proveedor["activo"]:
                raise ValueError("El proveedor está inactivo")

            # =====================================
            # 3. VALIDAR PRODUCTOS
            # =====================================

            productos = datos["productos"]

            if not productos:
                raise ValueError("El ticket no contiene productos")

            total_calculado = Decimal("0.00")

            for producto in productos:

                cantidad = Decimal(str(producto["cantidad"]))
                precio = Decimal(str(producto["precio_unitario"]))

                if cantidad <= 0 or precio < 0:
                    raise ValueError("Cantidad o precio inválido")

                total_calculado += cantidad * precio

            total_ticket = Decimal(str(datos["total"]))

            if total_ticket < 0:
                raise ValueError("El total no puede ser negativo")

            # =====================================
            # 4. INSERTAR TICKET
            # =====================================

            cursor.execute("""
                INSERT INTO tickets (
                    id_usuario,
                    id_proveedor,
                    folio,
                    fecha_compra,
                    subtotal,
                    total,
                    ruta_imagen,
                    estado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDIENTE')
            """, (
                id_usuario,
                id_proveedor,
                datos.get("folio") or None,
                datos.get("fecha_compra") or None,
                total_calculado,
                total_ticket,
                datos.get("ruta_imagen")
            ))

            id_ticket = cursor.lastrowid

            # =====================================
            # 5. INSERTAR PRODUCTOS Y DETALLES
            # =====================================

            for producto in productos:

                nombre = producto["nombre"].strip()
                presentacion = producto["presentacion"].strip()

                if not nombre or not presentacion:
                    raise ValueError(
                        "El nombre y la presentación son obligatorios"
                    )

                categoria = producto.get("categoria") or "Sin categoría"

                # ---------------------------------
                # 5.1 Obtener o crear categoría
                # ---------------------------------

                cursor.execute("""
                    INSERT INTO categorias (nombre)
                    VALUES (%s)

                    ON DUPLICATE KEY UPDATE
                    id_categoria = LAST_INSERT_ID(id_categoria)
                """, (categoria,))

                id_categoria = cursor.lastrowid

                cursor.execute("""
                    SELECT id_categoria, activo
                    FROM categorias
                    WHERE id_categoria = %s
                """, (id_categoria,))

                categoria_db = cursor.fetchone()

                if not categoria_db or not categoria_db["activo"]:
                    raise ValueError("La categoría está inactiva")

                codigo_barras = producto.get("codigo_barras") or None

                # ---------------------------------
                # 5.2 Buscar producto existente
                # ---------------------------------

                if codigo_barras:

                    cursor.execute("""
                        SELECT id_producto, id_proveedor, activo
                        FROM productos
                        WHERE codigo_barras = %s
                        FOR UPDATE
                    """, (codigo_barras,))

                    producto_db = cursor.fetchone()

                    if producto_db:

                        if producto_db["id_proveedor"] != id_proveedor:
                            raise ValueError(
                                "El código de barras pertenece a otro proveedor"
                            )

                        if not producto_db["activo"]:
                            raise ValueError("El producto está inactivo")

                        id_producto = producto_db["id_producto"]

                    else:
                        id_producto = None

                else:
                    id_producto = None

                if id_producto is None:

                    cursor.execute("""
                        SELECT id_producto, activo
                        FROM productos
                        WHERE id_proveedor = %s
                        AND nombre = %s
                        AND presentacion = %s
                        FOR UPDATE
                    """, (
                        id_proveedor,
                        nombre,
                        presentacion
                    ))

                    producto_db = cursor.fetchone()

                    if producto_db:

                        if not producto_db["activo"]:
                            raise ValueError("El producto está inactivo")

                        id_producto = producto_db["id_producto"]

                # ---------------------------------
                # 5.3 Crear producto si no existe
                # ---------------------------------

                if id_producto is None:

                    cursor.execute("""
                        INSERT INTO productos (
                            id_proveedor,
                            id_categoria,
                            nombre,
                            presentacion,
                            codigo_barras,
                            unidad,
                            stock_actual,
                            stock_minimo,
                            precio_venta,
                            activo
                        )
                        VALUES (
                            %s, %s, %s, %s, %s,
                            %s, 0, %s, %s, TRUE
                        )
                    """, (
                        id_proveedor,
                        id_categoria,
                        nombre,
                        presentacion,
                        codigo_barras,
                        producto.get("unidad", "pieza"),
                        producto.get("stock_minimo", 5),
                        producto.get("precio_venta")
                    ))

                    id_producto = cursor.lastrowid

                # ---------------------------------
                # 5.4 Insertar detalle del ticket
                # ---------------------------------

                cantidad = Decimal(str(producto["cantidad"]))
                precio = Decimal(str(producto["precio_unitario"]))

                subtotal = cantidad * precio

                cursor.execute("""
                    INSERT INTO detalle_ticket (
                        id_ticket,
                        id_producto,
                        descripcion_original,
                        cantidad,
                        precio_unitario,
                        subtotal
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    id_ticket,
                    id_producto,
                    nombre,
                    cantidad,
                    precio,
                    subtotal
                ))

            # =====================================
            # 6. GUARDAR TRANSACCIÓN
            # =====================================

        conexion.commit()

        return {
            "id_ticket": id_ticket,
            "id_proveedor": id_proveedor,
            "proveedor": nombre_proveedor,
            "subtotal": float(total_calculado),
            "total": float(total_ticket),
            "estado": "PENDIENTE",
            "mensaje": "Ticket registrado correctamente"
        }

    except Exception as error:

        conexion.rollback()

        print("Error al registrar ticket:", error)

        raise

    finally:

        conexion.close()