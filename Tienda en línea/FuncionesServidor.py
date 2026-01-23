"""
Funciones para el servidor de la tienda en línea.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 28/09/2025

Descripción:
    Este archivo contiene todas las funciones que usa el servidor de la tienda en
    línea para poder satisfacer las solicitudes del cliente.
"""

import json, socket
from datetime import datetime
from pathlib import Path

def obtenerRuta() -> tuple[Path, Path, Path]:
    """
    Obtiene la ruta del archivo "articulos.json".

    Esta función construye la ruta completa hacia el archivo "articulos.json".

    Returns
    -------
    tuple
        (carpetaScript, rutaArticulos, rutaCarrito)

        - **carpetaScript** (Path): Carpeta del script actual.
        - **rutaArticulos** (Path): Ruta completa del archivo "Articulos.json".
        - **rutaCarrito** (Path): Ruta completa del archivo "Carrito.json".
    """
    carpetaScript = Path(__file__).parent # Se obtiene la ruta de la carpeta del script
    rutaArticulos = carpetaScript/"data"/"Articulos.json" # Construye la ruta completa hacia "Articulos.json"
    rutaCarrito = carpetaScript/"data"/"Carrito.json" # Construye la ruta completa hacia "Carrito.json"
    
    return carpetaScript, rutaArticulos, rutaCarrito

def cargarJSON(ruta: Path) -> dict:
    """
    Convierte los artículos del archivo "Articulos.json" o "Carrito.json" a un diccionario.

    Esta función lee el archivo "Articulos.json" con codificación UTF-8, guarda el objeto
    archivo en "file" y lo convierte a un objeto de tipo Pyhton, es decir; a un diccionario.

    Parameters
    ----------
    ruta : Path
        Ruta del archivo "Articulos.json" o "Carrito.json".

    Returns
    -------
    dict
        Diccionario con los artículos guardados del archivo "Articulos.json" o "Carrito.json.
    """
    with open(ruta, "r", encoding = "utf-8") as file:
        articulos = json.load(file) # Toma "file" y lo convierte a un objeto de tipo Python (deserialización)

    return articulos

def guardarJSON(ruta: Path, diccionarioNuevo: dict) -> None:
    """
    Guarda los cambios hechos en los artículos en el archivo correspondiente:

    Esta función toma el diccionario con los cambios hechos y lo usa para actualizar el
    archivo "Carrito.json" o "Articulos.json".

    Parameters
    ----------
    ruta : Path
        Ruta del archivo "Carrito.json" o "Articulos.json".
    diccionarioNuevo: dict
        Diccionario con las modificaciones a cargar.
    """
    with open(ruta, "w", encoding = "utf-8") as file:
        json.dump(diccionarioNuevo, file, indent = 4, ensure_ascii = False)


def enviarMensaje(mensaje: str, conexion: socket.socket) -> None:
    """
    Envia mensajes al cliente desde el servidor.

    Esta función envia al cliente un mensaje específico desde el servidor.

    Parameters
    ---------
    mensaje : str
        Mensaje a enviar al cliente desde el servidor.
    conexion : socket.socket
        Nuevo socket que representa la conexión con un cliente en particular.
    """
    mensajeEnviar = {"mensaje": [{"msj": f"{mensaje}"}]} # Se crea el JSON con el mensaje

    print(f"\n>> Se envia al cliente: {mensajeEnviar}") # Se imprime lo que se envía al cliente

    respuesta = json.dumps(mensajeEnviar).encode("utf-8") # Convierte el diccionario a una cadena en formato JSON (serialización) y luego a bytes
    conexion.send(respuesta) # Envía los bytes al cliente a traves del socket "conexion" 

def enviarArticulos(ruta: Path, conexion: socket.socket) -> None:
    """
    Envía los artículos de la tienda o del carrito de compras.

    Esta función veriica si hay artículos en la tienda o en el carrito de compras,
    si los hay los envía de lo contrario envía un mensaje de error.

    Parameters
    ----------
    ruta : Path
        Ruta del archivo "Articulos.json" o "Carrito.json".
    conexion : socket.socket
        Nuevo socket que representa la conexión con un cliente en particular.
    """
    articulos = cargarJSON(ruta) # Obtenemos el diccionario con los artículos

    # Verificamos si hay artículos en la tienda o en el carrito
    if ("articulos" in articulos):
        if (not articulos["articulos"]): # Si no hay artículos en la tienda
            enviarMensaje("Servidor: No hay artículos para mostrar.", conexion)
        else:
            print(f"\n>> Se envia al cliente: {articulos}") # Se imprime lo que se envía al cliente

            respuesta = json.dumps(articulos).encode("utf-8") # Convierte el diccionario a una cadena en formato JSON (serialización) y luego a bytes
            conexion.send(respuesta) # Envía los bytes al cliente a traves del socket "conexion"

    if ("carrito" in articulos):
        if (not articulos["carrito"]): # Si no hay artículos en el carrito
            enviarMensaje("Servidor: No hay artículos para mostrar.", conexion)
        else:
            print(f"\n>> Se envia al cliente: {articulos}") # Se imprime lo que se envía al cliente

            respuesta = json.dumps(articulos).encode("utf-8") # Convierte el diccionario a una cadena en formato JSON (serialización) y luego a bytes
            conexion.send(respuesta) # Envía los bytes al cliente a traves del socket "conexion"

def buscarArticulo(rutaArticulos: Path, criterioBusqueda: str, conexion: socket.socket) -> None:
    """
    Busca un artículo que coincida con el nombre o marca indicada por el cliente.

    Esta función busca en los artículos de la tiendo aquel o aquellos que coincidan con la
    marca o nombre de un artículo. Si se encuentra una coincidencia agrega e artículo a un JSON,
    de lo contrario se envía el mensaje correspondiente.

    Parameters
    ----------
    rutaArticulos : Path
        Ruta del archivo "Articulos.json".
    criterioBusqueda : str
        La marca o el nombre del artículo a buscar.
    conexion : socket.socket
        Nuevo socket que representa la conexión con un cliente en particular.
    """
    buscar = criterioBusqueda.lower() # Guardamos el nombre o marca del artículo
    articulos = cargarJSON(rutaArticulos) # Guardamos los artículos en un diccionario
    counter = 0 # Contador de artículos encontrados

    coincidencias = {"articulos": []} # Cremos el JSON con un diccionario vacío

    for art in articulos.get("articulos", []): # Buscamos los artículos
        if ((buscar in art["nombre"].lower()) or (buscar in art["marca"].lower())):
            coincidencias["articulos"].append(art) # Agregamos el artículo que coindice con la búsqueda
            counter += 1

    if (counter > 0): # Si se encontró al menos un artículo
        print(f"\n>> Se envia al cliente: {coincidencias}") # Se imprime lo que se envía al cliente

        respuesta = json.dumps(coincidencias).encode("utf-8") # Serializar el JSON
        conexion.send(respuesta)
    else: # Si no se encontro ningún artículo
        enviarMensaje("Servidor: No hay coincidencias.", conexion)

def agregarCarrito(rutaArticulos: Path, rutaCarrito: Path, criterioBusqueda: str, cantidad: int, conexion: socket.socket) -> None:
    """
    Agrega un artículo al carrito de compras.

    Esta función se encarga de agregar un artículo al carrito de compras, teniendo en cuenta
    algunas consideraciones para esto.

    Parameters
    ----------
    rutaArticulos : Path
        Ruta del archivo "Articulos.json".
    rutaCarrito : Path
        Ruta del archivo "Carrito.json".
    criterioBusqueda : str
        El id o el nombre del artículo a agregar.
    cantidad : int
        Cantidad de ese artículo a agregar.
    conexion : socket.sokect
        Nuevo socket que representa la conexión con un cliente en particular.
    """
    # Revisamos si el criterio de búsqueda fue el nombre o el id del artículo y ajustamos
    # el tipo de la varibale 'buscar'
    if (criterioBusqueda.isdigit()):
        buscar = int(criterioBusqueda)
    else:
        buscar = criterioBusqueda.lower()

    articulos = cargarJSON(rutaArticulos) # Guardamos los artículos en un diccionario
    carrito = cargarJSON(rutaCarrito) # Guardamos los artículos del carrito en un diccionario

    articuloAgregar = None # Aquí se guarda el artículo a agregar

    # Buscamos el artículo a agregar
    for art in articulos.get("articulos", []):
        if (isinstance(buscar, int) and buscar == art["id"]):
            articuloAgregar = art

            break
        elif (isinstance(buscar, str) and buscar in art["nombre"].lower()):
            articuloAgregar = art

            break

    # Verificamos que se haya encontrado el artículo
    if (not articuloAgregar):
        enviarMensaje("Servidor: El artículo no existe en la tienda.", conexion)
        
        return

    # Verificamos si el stock del artículo es suficiente
    if (cantidad > articuloAgregar["stock"]):
        enviarMensaje(f"Servidor: No hay suficiente stock para agregar {cantidad} artículos.", conexion)
        
        return
    
    # Verificamos si el artículo encontrado ya esta en el artículo
    for item in carrito["carrito"]:
        if (item["id"] == articuloAgregar["id"]): # Si ya esta el artículo en el carrito
            if (item["cantidad"] + cantidad > 5): # Si es menor qur 5
                enviarMensaje("Servidor: No pudes agregar más de cinco unidades del mismo artículo.", conexion)

                return
            
            item["cantidad"] += cantidad # Actualizamos la cantidad del artículo en el carrito
            item["precioTotal"] = item["precio"] * item["cantidad"] # Actualizamos el precio total del artículo

            guardarJSON(rutaCarrito, carrito) # Actualizamos el artíclo en el carrito
            enviarMensaje("Servidor: El artículo se actualizó en el carrito.", conexion)

            return
        
    # Se crea el artículo que se va a agregar al carrito, si este no existe previamente
    itemCarrito = articuloAgregar.copy()
    itemCarrito.pop("stock", None) # Se saca el item none del artículo a agregar
    itemCarrito["cantidad"] = cantidad # Se crea el item 'cantidad' en el artículo a agregar
    itemCarrito["precioTotal"] = itemCarrito["precio"] * cantidad # Se calcula el precio total y se cre el item 'precioTotal' en el artículo a agregar

    carrito["carrito"].append(itemCarrito) # Se agregan los items creados al artículo a agregars
    guardarJSON(rutaCarrito, carrito) # Se agrega el artículo al carrito
    enviarMensaje("El artículo se agregó al carrito", conexion)

def eliminarCarrito(rutaCarrito: Path, criterioBusqueda: str, cantidad: int, conexion: socket.socket) -> None:
    """
    Elimina un artículo del carrito de compras.

    Esta función se encarga de eliminar un artículo del carrito de compras, teniendo en cuenta
    algunas consideraciones para esto.

    Parameters
    ----------
    rutaCarrito : Path
        Ruta del archivo "Carrito.json".
    criterioBusqueda : str
        El id o el nombre del artículo a eliminar.
    cantidad : int
        Cantidad de unidades de ese artículo a eliminar.
    conexion : socket.sokect
        Nuevo socket que representa la conexión con un cliente en particular.
    """
    # Revisamos si el criterio de búsqueda fue el nombre o el id del artículo y ajustamos
    # el tipo de la varibale 'buscar'
    if (criterioBusqueda.isdigit()):
        buscar = int(criterioBusqueda)
    else:
        buscar = criterioBusqueda.lower()

    carrito = cargarJSON(rutaCarrito) # Guardamos los artículos del carrito en un diccionario

    articuloEliminar = None # Aquí se guarda el artículo a eliminar

    # Buscamos el artículo a eliminar
    for art in carrito.get("carrito", []):
        if (isinstance(buscar, int) and buscar == art["id"]):
            articuloEliminar = art

            break
        elif (isinstance(buscar, str) and buscar in art["nombre"].lower()):
            articuloEliminar = art

            break

    # Verificamos que se haya encontrado el artículo
    if (not articuloEliminar):
        enviarMensaje("Servidor: El artículo no existe en el carrito.", conexion)
        
        return
    
    # Verificamos si la cantidad del artículo es suficiente
    if (cantidad > articuloEliminar["cantidad"]):
        enviarMensaje(f"Servidor: No hay suficiente artículos para eliminar {cantidad} artículos.", conexion)
        
        return
    
    # Verificamos si el artículo encontrado ya esta en el carrito
    for item in carrito["carrito"]:
        if (item["id"] == articuloEliminar["id"]): # Si ya esta el artículo en el carrito
            if ((item["cantidad"] - cantidad) > 0): # Si todavía restan artículos en el carrito
                item["cantidad"] -= cantidad # Actualizamos la cantidad del artículo en el carrito
                item["precioTotal"] = item["precio"] * item["cantidad"] # Actualizamos el precio total del artículo

                guardarJSON(rutaCarrito, carrito) # Actualizamos el artíclo en el carrito
                enviarMensaje("Servidor: El artículo se actualizó en el carrito.", conexion)
            else: # Ya no hay artículos
                carrito["carrito"].remove(item) # Eliminamos el artículo del carrito
                
                guardarJSON(rutaCarrito, carrito) # Actualizamos el artíclo en el carrito
                enviarMensaje("Servidor: El artículo se eliminó del carrito.", conexion)

            return

def finalizarCompra(rutaArticulos: Path, rutaCarrito: Path, conexion: socket.socket, carpetaScript: Path) -> None:
    """
    Finaliza la compra de los artículos en el carrito.

    Esta función actualiza el stock de los artículos correspondientes en la tienda de acuerdo con los
    agregados al carrito, después de finalizar la compra. También genera el recibo de compra, mostrando
    los artículos comprados con sus respectivos datos y al final el precio total de la compra.

    Parameters
    ----------
    rutaArticulos : Path
        Ruta del archivo "Articulos.json".
    rutaCarrito : Path
        Ruta del archivo "Carrito.json".
    conexion : socket.socket
        Nuevo socket que representa la conexión con un cliente en particular.
    carpetaScript : Path
        Carpeta del script actual.
    """
    articulos = cargarJSON(rutaArticulos) # Guardamos los artículos en un diccionario
    carrito = cargarJSON(rutaCarrito) # Guardamos los artículos del carrito en un diccionario
    fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # Se obtiene la fecha actual
    nombreArchivo = carpetaScript/"recibos"/f"recibo_{fecha}.txt" # Se crea el nombre del recibo

    totalPagar = 0

    # Verificamos que haya algo en el carrito
    if ("carrito" in carrito):
        if (not carrito["carrito"]): # Si no hay artículos en el carrito
            enviarMensaje("Servidor: La compra no puede proceder, el carrito esta vacío.", conexion)
        else:
            # Primero creamos el recibo de la compra
            with open(nombreArchivo, "w", encoding = "utf-8") as file:
                file.write("************ RECIBO DE COMPRA ************\n\n")
                file.write(f"Escuela Superior de Cómputo a {fecha}\n\n")
                for itemC in carrito["carrito"]:
                    file.write(
                        f"{itemC['nombre']} ({itemC['marca']})\n"
                        f"- Cantidad: {itemC['cantidad']}\n"
                        f"- Precio unitario: ${itemC['precio']} MXN\n"
                        f"- Subtotal: ${itemC['precioTotal']} MXN\n\n"
                    )

                    totalPagar += itemC["precioTotal"]

                file.write("==========================================\n")
                file.write(f"TOTAL A PAGAR: ${totalPagar} MXN\n")
                file.write("==========================================\n")

            # Actualizamos el stock de los artículos
            for itemC in carrito["carrito"]: # Iteramos el carrito
                for itemA in articulos["articulos"]: # Iteramos los artículos
                    if (itemC["id"] == itemA["id"]):
                        itemA["stock"] -= itemC["cantidad"] # Restamos la cantidad del artículo al stock de este

                        guardarJSON(rutaArticulos, articulos)

            carrito["carrito"].clear() # Borramos los artículos del carrito
            guardarJSON(rutaCarrito, carrito)

            enviarMensaje(f"Servidor: El total a pagar de los artículos del carrito es ${totalPagar} MXN. Consulta el recibo de tu compra.", conexion)