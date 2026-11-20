import flet as ft

from services.crear_tickets import crear_ticket


# Usuario que inició sesión (simulación)
ID_USUARIO = 1


# ==========================================
# DATOS SIMULADOS EXTRAÍDOS POR LA IA
# ==========================================

datos_ocr = {
    "proveedor": "Coca-Cola",
    "folio": "CC-2026-001",
    "fecha_compra": "2026-11-19 15:30:00",
    "total": 100.00,
    "ruta_imagen": None,

    "productos": [
        {
            "nombre": "Coca-Cola",
            "presentacion": "600 ml",
            "cantidad": 4,
            "precio_unitario": 15.00,
            "codigo_barras": None,
            "categoria": "Refrescos"
        },
        {
            "nombre": "Coca-Cola",
            "presentacion": "2 litros",
            "cantidad": 2,
            "precio_unitario": 20.00,
            "codigo_barras": None,
            "categoria": "Refrescos"
        }
    ]
}


def main(page: ft.Page):

    page.title = "Miscelánea - Registro de mercancía"
    page.window.width = 1100
    page.window.height = 850
    page.padding = 25
    page.scroll = ft.ScrollMode.AUTO

    # ======================================
    # INFORMACIÓN DEL TICKET
    # ======================================

    proveedor = ft.TextField(
        label="Proveedor",
        value=datos_ocr["proveedor"],
        expand=True
    )

    folio = ft.TextField(
        label="Folio",
        value=datos_ocr["folio"],
        expand=True
    )

    fecha = ft.TextField(
        label="Fecha de compra",
        value=datos_ocr["fecha_compra"],
        expand=True
    )

    total = ft.TextField(
        label="Total del ticket",
        value=str(datos_ocr["total"]),
        expand=True
    )

    # ======================================
    # PRODUCTOS DETECTADOS
    # ======================================

    lista_productos = ft.Column(spacing=15)

    campos_productos = []

    def construir_productos():

        lista_productos.controls.clear()
        campos_productos.clear()

        for indice, producto in enumerate(datos_ocr["productos"]):

            nombre = ft.TextField(
                label="Nombre",
                value=producto["nombre"],
                expand=True
            )

            presentacion = ft.TextField(
                label="Presentación",
                value=producto["presentacion"],
                expand=True
            )

            cantidad = ft.TextField(
                label="Cantidad",
                value=str(producto["cantidad"]),
                width=120
            )

            precio = ft.TextField(
                label="Precio unitario",
                value=str(producto["precio_unitario"]),
                width=150
            )

            categoria = ft.TextField(
                label="Categoría",
                value=producto["categoria"],
                expand=True
            )

            campos_productos.append({
                "nombre": nombre,
                "presentacion": presentacion,
                "cantidad": cantidad,
                "precio": precio,
                "categoria": categoria,
                "codigo_barras": producto.get("codigo_barras")
            })

            tarjeta = ft.Card(
                content=ft.Container(
                    padding=15,
                    content=ft.Column([
                        ft.Text(
                            f"Producto {indice + 1}",
                            weight=ft.FontWeight.BOLD,
                            size=18
                        ),

                        ft.Row([
                            nombre,
                            presentacion
                        ]),

                        ft.Row([
                            cantidad,
                            precio
                        ]),

                        categoria
                    ])
                )
            )

            lista_productos.controls.append(tarjeta)

    construir_productos()

    # ======================================
    # GUARDAR TICKET
    # ======================================

    boton_guardar = ft.Button(
        "Guardar ticket en base de datos",
        icon=ft.Icons.SAVE,
        width=350
    )

    mensaje = ft.Text(
        "",
        size=16,
        weight=ft.FontWeight.BOLD
    )

    detalle_resultado = ft.Column()

    def guardar_ticket(e):

        boton_guardar.disabled = True
        boton_guardar.text = "Guardando..."
        mensaje.value = ""
        detalle_resultado.controls.clear()

        page.update()

        try:
            # Obtener datos editados
            datos = {
                "proveedor": proveedor.value.strip(),
                "folio": folio.value.strip(),
                "fecha_compra": fecha.value.strip(),
                "total": total.value,
                "ruta_imagen": datos_ocr["ruta_imagen"],
                "productos": []
            }

            for campos in campos_productos:

                datos["productos"].append({

                    "nombre": campos["nombre"].value.strip(),

                    "presentacion": campos["presentacion"].value.strip(),

                    "cantidad": campos["cantidad"].value,

                    "precio_unitario": campos["precio"].value,

                    "codigo_barras": campos["codigo_barras"],

                    "categoria": campos["categoria"].value.strip()

                })

            # Llamar al servicio de inserción
            resultado = crear_ticket(
                datos,
                ID_USUARIO
            )

            mensaje.value = "¡Ticket registrado correctamente!"
            mensaje.color = ft.Colors.GREEN

            detalle_resultado.controls.extend([
                ft.Text(f"ID del ticket: {resultado['id_ticket']}"),
                ft.Text(f"Proveedor: {resultado['proveedor']}"),
                ft.Text(f"ID proveedor: {resultado['id_proveedor']}"),
                ft.Text(f"Subtotal: ${resultado['subtotal']:.2f}"),
                ft.Text(f"Total: ${resultado['total']:.2f}"),
                ft.Text(f"Estado: {resultado['estado']}")
            ])

        except Exception as error:

            mensaje.value = f"No se pudo guardar: {error}"
            mensaje.color = ft.Colors.RED

        finally:

            boton_guardar.disabled = False
            boton_guardar.text = "Guardar ticket en base de datos"

            page.update()

    boton_guardar.on_click = guardar_ticket

    # ======================================
    # DISEÑO DE LA INTERFAZ
    # ======================================

    page.add(

        ft.Row([
            ft.Icon(ft.Icons.STORE, size=35),
            ft.Text(
                "Registro de mercancía",
                size=28,
                weight=ft.FontWeight.BOLD
            )
        ]),

        ft.Text(
            "Rol: Encargado de tienda",
            color=ft.Colors.GREY
        ),

        ft.Divider(),

        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.RECEIPT_LONG, size=30),
                        ft.Text(
                            "Ticket escaneado",
                            size=20,
                            weight=ft.FontWeight.BOLD
                        )
                    ]),

                    ft.Container(
                        height=140,
                        bgcolor=ft.Colors.GREY_200,
                        border_radius=10,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column([
                            ft.Icon(
                                ft.Icons.IMAGE,
                                size=45,
                                color=ft.Colors.GREY_700
                            ),
                            ft.Text(
                                "Aquí se visualizará la fotografía del ticket",
                                color=ft.Colors.GREY_700
                            )
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                    ),

                    ft.Text(
                        "Datos extraídos automáticamente por IA",
                        color=ft.Colors.GREEN
                    )
                ])
            )
        ),

        ft.Text(
            "Información del ticket",
            size=21,
            weight=ft.FontWeight.BOLD
        ),

        proveedor,

        ft.Row([
            folio,
            fecha
        ]),

        total,

        ft.Divider(),

        ft.Text(
            "Productos detectados",
            size=21,
            weight=ft.FontWeight.BOLD
        ),

        lista_productos,

        ft.Divider(),

        ft.Container(
            padding=10,
            content=ft.Column([
                boton_guardar,
                mensaje,
                detalle_resultado
            ])
        )
    )


ft.run(main)