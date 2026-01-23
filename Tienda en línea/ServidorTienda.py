"""
Servidor de la tienda en línea.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 28/09/2025

Descripción:
    Este archivo contiene la creación y el flujo del servidor de la tienda en línea.
"""

import socket, json
from FuncionesServidor import obtenerRuta, enviarArticulos, buscarArticulo
from FuncionesServidor import agregarCarrito, eliminarCarrito, finalizarCompra

# Obetenos las rutas de los archivos JSON (Articulos.json, Carrito.json) y de la carpeta del script
carpetaScript, rutaArticulos, rutaCarrito = obtenerRuta()

# Cremos el servisor y lo conectamos al cliente
servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creamos al servidor (dirección IPv4, protocolo TCP)
servidor.bind(("127.0.0.1", 5000)) # Conectamos el servidor a la IP y al puerto
servidor.listen(2) # El socket esta en modo servidor, (2) = espera una solicitud en cola

print(">> Servidor en espera de clientes...")

# Aquí empieza el servidor a operar
while (True): # El servidor simpre activo
    conn, addr = servidor.accept() # Espera que un cliente se conecte al socket del servidor (conexión con cliente, dirección del cliente)

    print(f"\n>> Cliente conectado desde: {addr}")

    while (True): # Se mantiene la conexión abierta con el cliente
        # Verificamos la conexión con el cliente
        try:
            pedido = conn.recv(4096).decode() # Recibimos la solicitud del cliente

            # Verificamos si la solicitud llego
            if not pedido:
                print("\n>> Cliente desconectado")

                break

            print(f"\n>> Se recibe desde el cliente la solicitud: {pedido}")

            # Intentamos interpretar la solicitud del cliente (JSON) 
            try:
                solicitud = json.loads(pedido) # Convierte la solicitud en JSON a un diccionario
            except json.JSONDecodeError:
                conn.send(b"Solicitud no valida")

                continue

            # Revisamos las solicitudes
            if (solicitud["accion"] == "LISTAR_ARTICULOS"):
                enviarArticulos(rutaArticulos, conn)
            elif (solicitud["accion"] == "BUSCAR_ARTICULOS"):
                buscarArticulo(rutaArticulos, solicitud["buscar"], conn)
            elif (solicitud["accion"] == "MOSTRAR_CARRITO"):
                enviarArticulos(rutaCarrito, conn)
            elif (solicitud["accion"] == "AGREGAR_CARRITO"):
                agregarCarrito(rutaArticulos, rutaCarrito, solicitud["articulo"], int(solicitud["cantidad"]), conn)
            elif (solicitud["accion"] == "ELIMINAR_CARRITO"):
                eliminarCarrito(rutaCarrito, solicitud["articulo"], int(solicitud["cantidad"]), conn)
            elif (solicitud["accion"] == "FINALIZAR_COMPRA"):
                finalizarCompra(rutaArticulos, rutaCarrito, conn, carpetaScript)
            else:
                conn.send(b"Comando no reconocido")

        except ConnectionResetError:
            print("\n>> El cliente cerró la conexión abruptamente")
            
            break
    
    conn.close() # Cerrar la conexión con el cliente