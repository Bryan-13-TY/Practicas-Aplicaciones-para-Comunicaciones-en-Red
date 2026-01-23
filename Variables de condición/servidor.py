import socket
import sys
from pathlib import Path

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
BUFFER_SIZE = 4096

script = Path(__file__).parent
carpeta_destino = script / "archivos_recibidos"
carpeta_destino.mkdir(parents=True, exist_ok=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((SERVER_IP, SERVER_PORT))

print(f"Servidor escuchando en {SERVER_IP}: {SERVER_PORT}...")

# se recibe el nombre del archivo a enviar
nombre_arhivo, addr = sock.recvfrom(BUFFER_SIZE)
nombre_arhivo = nombre_arhivo.decode().strip()
print(f"\nRecibiendo archivo: {nombre_arhivo} desde {addr}")

ruta_archivo = carpeta_destino / nombre_arhivo

with open(ruta_archivo, "wb") as f:
    num_paquete = 0
    total_bytes = 0
    max_paquetes_update = 10 # se actualiza el número de paquetes recibidos cada 10
    archivo_completo = False # bandera para saber si el envío esta completo

    while True:
        data, _ = sock.recvfrom(BUFFER_SIZE)

        # se recibieron todos los paquetes
        if data == b"__FIN__": # cliente termina la transmisión
            archivo_completo = True
            break

        # se detiene la transmisión de paquetes
        if data == b"__ABORT__": # cliente aborta la transmisión
            archivo_completo = False
            print("\n>> Transmisión interrumpida por el cliente")
            break

        # escribir los paqutes en disco
        f.write(data) # cada paquete se escribe en el archivo
        f.flush() # asegura el vaciado del buffer de escritura
        num_paquete += 1
        total_bytes += len(data)

        # mostrar barra cada cierto número de paquetes
        if num_paquete % max_paquetes_update == 0:
            sys.stdout.write(f"\rRecibiendo paquetes... {num_paquete} recibidos")
            sys.stdout.flush()

# mostrar resultado de la transmisión
if archivo_completo:
    print(f"\n>> Archivo recibido completamente")
else:
    print(f"\n>> Archivo incompleto (transmisión interrumpida)")

print(f">> Total de paquetes recibidos: {num_paquete}")
print(f">> Bytes totales recibidos: {total_bytes}")
print(f">> Archivo guardado en: {ruta_archivo}")