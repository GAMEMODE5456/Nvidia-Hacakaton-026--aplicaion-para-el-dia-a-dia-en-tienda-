
from database.conexion import conectar
from decimal import Decimal, InvalidOperation


def crear_ticket(datos, id_usuario):

    conexion = conectar()

    if conexion is None:
        raise ConnectionError(
            "No se pudo conectar con MariaDB"
        )

    try:
        conexion.begin()

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
                raise ValueError(
                    "El usuario no existe o está inactivo"
                )

            # =====================================
            # 2. VALIDAR PROVEEDOR
            # =====================================

            nombre_proveedor = (
                datos.get("proveedor") or ""
            ).strip()

            if not nombre_proveedor:
                raise ValueError(
                    "El proveedor es obligatorio"
                )

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
                raise ValueError(
                    "El proveedor está inactivo"
                )

            # =====================================
            # 3. VALIDAR PRODUCTOS
            # =====================================

            productos = datos.get("productos") or []

            if not productos:
                raise ValueError(
                    "El ticket no contiene productos"
                )

            total_calculado = Decimal("0.00")

            for producto in productos:

                try:
                    cantidad = Decimal(
                        str(producto["cantidad"])
                    )

                    precio = Decimal(
                        str(producto["precio_unitario"])
                    )

                except (KeyError, InvalidOperation):
                    raise ValueError(
                        "Producto con cantidad o precio inválido"
                    )

                if not cantidad.is_finite() or not precio.is_finite():
                    raise ValueError(
                        "Cantidad o precio no válido"
                    )

                if cantidad <= 0 or precio < 0:
                    raise ValueError(
                        "Cantidad o precio inválido"
                    )

                total_calculado += cantidad * precio

            total_calculado = total_calculado.quantize(
                Decimal("0.01")
            )

            # =====================================
            # 4. OBTENER TOTAL DEL TICKET
            # =====================================

            if datos.get("total") is None:
                total_ticket = total_calculado
            else:
                try:
                    total_ticket = Decimal(
                        str(datos["total"])
                    )
                except InvalidOperation:
                    raise ValueError(
                        "El total del ticket es inválido"
                    )

            if not total_ticket.is_finite() or total_ticket < 0:
                raise ValueError(
                    "El total no puede ser negativo o inválido"
                )

            # =====================================
            # 5. INSERTAR TICKET
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
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, 'PENDIENTE'
                )
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
            # 6. INSERTAR PRODUCTOS
            # =====================================

            productos_guardados = []

            for producto in productos:

                nombre = (
                    producto.get("nombre") or ""
                ).strip()

                presentacion = (
                    producto.get("presentacion")
                    or "Sin presentación"
                ).strip()

                if not nombre:
                    raise ValueError(
                        "El producto no tiene nombre"
                    )

                categoria = (
                    producto.get("categoria")
                    or "Sin categoría"
                )

                codigo_barras = (
                    producto.get("codigo_barras") or None
                )

                unidad = producto.get("unidad") or "pieza"

                # ---------------------------------
                # 6.1 BUSCAR O CREAR CATEGORÍA
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
                    raise ValueError(
                        "La categoría está inactiva"
                    )

                # ---------------------------------
                # 6.2 BUSCAR PRODUCTO POR CÓDIGO
                # ---------------------------------

                id_producto = None

                if codigo_barras:

                    cursor.execute("""
                        SELECT
                            id_producto,
                            id_proveedor,
                            activo
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
                            raise ValueError(
                                "El producto está inactivo"
                            )

                        id_producto = producto_db["id_producto"]

                # ---------------------------------
                # 6.3 BUSCAR POR NOMBRE Y PRESENTACIÓN
                # ---------------------------------

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
                            raise ValueError(
                                "El producto está inactivo"
                            )

                        id_producto = producto_db["id_producto"]

                # ---------------------------------
                # 6.4 CREAR PRODUCTO SI NO EXISTE
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
                        unidad,
                        producto.get("stock_minimo") or 5,
                        producto.get("precio_venta")
                    ))

                    id_producto = cursor.lastrowid

                # ---------------------------------
                # 6.5 INSERTAR DETALLE DEL TICKET
                # ---------------------------------

                cantidad = Decimal(
                    str(producto["cantidad"])
                )

                precio = Decimal(
                    str(producto["precio_unitario"])
                )

                subtotal = (cantidad * precio).quantize(
                    Decimal("0.01")
                )

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

                productos_guardados.append({
                    "id_producto": id_producto,
                    "nombre": nombre,
                    "cantidad": float(cantidad),
                    "precio_unitario": float(precio),
                    "subtotal": float(subtotal)
                })

        # =====================================
        # 7. CONFIRMAR TRANSACCIÓN
        # =====================================

        conexion.commit()

        return {
            "success": True,
            "id_ticket": id_ticket,
            "id_usuario": id_usuario,
            "id_proveedor": id_proveedor,
            "proveedor": nombre_proveedor,
            "folio": datos.get("folio"),
            "subtotal": float(total_calculado),
            "total": float(total_ticket),
            "estado": "PENDIENTE",
            "productos_guardados": productos_guardados,
            "mensaje": "Ticket registrado correctamente"
        }

    except Exception as error:

        conexion.rollback()

        print(
            "ERROR AL REGISTRAR TICKET:",
            str(error)
        )

        raise

    finally:
        conexion.close()
