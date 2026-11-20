from productos.crud_productos import obtener_productos


try:

    productos = obtener_productos()

    print("\n========== INVENTARIO ==========\n")

    if not productos:

        print("No hay productos registrados.")

    else:

        for producto in productos:

            print("--------------------------------")

            print("ID:", producto["id_producto"])

            print("Producto:", producto["nombre"])

            print("Presentación:", producto["presentacion"])

            print("Proveedor:", producto["proveedor"])

            print("Categoría:", producto["categoria"])

            print("Stock:", producto["stock_actual"])

            print("Precio:", producto["precio_venta"])

        print("--------------------------------")

        print("Total de productos:", len(productos))


except Exception as error:

    print("Error:", error)