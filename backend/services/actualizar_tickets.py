
from database.conexion import conectar

from decimal import Decimal


def actualizar_ticket(id_ticket, datos):

    conexion = conectar()

    if conexion is None:
        raise ConnectionError(
            "No se pudo conectar con MariaDB"
        )

    try:

        with conexion.cursor() as cursor:

            # =====================================
            # 1. VERIFICAR QUE EXISTA EL TICKET
            # =====================================

            cursor.execute("""
                SELECT id_ticket
                FROM tickets
                WHERE id_ticket = %s
            """, (id_ticket,))

            ticket = cursor.fetchone()

            if not ticket:
                raise LookupError("El ticket no existe")

            # =====================================
            # 2. VALIDAR PROVEEDOR
            # =====================================

            nombre_proveedor = datos["proveedor"].strip()

            if not nombre_proveedor:
                raise ValueError(
                    "El proveedor es obligatorio"
                )

            cursor.execute("""
                SELECT id_proveedor, activo
                FROM proveedores
                WHERE nombre = %s
            """, (nombre_proveedor,))

            proveedor = cursor.fetchone()

            if not proveedor:
                raise ValueError(
                    "El proveedor no existe"
                )

            if not proveedor["activo"]:
                raise ValueError(
                    "El proveedor está inactivo"
                )

            id_proveedor = proveedor["id_proveedor"]

            # =====================================
            # 3. VALIDAR TOTAL
            # =====================================

            total = Decimal(str(datos["total"]))

            if total < 0:
                raise ValueError(
                    "El total no puede ser negativo"
                )

            # =====================================
            # 4. ACTUALIZAR TICKET
            # =====================================

            cursor.execute("""
                UPDATE tickets
                SET
                    id_proveedor = %s,
                    folio = %s,
                    fecha_compra = %s,
                    total = %s,
                    ruta_imagen = %s

                WHERE id_ticket = %s
            """, (
                id_proveedor,
                datos.get("folio") or None,
                datos.get("fecha_compra") or None,
                total,
                datos.get("ruta_imagen") or None,
                id_ticket
            ))

        # =====================================
        # 5. CONFIRMAR TRANSACCIÓN
        # =====================================

        conexion.commit()

        return {
            "id_ticket": id_ticket,
            "id_proveedor": id_proveedor,
            "proveedor": nombre_proveedor,
            "folio": datos.get("folio"),
            "total": float(total),
            "mensaje": "Ticket actualizado correctamente"
        }

    except Exception as error:

        conexion.rollback()

        print(
            "Error al actualizar ticket:",
            error
        )

        raise

    finally:

        conexion.close()
