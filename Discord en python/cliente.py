"""
Clase 'Cliente' que representa a un usuario en una sala.

Se cuentan con los métodos para enviar menasajes al servidor y para recibirlos
desde el servidor y también para buscar un sticker, y por último una función
para obtener las salas activas.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 09/11/2025
"""
import socket
import threading
import json
import sys
from pathlib import Path

from audio import Audio
from stickers import obtener_sticker
import utils

SERVER = ("127.0.0.1", 5007) # IP y puerto del servidor

class Cliente:
    def __init__(self, usuario: str, sala: str) -> None:
        """
        Constructor de la clase.

        Parameters
        ----------
        usuario : str
            Nombre de usuario del cliente.
        sala : str
            Nombre de la sala en la que se encuentra el cliente.
        """
        self.usuario = usuario
        self.sala = sala
        self.activo = True
        self.audio = Audio() # objeto de tipo audio

        # socket UDP para enviar y recibir mensajes
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0)) # puerto aleatorio para recibir mensajes

        self.carpeta_script = Path(__file__).parent
        self.carpeta_sala = self.carpeta_script / f"{self.sala}"
        self.carpeta_sala.mkdir(parents=True, exist_ok=True)
        self.carpeta_usuario = self.carpeta_sala / f"{self.usuario}"
        self.carpeta_usuario.mkdir(parents=True, exist_ok=True)

        # avisar al servidor que un usuario entro a la sala
        inicio = {"tipo": "inicio",
                  "user": self.usuario,
                  "sala": self.sala}
        self.sock.sendto(json.dumps(inicio).encode(), SERVER)

    def recibir_mensaje(self) -> None:
        """
        Recibe mensaje desde el servidor, tales como:

        - Audios (públicos o privados).
        - Stickers (públicos o privados).
        - Mensajes (públicos o privados).
        - Avisos del sistema. 
        """
        while self.activo:
            try:
                data, _ = self.sock.recvfrom(4096)
                mensaje = json.loads(data.decode())
                sala_mensaje = mensaje.get("sala", self.sala)
                tipo = mensaje.get("tipo")

                if sala_mensaje != self.sala:
                    continue

                if tipo == "msj":
                    if mensaje.get("privado"):
                        print(f"{utils.YELLOW}[Privado de {mensaje['from']}]{utils.RESET}: {mensaje['content']}")
                    else:
                        print(f"{utils.BLUE}[{mensaje['user']}]{utils.RESET}: {mensaje['content']}")

                if tipo == "aviso":
                    print(mensaje["content"])

                if tipo == "audio":
                    # servidor informa que alguien envío un audio (público o privado)
                    if mensaje.get("privado"):
                        print(f"{utils.YELLOW}[Privado de {mensaje['from']}]{utils.RESET}: {mensaje['content']}")
                    else:
                        print(f"{utils.BLUE}[{mensaje.get('from')}]{utils.RESET}: {mensaje['content']}")

                if tipo == "usuarios":
                    print(f"Usuarios en sala {utils.MAGENTA}'{self.sala}'{utils.RESET}: {utils.MAGENTA}{', '.join(mensaje['lista'])}{utils.RESET}")
            except:
                break

    def enviar_mensaje(self) -> None:
        """
        Envía mensajes al servidor, tales como:

        - Enviar audios (públicos o privados).
        - Enviar stickers (públicos o privados).
        - Enviar mensajes (públicos o privados).
        - Solicitud para la reproducción de audios. 
        """
        while self.activo:
            try:
                texto = input("").strip()

                if texto.lower() == "/salir":
                    salir = {"tipo": "salir",
                             "user": self.usuario,
                             "sala": self.sala}
                    self.sock.sendto(json.dumps(salir).encode(), SERVER)
                    self.activo = False
                    print(f">> {utils.RED}[system]{utils.RESET} Has salido de la sala")
                    self.sock.close()
                    break

                # =========================
                # Se envía un audio público
                # =========================
                elif texto.lower() == "/audio":
                    audio_meta = {"tipo": "audio",
                                  "privado": False,
                                  "user": self.usuario,
                                  "sala": self.sala}
                    # grabar y enviar directamente (no guarda copia local)
                    nombre_audio = self.audio.grabar_audio(audio_meta, self.sala, self.usuario)
                    # imprime confirmación local
                    print(f">> {utils.GREEN}[system]{utils.RESET} Has enviado el audio '{nombre_audio}'")
                
                # ===========================
                # Se envía un sticker píblico
                # ===========================
                elif texto.lower().startswith("/sticker"):
                    partes = texto.split(" ", 1)
                    if len(partes) < 2:
                        print(f">> {utils.RED}[system]{utils.RESET} Formato: /sticker nombre_sticker")
                        continue
                    _, nombre_sticker = partes
                    sticker = obtener_sticker(nombre_sticker)
                    if not sticker:
                        print(f">> {utils.RED}[system]{utils.RESET} El sticker no existe")
                        continue
                    mensaje = {"tipo": "msj",
                               "privado": False,
                               "user": self.usuario,
                               "sala": self.sala,
                               "content": sticker}
                    self.sock.sendto(json.dumps(mensaje).encode(), SERVER)
                
                # =============================
                # Se quiere reproducir un audio
                # =============================
                elif texto.lower().startswith("/reproducir"):
                    partes = texto.split(" ", 1)
                    if len(partes) < 2:
                        print(f">> {utils.RED}[system]{utils.RESET} Formato: /reproducir nombre_archivo")
                        continue
                    _, nombre_archivo = partes
                    ruta_audio = self.audio.buscar_audio(self.carpeta_sala, self.carpeta_usuario, self.usuario, nombre_archivo)
                    if ruta_audio:
                        self.audio.reproducir_audio(ruta_audio, nombre_archivo)
                    else:
                        print(f">> {utils.RED}[system]{utils.RESET} El audio no existe")

                # ===========================
                # Se envía un mensaje privado
                # ===========================
                elif texto.startswith("@"):
                    partes = texto.split(" ", 1)
                    if len(partes) < 2:
                        print(f">> {utils.RED}[system]{utils.RESET} Formato: @usuario mensaje")
                        continue

                    # ===========================
                    # Se envía un sticker privado
                    # ===========================
                    if partes[1].startswith("/sticker"):
                        partes2 = partes[1].split(" ")
                        if len(partes2) < 2:
                            print(f">> {utils.RED}[system]{utils.RESET} Formato: /sticker nombre_sticker")
                            continue
                        _, nombre_sticker = partes2
                        sticker = obtener_sticker(nombre_sticker)
                        if not sticker:
                            print(f">> {utils.RED}[system]{utils.RESET} El sticker no existe")
                            continue
                        destinatario, _ = partes
                        destinatario = destinatario[1:]
                        mensaje = {"tipo": "msj",
                                   "privado": True,
                                   "from": self.usuario,
                                   "to": destinatario,
                                   "content": sticker,
                                   "sala": self.sala}
                        self.sock.sendto(json.dumps(mensaje).encode(), SERVER) # FIXME: En ningún momento se válida que el destinatario existe en la sala
                        print(f"{utils.ORANGE}[Tú -> {destinatario}]{utils.RESET}: {sticker}")
                        continue

                    # =========================
                    # Se envía un audio privado
                    # =========================
                    elif partes[1] == "/audio":
                        destinatario, _ = partes
                        destinatario = destinatario[1:]
                        audio_meta = {"tipo": "audio",
                                      "privado": True,
                                      "from": self.usuario,
                                      "to": destinatario,
                                      "sala": self.sala}
                        nombre_audio = self.audio.grabar_audio(audio_meta, self.sala, self.usuario)
                        print(f"{utils.ORANGE}[Tú -> {destinatario}]{utils.RESET}: has enviado el audio '{nombre_audio}'")
                        continue

                    # ===========================
                    # Se envía un mensaje privado
                    # ===========================
                    else:
                        destinatario, contenido = partes
                        destinatario = destinatario[1:]
                        mensaje = {"tipo": "msj",
                                   "privado": True,
                                   "from": self.usuario,
                                   "to": destinatario,
                                   "content": contenido,
                                   "sala": self.sala}
                        self.sock.sendto(json.dumps(mensaje).encode(), SERVER)
                        print(f"{utils.ORANGE}[Tú -> {destinatario}]{utils.RESET}: {contenido}")
                        continue

                # ===========================
                # Se envía un mensaje público
                # ===========================
                else:
                    mensaje = {"tipo": "msj",
                               "privado": False,
                               "user": self.usuario,
                               "sala": self.sala,
                               "content": texto}
                    self.sock.sendto(json.dumps(mensaje).encode(), SERVER)
            except KeyboardInterrupt:
                salir = {"tipo": "salir",
                         "user": self.usuario,
                         "sala": self.sala}
                self.sock.sendto(json.dumps(salir).encode(), SERVER)
                self.activo = False
                self.sock.close()
                sys.exit(0)

    def iniciar(self) -> None:
        """Inicializa los hilos. Un hilo para recibir mensajes en segundo plano y uno principal para enviar."""
        threading.Thread(target=self.recibir_mensaje, daemon=True).start()
        self.enviar_mensaje()


def obtener_salas() -> list:
    """Muestra las salas disponibles para unirse."""
    # socket UDP para la solicitar las salas disponibles
    temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    temp_sock.bind(('', 0))
    peticion = {"tipo": "listar_salas"}
    temp_sock.sendto(json.dumps(peticion).encode(), SERVER)
    data, _ = temp_sock.recvfrom(4096)
    temp_sock.close()
    try:
        respuesta = json.loads(data.decode())
        return respuesta["lista"] if respuesta["tipo"] == "salas" else []
    except:
        return []
    

def main() -> None:
    print(f">> {utils.RED}[system]{utils.RESET} Obteniendo salas disponibles...\n")
    salas_disponibles = obtener_salas()
    if salas_disponibles:
        print("Salas disponibles:")
        for i, s in enumerate(salas_disponibles, 1):
            print(f"{i}. {s}")
    else:
        print(f">> {utils.RED}[system]{utils.RESET} No hay salas activas. Se creará una nueva sala al unirte")

    sala = input("\nEscribe el nombre de la sala a la que desesar unirte (o crea una nueva): ").strip()
    if not sala:
        sala = "general"

    usuario = input("Ingresa tu nombre de usuario: ")

    utils.limpiar_terminal()
    print(f"""
====================================
 BIENVENIDO A LA SALA '{sala}'
====================================
 USUARIO: {usuario}
====================================
""")
    cliente = Cliente(usuario, sala)
    cliente.iniciar()

if __name__ == "__main__":
    main()