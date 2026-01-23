"""
Archivo 'servidor.py': Este archivo implementa un servidor HTTP en python usando
sockets y threading, con estas características:

    - Atiende peticiones HTTP en el puerto 8080 (servidor primario)
    - Si hay demasidas conexiones, inicia automáticamente un segundo servidor en el 8081
    - Soporta los metodos:
        - GET -> leer archivos
        - POST -> crear archivos
        - PUT -> actualizar archivos
        - DELETE -> eliminar archivos
    - Usa un pool de conexiones máximo de 10
    - Genera un ID único (UUID) por conexión
    - Muestra hora, ID y estado en consola
    - Guarda los archivos en diferentes carpetas según el servidor:
        - archivos_1 (8080)
        - archivos_2 (8081) 

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 06/12/2025
"""

import socket
import threading
import time
import uuid # para los ID únicos de las conexiones 
from datetime import datetime
from pathlib import Path

import utils

HOST = "127.0.0.1"

# puertos
PUERTO_PRIMARIO = 8080
PUERTO_SECUNDARIO = 8081

# carpetas
CARPETA_SCRIPT = Path(__file__).parent
CARPETA_PRIMARIA = CARPETA_SCRIPT / "archivos1"
CARPETA_SECUNDARIA = CARPETA_SCRIPT / "archivos2"

# pool
POOL_MAX = 6
MITAD_POOL = POOL_MAX // 2
pool = threading.Semaphore(POOL_MAX) # limita realmente a clientes activos

conexiones_activas = 0 
lock = threading.Lock() # contador protegido para concurrencia

segundo_servidor_iniciado = False # evita arrancar el servidor secundario más de una vez

MIME_TYPES = {
    ".html": "text/html",
    ".json": "application/json",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".pdf": "application/pdf",
}

def ahora() -> str:
    """Devuelve le fecha/hora actual como string 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def obtener_mime(archivo: Path) -> str:
    """
    Devuelve el MIME según la extensión (archivo.suffix). Si no esá mapeada devuelve 'application/octet-stream'.
    
    Parameters
    ----------
    archivo : Path
        Ruta del archivo en la petición.

    Returns
    -------
    str
        MIME, 'application/octet-stream' en caso de no estar mapeada.
    """
    return MIME_TYPES.get(archivo.suffix, "application/octet-stream")


def leer_body(peticion: str) -> str:
    """
    Devuelve el cuerpo de la petición.

    Parameters
    ----------
    peticion : str
        Texto bruto recibido (headers + body).

    Returns
    -------
    str
        Cuerpo de la petición si lo encuentra, en caso contrario ''.
    """
    # FIXME se asume que toda la petición llego en un solo recv()
    # FIXME pero habría que acumular hasta \r\n\r\ny luego, si hay body leer Content-Length
    separador = "\r\n\r\n"

    if separador in peticion: # si el cuerpo existe en la petición
        return peticion.split(separador, 1)[1]
    
    return ""


def enviar_respuesta(cliente: socket.socket, status_line: str, content_type: str, body: str) -> None:
    """
    Codifica el cuerpo de la petición a bytes, construye la cabecera con Content-Length
    y envía cabecera + body_bytes (respuesta) en una sola sendall().
    
    Parameters
    ----------
    cliente : socket.socket
        Socket del cliente al quien se envía la respuesta.
    status_line : str
        Estatus de la respuesta.
    content_type : str
        Tipo del contenido de acuerdo a MIME.
    body : str
        Contenido de la respuesta.
    """
    body_bytes = body.encode("utf-8")

    cabecera = (
        f"{status_line}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"\r\n"
    )
    cliente.sendall(cabecera.encode() + body_bytes)


def procesar_peticion(cliente: socket.socket, peticion: str, carpeta_base: Path, puerto: int) -> None:
    """
    Se extrae la primeta línea de la petición, de esta se extrae el método y la ruta.
    Mapea / a /index.html y envía la respuesta al cliente de acuerdo al tipo del método.

    Parameters
    ----------
    cliente : socket.socket
        Socket del cliente a quien se envía la respuesta.
    peticion : str
        Texto bruto recibido (headers + body).
    carpeta_base : Path
        Carpeta con los archivos solicitados en la petición.
    puerto: int
        Puerto del servidor.
    """
    linea = peticion.splitlines()[0] # ejemplo 'GET /mensaje.txt HTTP/1.1'
    metodo, ruta, _ = linea.split() # FIXME no hay manejo de errores si la petición está mal formada

    if ruta == "/":
        ruta = "/index.html"

    archivo = carpeta_base / ruta.lstrip("/")

    # ====== GET ======
    if metodo == "GET":
        if archivo.exists() and archivo.is_file():
            contenido = archivo.read_bytes()
            mime = obtener_mime(archivo)

            cabecera = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: {mime}\r\n"
                f"Content-Length: {len(contenido)}\r\n"
                "\r\n"
            ).encode()

            print("_" * 50)
            print(f"{utils.BLUE}<====== RESPUESTA ({puerto}) ======>{utils.RESET}")
            print(cabecera.decode(errors="ignore"))
            print("_" * 50)

            cliente.sendall(cabecera + contenido)
        else:
            body = "<h1>404 - Archivo no encontrado</h1>"
            enviar_respuesta(cliente, "HTTP/1.1 404 Not Found", "text/html", body)

    # ====== POST ======
    elif metodo == "POST":
        body = leer_body(peticion) # texto a escribir en un .txt

        archivo.write_text(body, encoding="utf-8")
        respuesta_body = f"Archivo {archivo.name} creado correctamente en {carpeta_base}"
        
        enviar_respuesta(
            cliente,
            "HTTP/1.1 201 Created",
            "text/plain",
            respuesta_body
        )

    # ====== PUT ======
    elif metodo == "PUT":
        body = leer_body(peticion) # texto a escribir en un .txt

        if archivo.exists():
            archivo.write_text(body, encoding="utf-8")

            respuesta_body = f"Archivo {archivo.name} actualizado correctamente"

            enviar_respuesta(
                cliente,
                "HTTP/1.1 200 OK",
                "text/plain",
                respuesta_body
            )
        else:
            enviar_respuesta(
                cliente,
                "HTTP/1.1 404 Not Found",
                "text/plain",
                "Archivo no existe"
            )
    
    # ====== DELETE ======
    elif metodo == "DELETE":
        if archivo.exists():
            archivo.unlink()

            respuesta_body = f"Archivo {archivo.name} eliminado"

            enviar_respuesta(
                cliente,
                "HTTP/1.1 200 OK",
                "text/plain",
                respuesta_body
            )
        else:
            enviar_respuesta(
                cliente,
                "HTTP/1.1 404 Not Found",
                "text/plain",
                "Archivo no encontrado"
            )

    # ====== OTROS ======
    else:
        enviar_respuesta(
            cliente,
            "HTTP/1.1 405 Method Not Allowed",
            "text/plain",
            "Método no permitido"
        )


def atender_cliente(cliente: socket.socket, carpeta_base: Path, puerto: int) -> None:
    """
    See encarga de recibit la petición.

    Parameters
    ----------
    cliente : socket.socket
        Socket del cliente al quien se envía la respuesta.
    carpeta_base : Path
        Carpeta con los archivos solicitados en la petición.
    puerto : int
        Puerto del servidor.
    """
    # Si ya hay 10 clientes ocupando el semáforo, rechazas inmediatamente con 503. Esto limita realmente concurrencia.
    if not pool.acquire(blocking=False): 
        cliente.sendall(
            b"HTTP/1.1 503 Service Unavailable\r\n"
            b"Content-Type: text/plain\r\n\r\n"
            b"Servidor saturado"
        )
        cliente.close()

        return
    
    global conexiones_activas

    conexion_id = uuid.uuid4().hex[:8] # genera un ID único

    with lock: # protege y aumenta el incremento del contador
        conexiones_activas += 1
        print(f"[{ahora()}] [+] [ID: {conexion_id}] ({puerto}) Conexiones activas: {conexiones_activas}")

    try:
        datos = cliente.recv(4096) # FIXME asume petición completa en 4096 bytes
        peticion = datos.decode("utf-8", errors="ignore")

        if not peticion:
            return
        
        linea = peticion.splitlines()[0] # ejemplo 'GET /mensaje.txt HTTP/1.1'
        print(f"[{ahora()}] [ID: {conexion_id}] PETICIÓN => {linea}")

        with lock:
            redirigir = conexiones_activas > MITAD_POOL and puerto == PUERTO_PRIMARIO

        if redirigir: # sobrepasa la cantidad de clientes activos
            respuesta = (
                "HTTP/1.1 302 Found\r\n"
                f"Location: http://{HOST}:{PUERTO_SECUNDARIO}\r\n\r\n"
            )

            cliente.sendall(respuesta.encode())
            print(f"[{ahora()}] [ID: {conexion_id}] REDIRECCIONANDO A PUERTO {PUERTO_SECUNDARIO}")

            return
        
        procesar_peticion(cliente, peticion, carpeta_base, puerto)

        print(f"[{ahora()}] [ID: {conexion_id}] RESPUESTA enviada correctamente")
        time.sleep(2) # HACK simulación de carga
    except Exception as e:
        print(f"[{ahora()}] [ID: {conexion_id}] ERROR: {e}")

        try:
            cliente.sendall(
                b"HTTP/1.1 500 Internar Server Error\r\n"
                b"Content-Type: text/plain\r\n\r\n"
                b"Error interno del servidor"
            )
        except:
            pass

    finally: # libera semáforo para aceptar nuevas conexiones y decrementa contador.
        cliente.close()

        with lock:
            conexiones_activas -= 1
            print(f"[{ahora()}] [-] [ID: {conexion_id}] ({puerto}) Conexiones activas: {conexiones_activas}")

        pool.release()


def iniciar_servidor(puerto: int, carpeta_base: Path) -> None:
    """
    Inicia el primero o segundo servidor.

    Parameters
    ----------
    puerto : int
        Puerto del servidor.
    carpeta_base : Path
        Carpeta con los archivos solicitados en la petición.
    """
    global segundo_servidor_iniciado

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind((HOST, puerto))
    servidor.listen()

    print(f"Servidor escuchando en http://{HOST}:{puerto} usando {carpeta_base}")

    while True:
        cliente, _ = servidor.accept()

        iniciar_segundo = False

        with lock:
            if conexiones_activas >= MITAD_POOL and not segundo_servidor_iniciado and puerto == PUERTO_PRIMARIO:
                segundo_servidor_iniciado = True
                iniciar_segundo = True

        if iniciar_segundo:
            print(f"\n{utils.RED}>>> INICIANDO SEGUNDO SERVIDOR (8081) <<<{utils.RESET}\n")

            threading.Thread(
                target=iniciar_servidor,
                args=(PUERTO_SECUNDARIO, CARPETA_SECUNDARIA),
                daemon=True
            ).start()

        hilo = threading.Thread(
            target=atender_cliente,
            args=(cliente, carpeta_base, puerto)
        )
        hilo.start()

if __name__ == "__main__":
    iniciar_servidor(PUERTO_PRIMARIO, CARPETA_PRIMARIA)