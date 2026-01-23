import socket, struct, tempfile
from pathlib import Path
from Reproductor import reproductor

SERVER = ("127.0.0.1", 5000)
MAX_BYTES_PAQUETE = 1024 # Tamaño máximo en bytes del contenido útil dentro de cada paquete
ENCABEZADO_FORMAT = "!I" # Se usa para convertir el número de secuencia a 'bytes'
ENCABEZADO_SIZE = 4 # Tamaño en bytes del encabezado

def pedirLista(sock: socket.socket) -> list[str]:
    sock.sendto(b"LIST", SERVER) # Se envía el mensaje al servidor para pedir la lista de canciones
    data, _ = sock.recvfrom(65536) # Espera la respuesta del servidor
    canciones = data.decode().split("::") if data else [] # Se convierte la respuesta en lista
    lista_canciones = [s for s in canciones if s] # Lista final con las canciones

    return lista_canciones

def recibeCancion_gbn(sock: socket.socket, nombre_cancion: str, timeout=2.0, window_size=6) -> str:
    """
    Recibe el archivo .mp3.

    Parameters
    ----------
    sock : socket.socket
        Socket UDP ya creado y enlazado.
    nombre_cancion : strr
        Nombre de la canción elegida por el cliente.
    timeout : float
        Tiempo límite para recibir respuesta del servidor.
    window_size : int
        Número máximo de paquetes "en vuelo" (tamaño de la ventana GBN).
    """
    sock.sendto(f"GET:{nombre_cancion}".encode(), SERVER) # Solocita al servidor el envio de la canción indicada
    sock.settimeout(5.0) # Tiempo límite de espera para recibir información sobre la canción

    try:
        data, _ = sock.recvfrom(65536) # Se recibe la respuesta del servidor
    except socket.timeout: # Si el tiempo de espera para recibir respuesta del servidor se excede
        # Se considera que no hubo respuesta del servidor
        raise RuntimeError(">> Se excedio el tiempo de espera para la respuesta del servidor")

    encabezado = data.decode(errors="ignore")

    if (encabezado.startswith("ERROR")): # Si el encabezado de la respuesta del servidor indica error
        raise RuntimeError(">> El servidor respondió con el error: " + encabezado)
    
    if (not encabezado.startswith("FILEINFO")): # Si el encabezado de la respuesta del servidor no indica el envio de meta datos
        raise RuntimeError(">> Respuesta inesperada: " + encabezado)
    
    # Si el encabezado de la respuesta del servidor indica el envio de meta datos
    # Se parsea el mensaje FILEINFO|name|tamano_archivo|total_paquetes
    partes = encabezado.split("|") # Se divide el encabezado en partes

    _, nombre_archivo, tamano_archivo_s, total_paquetes_s = partes # Se extraen las partes del encabezado
    tamano_archivo = int(tamano_archivo_s) # Se obtiene el tamaño del archivo .mp3 en bytes
    total_paquetes = int(total_paquetes_s) # Se ontiene el total de paquetes enviados por el servidor

    print(f">> Se recibe del servidor: '{nombre_archivo}' ({tamano_archivo} bytes) en {total_paquetes} paquetes")

    # Se prepara el buffer para recibir los paquetes
    paquetes = {} # Diccionario donde se guardan los paquetes recibidos indexados por número de secuencia
    num_seq_esperado = 0 # Número de secuencia que se espera recibir

    sock.settimeout(timeout) # Tiempo límite de espera para recibir un paquete desde el servidor

    # Bucle donde se reciben los paquetes desde el servidor
    while (num_seq_esperado < total_paquetes): # Mientras no se reciban todos los paquetes
        try:
            paquete, _ = sock.recvfrom(4096) # Se intenta leer un paquete bloqueante
        except socket.timeout: # Si el tiempo de espera para recibir un paquete se excede
            ACK_seq = num_seq_esperado - 1 # Número de secuencia del último paquete confirmado

            if (ACK_seq >= 0): # Si el número de secuencia es válido
                ACK_paquete = b"ACK" + struct.pack(ENCABEZADO_FORMAT, ACK_seq)
                sock.sendto(ACK_paquete, SERVER) # Se reenvía al servidor el número de secuencia del último paquete confirmado (ACK)

            print(f">> No se recibió el paquete: Se reenvia ACK{ACK_seq} del último paquete confirmado")

            continue

        if (paquete == b"FIN"): # Rompe la señal de fin envada por el servidor
            break

        # Se verifica el tamaño mínimo del paquete
        if (len(paquete) < ENCABEZADO_SIZE):
            continue

        num_seq = struct.unpack(ENCABEZADO_FORMAT, paquete[:ENCABEZADO_SIZE])[0] # Se extrae el número de secuencia del encabezado del paquete recibido
        bytes_paquete = paquete[ENCABEZADO_SIZE:] # Se extrae del archivo el fragmento de datos (bytes) recibidos en este paquete

        # Lógica para la aceptación del paquete
        if (num_seq == num_seq_esperado): # Si el paquete es el esperado
            paquetes[num_seq] = bytes_paquete # Se acepta el paquete y se guarda

            while (num_seq_esperado in paquetes): # Se verifica si el número de secuencia ya esta guardado
                num_seq_esperado += 1 # Se actualiza el número de secuencia que se espera recibir
                # Todo en orden

            # Se envía el número de secuencia del último paquete confirmado (ACK)
            ACK_enviar = num_seq_esperado - 1
            ACK_paquete = b"ACK" + struct.pack(ENCABEZADO_FORMAT, ACK_enviar)
            sock.sendto(ACK_paquete, SERVER) # Se envía al servidor el número de secuencia del último paquete confirmado (ACK) (actualizado)
            
            print(f">> Se recibe y se envía ACK{ACK_enviar}")
        elif (num_seq > num_seq_esperado): # Si el paquete esta fuera de orden
            if (num_seq not in paquetes):
                paquetes[num_seq] = bytes_paquete # Se guarda el paquete para el futuro

            # Se reenvia el número de secuencia del último paquete confirmado (válido) (ACK)
            ACK_seq = num_seq_esperado - 1

            if (ACK_seq >= 0): # Si el número de secuencia es válido
                ACK_paquete = b"ACK" + struct.pack(ENCABEZADO_FORMAT, ACK_seq)
                sock.sendto(ACK_paquete, SERVER)
        else: # Si el paquete ya se ha recibido (duplicado)
            ACK_paquete = b"ACK" + struct.pack(ENCABEZADO_FORMAT, num_seq)
            sock.sendto(ACK_paquete, SERVER) # Se reenvia el número de secuencia extraido del encabezado del paquete recibido

    # Se ensamblan los bytes en orden del archivo y se almacena temporalmente
    bytes_archivo = bytearray()

    for pack in range(total_paquetes): # Se concatenan en orden los chunks (paquetes) desde 0 hasta total_paquetes
        chunk = paquetes.get(pack, b"")
        bytes_archivo.extend(chunk)

    bytes_archivo = bytes_archivo[:tamano_archivo] # Se recorta el exceso (último chunk)

    # Se crea y guarda un archivo temporal
    temporal = tempfile.NamedTemporaryFile(delete=False, suffix="." + Path(nombre_archivo).suffix.lstrip("."))
    temporal.write(bytes_archivo) # Se escribe todo el comtenido del archivo
    temporal.flush()
    ruta_temporal = temporal.name
    temporal.close()

    print(f"\n>> Archivo guardado temporalmente en: {ruta_temporal}")

    return ruta_temporal # Devuelve la ruta temporal

def main():
    # Se crea el socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(5.0) # Tiempo límite para recibir la lista de canciones

    print(">> Se solicita la lista de canciones al servidor...\n")
    lista_canciones = pedirLista(sock) # Se obtiene la lista de canciones

    if (not lista_canciones): # Si no hay canciones
        print("\n>> No hay canciones disponibles o no se pudó obtener la lista")

        return
    
    print("Canciones disponibles:\n")

    for index, cancion in enumerate(lista_canciones, start=1): # Se muestra la lista de canciones
        print(f"{index}.- {cancion}")

    opcion = input("\nEscribe el número de la canción a reproducir: ").strip()

    if (not opcion.isdigit() or int(opcion) < 1 or int(opcion) > len(lista_canciones)):
        print("\n>> Opción inválida")

        return
    
    cancion = lista_canciones[int(opcion) - 1] # Canción elegida
    
    print(f"\n>> Solicitando la canción '{cancion}'...")

    try: # Trata de obtener la ruta de la canción
        ruta_temporal = recibeCancion_gbn(sock, cancion)
    except Exception as e:
        print("\n>> Error al recibir la canción: ", e)

        return
    
    print("\n>> Reproducción iniciada")

    # Llama al reproductor
    reproductor(ruta_temporal, cancion)

if __name__ == "__main__":
    main()