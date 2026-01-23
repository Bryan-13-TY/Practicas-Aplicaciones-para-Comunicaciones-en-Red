import socket
import selectors
from pathlib import Path
import zipfile
import io
import time

HOST = "127.0.0.1"

PORT_PRIMARIO = 8080
PORT_SECUNDARIO = 8081

POOL_MAX = 5
MITAD_POOL = POOL_MAX // 2

BASE_DIR = Path(__file__).parent
ARCHIVES = BASE_DIR / "archives"

# selector principal que monitorea todos los sockets
selector = selectors.DefaultSelector() 

conexiones_activas = {
    PORT_PRIMARIO: 0,
    PORT_SECUNDARIO: 0
}

MIME_TYPES = {
    ".html": "text/html",
    ".txt": "text/plain",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".pdf": "application/pdf",
}

# se indican los tipos que el navegador puede mostrar
MIMES_RENDERIZABLES = set(MIME_TYPES.values()) 

# -------------------------------------------------

def log_peticion(puerto: int, linea: str) -> None:
    """
    Docstring for log_peticion

    Muestra en consola la petición recibida.
    
    :param puerto: Puerto donde llegó la petición.
    :type puerto: int
    :param linea: Primera línea del request HTTP.
    :type linea: str
    """
    print(f"[PETICIÓN] ({puerto}) {linea}")


def log_respuesta(puerto: int, status: str) -> None:
    """
    Docstring for log_respuesta

    Muestra en consola la respuesta enviada.
    
    :param puerto: Puerto que envía la respuesta.
    :type puerto: int
    :param status: Código HTTP enviado.
    :type status: str
    """
    print(f"[RESPUESTA] ({puerto}) {status}")

# -------------------------------------------------

class Conexion:
    def __init__(self, sock: socket.socket, puerto: int):
        """
        Docstring for __init__
        
        :param sock: Socket del cliente.
        :type sock: socket.socket
        :param puerto: Puerto del servidor que aceptó la conexión.
        :type puerto: int
        """
        self.sock = sock
        self.puerto = puerto
        self.inb = b"" # buffer de entrada (bytes recibidos)
        self.outb = b"" # buffer de salida (respuesta)
        self.headers_completos = False
        self.content_length = 0 # tamaño del body esperado

# -------------------------------------------------

def aceptar(sock: socket.socket, puerto: int) -> None:
    """
    Docstring for aceptar

    Acepta una conexión entrante.
    Verifica si el pool está lleno.
    Registra el socket cliente en el selector.
    Incrementa el contador de conexiones.
    
    :param sock: Socket del servidor.
    :type sock: socket.socket
    :param puerto: Puerto donde llegó la conexión.
    :type puerto: int
    """
    cliente, _ = sock.accept()
    cliente.setblocking(False)

    if conexiones_activas[puerto] >= POOL_MAX: # si el pool está lleno
        cliente.sendall(
            b"HTTP/1.1 503 Service Unavailable\r\n\r\nServidor saturado"
        )
        cliente.close()
        return

    conexiones_activas[puerto] += 1 # incrementa el pool solo si entra
    selector.register(cliente, selectors.EVENT_READ, data=Conexion(cliente, puerto))

# -------------------------------------------------

def leer(con: Conexion) -> None:
    """
    Docstring for leer

    Lee datos del socket sin bloquear.
    Acumula bytes en con.inb.
    Detecta fin de headers.
    Llama a procesar_peticion.
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    """
    datos = con.sock.recv(4096)
    if not datos:
        cerrar(con)
        return

    con.inb += datos

    # headers
    if not con.headers_completos and b"\r\n\r\n" in con.inb:
        headers, resto = con.inb.split(b"\r\n\r\n", 1)
        con.headers_completos = True

        for linea in headers.decode(errors="ignore").splitlines():
            if linea.lower().startswith("content-length"):
                con.content_length = int(linea.split(":")[1].strip())

        con.inb = headers + b"\r\n\r\n" + resto

    # se verifica si ya esta todo
    if con.headers_completos:
        total = len(con.inb.split(b"\r\n\r\n", 1)[1])
        if total >= con.content_length:
            procesar_peticion(con)

# -------------------------------------------------

def procesar_peticion(con: Conexion) -> None:
    """
    Docstring for procesar_peticion

    Extrae el método, ruta y versión.
    Registra la petición.
    Valida los métodos GET, POST, PUT y DELETE.
    Maneja balanceo de carga.
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    """
    texto = con.inb.decode(errors="ignore")
    lineas = texto.splitlines()
    linea = lineas[0]
    log_peticion(con.puerto, linea)

    try:
        metodo, ruta, _ = linea.split()
    except ValueError:
        enviar_error(con, 400, "Bad Request")
        return
    
    # redirige las peticiones al segundo servidor (302)
    if con.puerto == PORT_PRIMARIO and conexiones_activas[PORT_PRIMARIO] > MITAD_POOL:
        redirigir(con, PORT_SECUNDARIO)
        return
    
    # resolver la ruta principal
    if ruta == "/":
        ruta = "/index.html"

    path = ARCHIVES / ruta.lstrip("/")

    body = texto.split("\r\n\r\n", 1)[1].encode()

    # <====== GET ======>
    if metodo == "GET":
        if path.exists() and path.is_dir():
            if not ruta.endswith("/"):
                redirigir_ruta(con, ruta + "/") # 301
                return
            enviar_zip(con, path)
            return

        if not path.exists() or not path.is_file():
            enviar_error(con, 404, "Not Found")
            return

        mime = MIME_TYPES.get(path.suffix, "application/octet-stream")
        contenido = path.read_bytes()

        headers = [
            "HTTP/1.1 200 OK",
            f"Content-Type: {mime}",
            f"Content-Length: {len(contenido)}",
        ]

        if mime not in MIMES_RENDERIZABLES:
            headers.append(
                f'Content-Disposition: attachment; filename="{path.name}"'
            )

        headers.append("\r\n")
        con.outb = ("\r\n".join(headers)).encode() + contenido
        log_respuesta(con.puerto, "200 OK")

    # <====== POST ======>
    elif metodo == "POST":
        if path.exists():
            enviar_error(con, 409, "Conflict") # si ya existe
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

        respuesta = b"Archivo creado correctamente"
        con.outb = (
            "HTTP/1.1 201 Created\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(respuesta)}\r\n\r\n"
        ).encode() + respuesta
        log_respuesta(con.puerto, "201 Created")

    # <====== PUT ======>
    elif metodo == "PUT":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

        respuesta = b"Archivo creado/actualizado"
        con.outb = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(respuesta)}\r\n\r\n"
        ).encode() + respuesta
        log_respuesta(con.puerto, "200 OK")

    # <====== DELETE ======>
    elif metodo == "DELETE":
        if not path.exists():
            enviar_error(con, 404, "Not Found") # no existe
            return

        path.unlink()
        respuesta = b"Archivo eliminado"
        con.outb = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(respuesta)}\r\n\r\n"
        ).encode() + respuesta
        log_respuesta(con.puerto, "200 OK")

    else:
        enviar_error(con, 405, "Method Not Allowed")
        return

    selector.modify(con.sock, selectors.EVENT_WRITE, data=con)

# -------------------------------------------------

def enviar_zip(con: Conexion, carpeta: Path) -> None:
    """
    Docstring for enviar_zip

    Comprime la carpeta en memoria, conservando la estructura interna
    y envía ZIP como descarga.
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    :param carpeta: Ruta de la carpeta.
    :type carpeta: Path
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for archivo in carpeta.rglob("*"):
            if archivo.is_file():
                zipf.write(archivo, archivo.relative_to(carpeta))

    data = buffer.getvalue()
    con.outb = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/zip\r\n"
        f"Content-Length: {len(data)}\r\n"
        f'Content-Disposition: attachment; filename="{carpeta.name}.zip"\r\n\r\n'
    ).encode() + data
    log_respuesta(con.puerto, "200 OK (ZIP)")
    selector.modify(con.sock, selectors.EVENT_WRITE, data=con)

# -------------------------------------------------

def redirigir(con: Conexion, puerto_destino: int) -> None:
    """
    Docstring for redirigir

    Envía un 302 Found al servidor secundario.
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    :param puerto_destino: Puerto del segundo servidor.
    :type puerto_destino: int
    """
    con.outb = (
        "HTTP/1.1 302 Found\r\n"
        f"Location: http://{HOST}:{puerto_destino}\r\n\r\n"
    ).encode()
    log_respuesta(con.puerto, f"302 Redirect -> {puerto_destino}")
    selector.modify(con.sock, selectors.EVENT_WRITE, data=con)


def redirigir_ruta(con: Conexion, nueva: str) -> None:
    """
    Docstring for redirigir_ruta

    Envía un 301 Moved Permanently
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    :param nueva: Ruta de la carpeta con / al final.
    :type nueva: str
    """
    con.outb = (
        "HTTP/1.1 301 Moved Permanently\r\n"
        f"Location: {nueva}\r\n\r\n"
    ).encode()
    log_respuesta(con.puerto, "301 Moved Permanently")
    selector.modify(con.sock, selectors.EVENT_WRITE, data=con)

# -------------------------------------------------

def enviar_error(con: Conexion, codigo: int, mensaje: str) -> None:
    """
    Docstring for enviar_error

    Construye respuesta HTML de error.
    Envúa códigos 400, 404, 405, etc.
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    :param codigo: Código HTTP.
    :type codigo: int
    :param mensaje: Mensaje de estatus.
    :type mensaje: str
    """
    body = f"<h1>{codigo} {mensaje}</h1>".encode()
    con.outb = (
        f"HTTP/1.1 {codigo} {mensaje}\r\n"
        "Content-Type: text/html\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode() + body
    log_respuesta(con.puerto, f"{codigo} {mensaje}")
    selector.modify(con.sock, selectors.EVENT_WRITE, data=con)

# -------------------------------------------------

def escribir(con: Conexion) -> None:
    """
    Docstring for escribir

    Envía el contenido de outb en bloques.
    Permite escritura no bloqueante.
    Cierra la conexión al terminar.
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    """
    enviados = con.sock.send(con.outb)
    con.outb = con.outb[enviados:]
    if not con.outb:
        #time.sleep(3) # simula cliente activo
        cerrar(con)

def cerrar(con: Conexion) ->None:
    """
    Docstring for cerrar

    Elimina el socket del selector.
    Cierra la conexión.
    Decrementa el contador del pool.
    
    :param con: Objeto de conexión activa.
    :type con: Conexion
    """
    selector.unregister(con.sock)
    con.sock.close()
    conexiones_activas[con.puerto] -= 1

# -------------------------------------------------

def iniciar_servidor(puerto: int) -> None:
    """
    Docstring for iniciar_servidor

    Crea el socket TCP, lo pone en modo no bloqueante y lo registra en el selector.
    
    :param puerto: Puerto del servidor principal.
    :type puerto: int
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, puerto))
    sock.listen()
    sock.setblocking(False)

    selector.register(sock, selectors.EVENT_READ, data=puerto)
    print(f"Servidor escuchando en http://{HOST}:{puerto}")


def main() -> None:
    """
    Docstring for main

    Inicializa ambos servidores
    """
    iniciar_servidor(PORT_PRIMARIO)
    iniciar_servidor(PORT_SECUNDARIO)

    while True:
        for key, mask in selector.select():
            if isinstance(key.data, int):
                aceptar(key.fileobj, key.data) # type: ignore
            else:
                con = key.data
                if mask & selectors.EVENT_READ:
                    leer(con)
                if mask & selectors.EVENT_WRITE:
                    escribir(con)

if __name__ == "__main__":
    main()