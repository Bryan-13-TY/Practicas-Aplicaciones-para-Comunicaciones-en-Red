"""
Servidor del chat.

Se cuentan con las funciones para enviar mensajes a usuarios especificos
en cualquier sala, para enviar mensajes a todos los usuarios en una sala,
para manejar los tipos de mensajes que se envían desde los usuarios y a los
usuarios y para recibir el audio enviado por fragmentos.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigos

Fecha: 09/11/2025
"""
import socket
import json
import threading
import struct
import time
from pathlib import Path

import wave

import utils

SERVER_ADDR = ("0.0.0.0", 5007) # el servidor escucha en todas las interfaces en el puerto 5007
usuarios = {"general": {}} # lista de usuarios por sala: {"general": {"usuario": (ip, puerto)}}

# socket UDP principal del servidor (para mensajes JSON tipo msj, inicio, listar_salas, etc.)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(SERVER_ADDR)

print("Servidor de chat activo...")

# constantes para transferencia de audio
ENCABEZADO_FORMAT = "!I"
ENCABEZADO_SIZE = 4
MAX_BYTES_PAQUETE = 1024 # incluye encabezado

def enviar_unicast(data: dict, addr: tuple) -> None:
    """
    Envía un mensaje a un cliente específico.

    Parameters
    ----------
    data : dict
        Metadatos a enviar al usuario.
    addr : tuple
        (direccion_IP, puerto)

        - **direccion_IP** (str): Dirección IP del usuario.
        - **puerto** (int): Puerto del usuario.
    """
    sock.sendto(json.dumps(data).encode(), addr)


def enviar_publico(data: dict, sala: str) -> None:
    """
    Envía un mensaje a cada uno de los usuarios de la sala.

    Parameters
    ----------
    data : dict
        Metadatos a enviar a cada usuario.
    sala : str
        Sala a la que se envían los metadatos.
    """
    for usuario_addr in usuarios[sala].values():
        enviar_unicast(data, usuario_addr)


def recibir_audio_gbn(audio_sock: socket.socket, cliente_addr: tuple[str, int], info: dict) -> None:
    """
    Recibe por UDP un audio enviado por fragmentos (Go-Back-N simplificado).

    Parameters
    ----------
    audio_sock : socket.socket
        Socket UDP ligado al puerto asignado para esta transferencia.
    cliente_addr : tuple
        (direccion_IP, puerto)

        - **direccion_IP** (str): Dirección IP del cliente.
        - **puerto** (int): Puerto de origen del cliente.
    info: dict
        Metadatos enviados por el cliente (incluye nombre, sala, user, privado,
        to, frecuencia, canales, tamano, total_paquetes).
    """
    # se extrae información de los metadatos enviados por el cliente
    nombre = info.get("nombre", f"{info.get('user','anon')}_{int(time.time())}.wav") # nombre del usuario que envía el audio
    tamano = int(info.get("tamano", 0))
    total_paquetes = int(info.get("total_paquetes", 0))
    frecuencia = int(info.get("frecuencia", 44100))
    canales = int(info.get("canales", 2))
    sala = info.get("sala", "general") # sala desde donde se envía el audio
    privado = bool(info.get("privado", False))
    usuario = info.get("user") or info.get("from") or "anon"
    destinatario = info.get("to") # usuario que recibe el audio

    print(f">> Iniciando recepción de audio '{nombre}' desde {cliente_addr} (sala='{sala}', user='{usuario}', privado={privado}, paquetes={total_paquetes})")
    paquetes = {}
    num_seq_esperado = 0
    audio_sock.settimeout(3.0)

    while True:
        try:
            paquete, addr = audio_sock.recvfrom(4096)
        except socket.timeout:
            # si aún no llega nada, seguir esperando
            continue

        # aceptar la primera dirección válida como fuente de paquetes
        if 'addr_audio' not in locals():
            addr_audio = addr # guardar la dirección real de envío del cliente

        # ignorar solo si viene de otro cliente distinto
        if addr != addr_audio:
            continue

        # se termino la transferencia de los fragmentos
        if paquete == b"FIN":
            print("FIN recibido para transferencia de audio.")
            audio_sock.settimeout(None)
            break

        if len(paquete) < ENCABEZADO_SIZE:
            continue

        num_seq = struct.unpack(ENCABEZADO_FORMAT, paquete[:ENCABEZADO_SIZE])[0]
        datos = paquete[ENCABEZADO_SIZE:]

        if num_seq == num_seq_esperado:
            paquetes[num_seq] = datos
            num_seq_esperado += 1

            ack = {"tipo": "ACK",
                   "num_seq": num_seq}
            audio_sock.sendto(json.dumps(ack).encode(), addr_audio)
            print(f">> Recibido paquete {num_seq}, enviado ACK{num_seq}")
        else:
            # reenviar último ACK válido (num_seq_esperado - 1)
            ack_num = max(0, num_seq_esperado - 1)
            ack = {"tipo": "ACK",
                   "num_seq": ack_num}
            audio_sock.sendto(json.dumps(ack).encode(), addr_audio)
            print(f">> Paquete fuera de orden {num_seq}, reenvío ACK{ack_num}")

    # reconstruir bytes del audio
    audio_bytes = bytearray()
    for i in range(num_seq_esperado):
        audio_bytes.extend(paquetes.get(i, b""))

    audio_bytes = bytes(audio_bytes[:tamano])

    # guardar archivo .wav en la carpeta correspondiente
    carpeta = Path(__file__).parent
    carpeta_sala = carpeta / f"{sala}"
    carpeta_sala.mkdir(parents=True, exist_ok=True)

    if privado and destinatario: # si es un audio privado
        # TODO: si el destinatario se sabe que no existe, de todas formas se crea la carpeta con su nombre.
        # TODO: hacer la validación del destinatario no soluciona el problema del todo, ya que el cliente se cierra al no existir la carpeta
        carpeta_dest = carpeta_sala / f"{destinatario}"
        carpeta_dest.mkdir(parents=True, exist_ok=True)
        ruta_archivo = carpeta_dest / nombre
    else:
        ruta_archivo = carpeta_sala / nombre

    try:
        with wave.open(str(ruta_archivo), "wb") as wf:
            wf.setnchannels(canales)
            wf.setsampwidth(2) # estamos recibiendo int16 (2 bytes)
            wf.setframerate(frecuencia)
            wf.writeframes(audio_bytes)
        print(f"💾 Audio guardado en: {ruta_archivo}")
    except Exception as e:
        print(f"Error al guardar audio: {e}")
        return
    
    # avisar a destinatarios (usando el socket principal) el aviso del envío de un audio
    aviso = {"tipo": "audio",
             "sala": sala,
             "from": usuario,
             "nombre": nombre,
             "privado": privado,
             "content": f"{utils.GREEN}[🎙️][{usuario}]{utils.RESET} ha enviado el audio '{nombre}'"}
    
    if privado and destinatario:
        if destinatario in usuarios.get(sala, {}):
            enviar_unicast(aviso, usuarios[sala][destinatario])
        else: # TODO: Si se sabe que el destinatario no existe, envía el mensaje, pero de todas formas se guarda el audio
            # si destinatario no está, enviar notificación al emisor
            error = {"tipo": "aviso",
                     "sala": sala,
                     "content": f">> {utils.RED}[system]{utils.RESET} Usuario '{destinatario}' no está conectado"}
            enviar_unicast(error, usuarios[sala].get(usuario, cliente_addr))
    else:
        enviar_publico(aviso, sala)

    # cerrar el socket de audio
    try:
        audio_sock.close()
    except:
        pass


def manejar_cliente() -> None:
    """
    Bucle principal del servidor para recibir mensajes del cliente
    y enviar mensajes al servidor, tales como:
    
    - Audios (públicos o privados).
    - Stickers (públicos o privados).
    - Mensajes (públicos o privados).
    - Solicitud de reproducción de audios. 
    - Listar salas disponibles.
    - Entradas y salidas de usuarios.
    """
    while True:
        data, addr = sock.recvfrom(4096) # recibe datagramas de cualquier cliente.
        try:
            mensaje = json.loads(data.decode())
        except:
            # se ignora si la decodificación falla
            continue

        tipo = mensaje.get("tipo")
        usuario = mensaje.get("user") or mensaje.get("from")
        sala = mensaje.get("sala", "general")

        # =========================================
        # Se solicita la lista de salas disponibles
        # =========================================
        if tipo == "listar_salas":
            salas = list(usuarios.keys())
            respuesta = {"tipo": "salas",
                         "lista": salas}
            enviar_unicast(respuesta, addr)
            continue

        # ============================
        # Se crea la sala si no existe
        # ============================
        if sala not in usuarios:
            usuarios[sala] = {}

        # =======================
        # Usuario entra a la sala
        # =======================
        if tipo == "inicio":
            if usuario not in usuarios[sala]: # si el usuario no esta en la sala anteriormente
                usuarios[sala][usuario] = addr
                aviso = {"tipo": "aviso",
                         "sala": sala,
                         "content": f">> {utils.GREEN}[+]{utils.RESET}{utils.BLUE}[{usuario}]{utils.RESET} se ha unido a la sala"}
                enviar_publico(aviso, sala)

            # se actualiza la lista de usuarios conectados en la sala
            usuarios_sala = {"tipo": "usuarios",
                             "sala": sala,
                             "lista": list(usuarios[sala].keys())}
            enviar_publico(usuarios_sala, sala)

        # =======
        # Mensaje
        # =======
        elif tipo == "msj":
            # ===============
            # Mensaje público
            # ===============
            if not mensaje.get("privado", False):
                enviar_publico(mensaje, sala)
            # ===============
            # Mensaje privado
            # ===============
            elif mensaje.get("privado", False):
                dest = mensaje.get("to") # se extrae al destinatario del mensaje
                if dest in usuarios[sala]: # si el destinatario esta en la sala
                    enviar_unicast(mensaje, usuarios[sala][dest])
                else: # si el destinatario no esta en la sala
                    error = {"tipo": "aviso",
                             "sala": sala,
                             "content": f">> {utils.RED}[system]{utils.RESET} Usuario '{dest}' no está conectado"}
                    enviar_unicast(error, addr)

        # ========================
        # Usuario abandona la sala
        # ========================
        elif tipo == "salir":
            if usuario in usuarios[sala]: # si el usuario esta actualmente en la sala
                usuarios[sala].pop(usuario) # se elimina el usuario de la sala
                aviso = {"tipo": "aviso",
                         "sala": sala,
                         "content": f">> {utils.RED}[-]{utils.RESET}{utils.BLUE}[{usuario}]{utils.RESET} ha abandonado la sala"}
                enviar_publico(aviso, sala)

            # se actualiza la lista de usuarios conectados en la sala
            usuarios_sala = {"tipo": "usuarios",
                             "sala": sala,
                             "lista": list(usuarios[sala].keys())}
            enviar_publico(usuarios_sala, sala)

        # ===============================================================
        # AUDIOINFO: un cliente quiere iniciar una transferencia de audio
        # ===============================================================
        elif tipo == "AUDIOINFO" or tipo == "audio":
            # Para evitar congestionar el socket principal con paquetes binarios,
            # se crea nuevo socket UDP ligado a un puerto efímero y le decimos al cliente
            # que envíe los fragmentos a ese puerto.
            try:
                audio_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                audio_sock.bind(("0.0.0.0", 0)) # puerto efímero asignado por SO
                audio_port = audio_sock.getsockname()[1]

                # enviar READY indicando el puerto donde recibir la transferencia
                respuesta = {"tipo": "READY",
                             "port": audio_port}
                enviar_unicast(respuesta, addr)

                # arrancar hilo que recibirá la transferencia en segundo plano
                threading.Thread(target=recibir_audio_gbn, args=(audio_sock, addr, mensaje), daemon=True).start()
            except Exception as e:
                print(f"Error iniciando transferencia de audio: {e}")
                error = {"tipo": "aviso",
                         "sala": sala,
                         "content": f">> {utils.RED}[system]{utils.RESET} No se pudo iniciar transferencia de audio."}
                enviar_unicast(error, addr) 


def main() -> None:
    threading.Thread(target=manejar_cliente, daemon=True).start() # hilo principal del servidor

    while True: # mantener el servidor activo
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nServidor detenido.")
            break

if __name__ == "__main__":
    main()