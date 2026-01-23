import socket, struct
from  pathlib import Path

SERVER_ADDR = ("0.0.0.0", 5000) # IP y puerto donde escucha el servidor ('0.0.0.0' -> Todas las interfaces)
MAX_BYTES_PAQUETE = 1024 # Tamaño máximo en bytes del contenido útil dentro de cada paquete
ENCABEZADO_FORMAT = "!I" # Se usa para convertir del número de secuencia a 'bytes'
ENCABEZADO_SIZE = 4 # Tamaño en bytes del encabezado

def listarCanciones() -> list[str]:
    """
    Obtiene los nombres de las canciones en la carpeta 'pistas' y los guarda en una lista.
    
    Es la respuesta a la petición 'LIST' del cliente.

    Returns
    -------
    list[str]
        Lista de los nombres de las canciones en la carpeta 'pistas'.
    """
    pistas = Path(__file__).parent/"pistas" # Construir la ruta a la carpetas de las canciones

    if (not pistas.exists()):
        return [] # Devuelve una lista vacía si no hay canciones
    
    canciones = [f.name for f in pistas.glob("*.mp3")] # Guarda los nombres de las canciones en una lista

    return canciones # Devuelve solo nos nombres de las canciones

def enviarCancion_gbn(sock: socket.socket, cliente_addr: tuple, filepath: Path, window_size=6) -> None:
    """
    Envía el archivo .mp3 usando Go-Back-N.

    Formato del paquete: [4 bytes seq][payload bytes]
    ACK: b"ACK" + bytes seq.

    Parameters
    ----------
    sock : socket.soscket
        Socket UDP ya creado y enlazado.
    clienteAddr : tuple
        Tupla (ip, puerto) del cliente destino.
    filepath : Path
        Path del archivo .mp3 a enviar.
    window_size : int
        Número máximo de paquetes "en vuelo" (tamaño de la ventana GBN).
    """

    tamano_archivo = filepath.stat().st_size # Se calcula el tamaño del archivo .mp3
    total_paquetes = (tamano_archivo + MAX_BYTES_PAQUETE - 1) // MAX_BYTES_PAQUETE # Se calcula el total de paquetes necesarios para enviar la canción

    # Se lee la canción en memoria
    with open(filepath, "rb") as file:
        bytes_archivo = file.read() # Bytes del archivo .mp3

    print(f"\n>> Se envía al cliente: '{filepath.name}' ({tamano_archivo} bytes) en {total_paquetes} paquetes a {cliente_addr}")

    first_num_seq_ACKed = 0 # Número de secuencia del primer paquete no confirmado (ACKed)
    sgt_num_seq = 0 # Número de secuencia del siguiente paquete a enviar (0, 1, 2, 3, ...)

    sock.settimeout(360) # Tiempo límite para recibir ACKs (al expirar el servidor retransmite)

    # Enviar nombre, tamaño y número total de paquetes del archivo (informativo)
    meta_datos = f"FILEINFO|{filepath.name}|{tamano_archivo}|{total_paquetes}"
    sock.sendto(meta_datos.encode(), cliente_addr) # Se envían los meta datos al cliente

    # Bucle principal para el envió de la canción (Algoritmo Go-Back-N)
    while (first_num_seq_ACKed < total_paquetes):
        # Enviar paquetes dentro de la ventana
        while ((sgt_num_seq < first_num_seq_ACKed + window_size) and (sgt_num_seq < total_paquetes)): # Envía tantos paquetes como permita la ventana
            # Para cada número de secuencia siguiente se calcula los siguiente
            inicio = sgt_num_seq * MAX_BYTES_PAQUETE # Índice inicial (desde donde se deben de tomar los bytes para el siguiente paquete)
            final = inicio + MAX_BYTES_PAQUETE # Índice final (final de los bytes que se tomaron) (no se incluye en el paquete)
            bytes_paquete = bytes_archivo[inicio:final] # Extrae del archivo el fragmento de datos (bytes) que se enviará en este paquete
            
            # struct.pack("!I", sgt_num_seq) convierte el entero sgt_num_seq en 4 bytes binarios en formato de red (big endian)
            # Ejemplo: struct.pack("!I", 1) → b'\x00\x00\x00\x01'
            encabezado = struct.pack(ENCABEZADO_FORMAT, sgt_num_seq) # Crea el encabezado binario del paquete, que contiene el número de secuencia
            
            # Ejemplo: [ 4 bytes de encabezado (número de secuencia) ] + [ datos del archivo ]
            paquete = encabezado + bytes_paquete # Combina el encabezado y los datos del archivo en un solo bloque de bytes (paquete completo a enviar)
            
            sock.sendto(paquete, cliente_addr) # Se envía el paquete formado al cliente
            print(f">> Se envía el paquete: {sgt_num_seq}")

            sgt_num_seq += 1 # Siguiente paquete a enviar

        # Esperamos la confirmación del paquete enviado (ACK)
        try:
            data, addr = sock.recvfrom(4096) # Se recibe la solicitud del cliente

            if (addr != cliente_addr): # Si la dirección del mensaje es diferente a la del cliente
                continue # Se ignora al cliente (evitar mezclar clientes)

            if (data.startswith(b"ACK")): # Si se recibe la confirmación
                ACK_seq = struct.unpack(ENCABEZADO_FORMAT, data[3:3 + ENCABEZADO_SIZE])[0] # Se extraen los 4 bytes siguientes como número de secuencia

                if (ACK_seq >= first_num_seq_ACKed): # Si el paquete enviado fue confirmado
                    first_num_seq_ACKed = ACK_seq + 1 # Se actualiza el número de secuencia del primer paquete no confirmado

                    print(f">> Se confirma paquete [{ACK_seq}] -> últmo paquete sin confirmar [{first_num_seq_ACKed}]")
            elif (data.startswith(b"STOP")): # Si el solicita detener la transferencia
                print(">> El cliente solicitó detener la transferencia")

                return # Se detiene la transferencia del paquete
        except socket.timeout: # Si el tiempo de espera para recibir ACKs se excede
            # Se considera que el paquete se perdio (no se recibe ACK), se reenvian los paquetes desde el último no confirmado
            print(f">> Perdida del paquete: Se reenvia desde el paquete [{first_num_seq_ACKed}]")

            sgt_num_seq = first_num_seq_ACKed # Retroceder paquete
            
            continue # Reintenta 

    print("\n>> Transferencia de la canción completa")

    # Todos los paquetes se enviaron correctamente
    sock.sendto(b"FIN", cliente_addr) # Se envia la confirmación del termino de la transferencia de la canción

def main() -> None:
    # Se crea y se bindea un socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(SERVER_ADDR)

    print(f">> Servidor Go-Back-N escuchando en {SERVER_ADDR}")

    while (True):
        data, addr = sock.recvfrom(4096)
        mensaje = data.decode(errors="ignore")

        if (mensaje == "LIST"): # Cliente solicita la lista de canciones
            lista_canciones = listarCanciones()
            bytes_paquete = "::".join(lista_canciones)

            sock.sendto(bytes_paquete.encode(), addr) # Se envía la lista de canciones

            print(f">> Lista enviada a {addr} ({len(lista_canciones)} canciones en total)")
        elif (mensaje.startswith("GET:")): # Cliente solicita la canción
            nombre_cancion = mensaje.split(":", 1)[1] # Se obtiene el nombre de la canción solicitada
            ruta_cancion = Path(__file__).parent/"pistas"/nombre_cancion # Se obtiene la ruta de la canción

            if (not ruta_cancion.exists()): # Si la canción no existe
                sock.sendto(b"ERROR|NOFILE", addr)

                print(f"Cliente pidió '{nombre_cancion}' pero no existe")

                continue

            # Enviar el archivo con la canción
            enviarCancion_gbn(sock, addr, ruta_cancion, window_size=6)        
        else:
            # Mensaje desconocido
            sock.sendto(b"ERROR|UNKNOWN", addr)

if __name__ == "__main__":
    main()