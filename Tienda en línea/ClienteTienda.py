"""
Cliente de la tienda en línea.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 28/09/2025

Descripción:
    Este archivo contiene la creación y el flujo del cliente de la tienda en línea.
"""

import json, socket
from FuncionesCliente import listarArticulos, limpiarTerminal, mostrarBusqueda
from FuncionesCliente import mostrarMensaje, mostrarCarrito, esperarTecla

# Cremos al cliente y lo conectamos al servidor
cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creamos al cliente (dirección IPv4, protocolo TCP)
cliente.connect(("127.0.0.1", 5000)) # Conectamos al cliente con el servidor (dirección IP, puerto)

# Menú del cliente
while (True): # Mientras no se cierre el cliente
    limpiarTerminal()
    print("""
/*---------------------------.
| TIENDA EN LÍNEA: LALITOXDE |
`---------------------------*/

>> Elije una de las opciones

1.- Listar artículos de la tienda
2.- Buscar un artículo
3.- Carrito de compras
4.- Finalizar la compra
5.- Salir de la tienda
""")
    
    opcion = input("Opción: ").strip()

    match (opcion):
        case '1':
            print("""
/*--------------------------------.
| LISTA DE ARTÍCULOS EN LA TIENDA |                  
`--------------------------------*/
""")
            solicitud = {"accion": "LISTAR_ARTICULOS"} # Creamos la solicitud como un diccionario
            cliente.send(json.dumps(solicitud).encode("utf-8")) # Enviamos al servidor la solicitud serializada
            datosRecibidos = cliente.recv(4096).decode() # Recibe y deserializa los datos recibidos desde el servidor

            articulos = json.loads(datosRecibidos) # Convierte los datos recibidos en JSON a un diccionario

            if ("mensaje" in articulos): # No hay artículos en la tienda
                mostrarMensaje(articulos)
            else: # Si hay al menos un artículos en la tienda
                listarArticulos(articulos)

            # Esperamos una tecla
            print("\n>> Presiona una tecla para continuar...")
            tecla = esperarTecla()

        case '2':
            print("""
/*-------------------.
| BUSCAR UN ARTÍCULO |                  
`-------------------*/
""")
            buscar = input("Escribe el nombre o la marca del/los artículo(s) a buscar: ").strip()

            solicitud = {"accion": "BUSCAR_ARTICULOS", "buscar": buscar} # Creamos la solicitud como un diccionario
            cliente.send(json.dumps(solicitud).encode("utf-8")) # Enviamos al servidor la solicitud serializada
            datosRecibidos = cliente.recv(4096).decode() # Recibe y deserializa los datos recibidos desde el servidor

            resultadoBusqueda = json.loads(datosRecibidos) # Convierte los datos recibidos en JSON a un diccionario

            if ("mensaje" in resultadoBusqueda): # No hubo coincidencias
                print()
                mostrarMensaje(resultadoBusqueda)
            else: # Si hubo al menos una coincidencia
                mostrarBusqueda(resultadoBusqueda) # # Se muestran los artículos encontrados
            
            # Esperamos una tecla
            print("\n>> Presiona una tecla para continuar...")
            tecla = esperarTecla()

        case '3':
            # Menú para el carrito
            while (True):
                limpiarTerminal()
                print("""
/*-------------------.
| CARRITO DE COMPRAS |
`-------------------*/
                  
>> Elije una de las opciones

1.- Ver carrito
2.- Agregar un artículo al carrito
3.- Eliminar un artículo del carrito
4.- Volver
""")
                
                opcion = input("Opción: ").strip()

                match (opcion):
                    case '1':
                        print("""
/*------------------------.
| ARTÍCULOS EN EL CARRITO |                              
`------------------------*/
""")
                        solicitud = {"accion": "MOSTRAR_CARRITO"} # Creamos la solicitud como un diccionario
                        cliente.send(json.dumps(solicitud).encode("utf-8")) # Enviamos al servidor la solicitud serializada
                        datosRecibidos = cliente.recv(4096).decode() # Recibe y deserializa los datos recibidos desde el servidor

                        articulosCarrito = json.loads(datosRecibidos) # Convierte los datos recibidos en JSON a un diccionario

                        if ("mensaje" in articulosCarrito): # El carrito esta vacío
                            mostrarMensaje(articulosCarrito)
                        else: # Si hay al menos un artículo en el carrito
                            mostrarCarrito(articulosCarrito)

                        # Esperamos una tecla
                        print("\n>> Presiona una tecla para continuar...")
                        tecla = esperarTecla()

                    case '2':
                        print("""
/*-----------------.
| AGREGAR ARTÍCULO |
`-----------------*/
""")
                        agregar = input("Escribe el id o el nombre del artículo a agregar: ").strip()
                        cantidad = input("Escribe la cantidad a agregar de ese artículo (máx 5, min 1): ").strip()

                        if (cantidad.isdigit() and (5 >= int(cantidad) > 0)):
                            solicitud = {"accion": "AGREGAR_CARRITO", "articulo": agregar, "cantidad": cantidad} # Creamos la solicitud como un diccionario
                            cliente.send(json.dumps(solicitud).encode("utf-8")) # Enviamos al servidor la solicitud serializada

                            datosRecibidos = cliente.recv(4096).decode() # Recibe y deserializa los datos recibidos desde el servidor
                            confirmacion = json.loads(datosRecibidos) # Convierte los datos recibidos en JSON a un diccionario

                            if ("mensaje" in confirmacion): # El carrito esta vacío
                                print()
                                mostrarMensaje(confirmacion)
                        else:
                            print("\n>> Ingresa una cantidad válida")

                        # Esperamos una tecla
                        print("\n>> Presiona una tecla para continuar...")
                        tecla = esperarTecla()

                    case '3':
                        print("""
/*------------------.
| ELIMINAR ARTÍCULO |            
`------------------*/
""")
                        eliminar = input("Escribe el id o el nombre del artículo a eliminar: ").strip()
                        cantidad = input("Escribe la cantidad a eliminar de ese artículo: ").strip()

                        if (cantidad.isdigit() and int(cantidad) > 0):
                            solicitud = {"accion": "ELIMINAR_CARRITO", "articulo": eliminar, "cantidad": cantidad} # Creamos la solicitud como un diccionario
                            cliente.send(json.dumps(solicitud).encode("utf-8")) # Enviamos al servidor la solicitud serializada

                            datosRecibidos = cliente.recv(4096).decode() # Recibe y deserializa los datos recibidos desde el servidor
                            confirmacion = json.loads(datosRecibidos) # Convierte los datos recibidos en JSON a un diccionario

                            if ("mensaje" in confirmacion): # El carrito esta vacío
                                print()
                                mostrarMensaje(confirmacion)
                        else:
                            print("\n>> Ingresa una cantidad válida")

                        # Esperamos una tecla
                        print("\n>> Presiona una tecla para continuar...")
                        tecla = esperarTecla()

                    case '4':
                        break

                    case _:
                        print("\n>> La opción no es válida")

                        # Esperamos una tecla
                        print("\n>> Presiona una tecla para continuar...")
                        tecla = esperarTecla()

        case '4':
            print("""
/*--------------------.
| FINALIZAR LA COMPRA |                  
`--------------------*/
""")
            solicitud = {"accion": "FINALIZAR_COMPRA"} # Creamos la solicitud como un diccionario
            cliente.send(json.dumps(solicitud).encode("utf-8")) # Enviamos al servidor la solicitud serializada
            datosRecibidos = cliente.recv(4096).decode() # Recibe y deserializa los datos recibidos desde el servidor

            totalPagar = json.loads(datosRecibidos) # Convierte los datos recibidos en JSON a un diccionario

            if ("mensaje" in totalPagar):
                mostrarMensaje(totalPagar)

            # Esperamos una tecla
            print("\n>> Presiona una tecla para continuar...")
            tecla = esperarTecla()

        case '5':
            print("\n>> Gracias por visitar nuestra tienda, esperamos volverte a ver")
            cliente.close()
            break

        case _:
            print("\n>> La opción no es válida")

            # Esperamos una tecla
            print("\n>> Presiona una tecla para continuar...")
            tecla = esperarTecla()