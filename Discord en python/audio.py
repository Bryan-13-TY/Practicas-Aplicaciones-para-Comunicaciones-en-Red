"""
Módulo 'audio.py': Para manejar todo lo relacionado al envío y reproducción
de los audios grabados por el usuario.

Se cuentan con los métodos para enviar el audio por Go-Back_n, grabarlo,
buscarlo y reproducirlo.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 09/11/2025
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from pathlib import Path
import socket
import struct
import json

import pygame
import sounddevice as sd

import utils

pygame.mixer.init()

# constantes para transferencia de audio
ENCABEZADO_FORMAT = "!I"
ENCABEZADO_SIZE = 4
MAX_BYTES_PAQUETE = 1024 # incluye encabezado

def enviar_audio_gbn(server_addr_main: tuple, metadata: dict, audio_bytes: bytes, window_size=6, timeout=3.0) -> str | None:
    """
    Envía el audio por fragmentos a un puerto de audio del servidor.

    Parameters
    ----------
    server_addr_main : tuple
        (ip, puerto) del servidor principal, donde se envía el AUDIOINFO.
    metadata : dict
        diccionario con metadatos (incluye 'nombre', 'frecuencia', 'canales', 'privado', 'to', 'user', 'sala', etc.).
    audio_bytes : bytes
        bytes del audio (int16).
    window_size : int
        Número de paquetes que se pueden enviar al mismo tiempo.
    timeout : float
        Tiempo máximo de espera para recibir mensajes del servidor.

    Returns
    -------
    str | None
        Nombre asignado al audio al terminar el envío, None si falla el envío.
    """
    tamano_archivo = len(audio_bytes)
    total_paquetes = (tamano_archivo + (MAX_BYTES_PAQUETE - ENCABEZADO_SIZE) - 1) // (MAX_BYTES_PAQUETE - ENCABEZADO_SIZE)

    # enviar metadatos al socket principal (AUDIOINFO)
    metadata_enviar = dict(metadata) # copia de los metadatos
    metadata_enviar.update({"tipo": "AUDIOINFO",
                            "tamano": tamano_archivo,
                            "total_paquetes": total_paquetes})
    
    # socket UDP temporal para el envío de los metadatos del audio
    temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    temp_sock.bind(('', 0))
    temp_sock.sendto(json.dumps(metadata_enviar).encode(), server_addr_main) # enviar AUDIOINFO al servidor principal

    # esperar READY con puerto de audio
    temp_sock.settimeout(3.0)
    try:
        data, _ = temp_sock.recvfrom(4096)
    except socket.timeout:
        print("No se recibió READY del servidor (timeout).")
        temp_sock.close()
        return None

    try:
        respuesta = json.loads(data.decode())
    except:
        print("Respuesta inválida del servidor al solicitar transferencia de audio.")
        temp_sock.close()
        return None

    if respuesta.get("tipo") != "READY" or "port" not in respuesta:
        print("Servidor no listo para transferencia.")
        temp_sock.close()
        return None
    
    audio_port = int(respuesta["port"])
    server_ip = server_addr_main[0]
    server_audio_addr = (server_ip, audio_port) # dirección IP y puerto a donde se enviará el audio

    # socket UDP para enviar los paquetes directamente al puerto de audio
    sock_audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_audio.bind(('', 0))
    sock_audio.settimeout(timeout)

    print(f">> Enviando audio a {server_audio_addr} — {tamano_archivo} bytes, {total_paquetes} paquetes")

    base = 0
    next_seq = 0
    payload_size = MAX_BYTES_PAQUETE - ENCABEZADO_SIZE

    while base < total_paquetes:
       # enviar paquetes en ventana
        while next_seq < base + window_size and next_seq < total_paquetes:
            inicio = next_seq * payload_size
            fin = inicio + payload_size
            chunk = audio_bytes[inicio:fin]
            encabezado = struct.pack(ENCABEZADO_FORMAT, next_seq)
            paquete = encabezado + chunk
            sock_audio.sendto(paquete, server_audio_addr)
            #print(f">> Enviado paquete {next_seq}") # opcional
            next_seq += 1 

        # esperar ACK (confirmación del servidor)
        try:
            data, _ = sock_audio.recvfrom(4096)
            msj = json.loads(data.decode())
            if msj.get("tipo") == "ACK":
                ack_seq = int(msj["num_seq"])
                if ack_seq >= base:
                    base = ack_seq + 1 # desplazar ventana
        except socket.timeout:
            next_seq = base # reenviar desde base
            print(f">> Timeout — reintentando desde paquete {base}")

    # enviar FIN (no hay más paquetes por enviar)
    sock_audio.sendto(b"FIN", server_audio_addr)
    sock_audio.close()
    temp_sock.close()

    return metadata.get("nombre") # nombre asignado al audio


class Audio:
    def grabar_audio(self, mensaje: dict, sala: str, usuario: str) -> str | None:
        """
        Graba un audio y lo envía directamente al servidor por fragmentos.

        Parameters
        ----------
        mensaje : dict
            Diccionario con los metadatos para la grabación.
        sala : str
            Nombre de la sala desde donde se graba el audio.
        usuario: str
            Nombre del usuario que graba el audio.

        Returns
        -------
        str | None
            Nombre asignado al audio al terminar el envío, None si falla el envío.
        """
        fecha = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nombre_audio = f"{usuario}_{fecha}.wav"

        # metadatos
        privado = bool(mensaje.get("privado", False))
        dest = mensaje.get("to")
        grab_name = nombre_audio

        duracion = 5
        frecuencia = 44100
        canales = 2

        print(f">> {utils.RED}[system]{utils.RESET} Grabando audio...")
        audio = sd.rec(int(duracion * frecuencia), samplerate=frecuencia, channels=canales, dtype="int16") # grabar en int16 directamente
        sd.wait()
        print(f">> {utils.RED}[system]{utils.RESET} Grabación completa")

        # convertir a bytes (int16)
        try:
            audio_bytes = audio.tobytes()
        except Exception:
            # si por alguna razón no es ndarray estándar, convertir manualmente
            import numpy as np
            audio_bytes = np.asarray(audio, dtype="int16").tobytes()

        metadata = {"user": usuario,
                    "from": usuario,
                    "to": dest,
                    "sala": sala,
                    "privado": privado,
                    "nombre": grab_name,
                    "frecuencia": frecuencia,
                    "canales": canales}
        
        # enviar al servidor principal (la dirección IP y el puerto ya se conocen)
        SERVER = ("127.0.0.1", 5007)
        enviar_nombre = enviar_audio_gbn(SERVER, metadata, audio_bytes, window_size=6, timeout=3.0)

        return enviar_nombre
    
    def buscar_audio(self, carpeta_sala: Path, carpeta_personal: Path, usuario: str, nombre_audio: str) -> Path | None:
        """
        Busca el audio que se quiere reproducir.

        Parameters
        ----------
        carpeta_sala : Path
            Ruta hacia la carpeta de la sala donde se buscará el audio.
        carpeta_personal : Path
            Ruta hacia la carpeta del usuario donde se buscará el audio.
        usuario : str
            Nombre del usuario que quiere reproducir el audio.
        nombre_audio : str
            Nombre del audio que se quiere buscar.

        Returns
        -------
        Path | None
            Ruta hacia del audio si este existe, de lo contrario None.
        """
        ruta_directa = carpeta_sala / nombre_audio
        if ruta_directa.exists(): # si es un audio público
            return ruta_directa

        for archivo in carpeta_sala.rglob("*"): # si es un audio privado enviado
            if archivo.is_file:
                nombre = archivo.name
                if nombre.startswith(usuario) and nombre.endswith(nombre_audio):
                    return archivo

        ruta_personal = carpeta_personal / nombre_audio
        if ruta_personal.exists(): # si es un audio privado enviado
            return ruta_personal

        return None
    
    def reproducir_audio(self, ruta_audio: Path, nombre_audio: str) -> None:
        """
        Controla la reproducción del audio.

        Parameters
        ----------
        ruta_audio : Path
            Ruta del audio a reproducir.
        nombre_audio : str
            Nombre del audio que se quiere reproducir.
        """
        def reproducir() -> None:
            """Comienza la reproducción del audio al presionar el botón 'Reproducir'."""
            pygame.mixer.music.play()
            label_state.config(text="Reproduciendo audio...")

        def pausar() -> None:
            """Pausa la reproducción del audio al presionar el botón 'Pausar'."""
            pygame.mixer.music.pause()
            label_state.config(text="Audio en pausa")

        def continuar() -> None:
            """Continua la reproducción del audio al presionar el botón 'Coninuar'."""
            pygame.mixer.music.unpause()
            label_state.config(text="Continuando audio...")

        def detener() -> None:
            """Detiene la reproducción del audio al presionar el botón 'Detener'."""
            pygame.mixer.music.stop()
            label_state.config(text="Audio detenido")

        def ajustar_volumen(valor: int) -> None:
            """
            Ajusta el volumen del audio.

            Parameters
            ----------
            valor : int
                Volumen inicial del audio.
            """
            volumen = float(valor)
            pygame.mixer.music.set_volume(volumen)
            label_volume.config(text=f"Volumen al {int(volumen * 100)}%")

        try:
            pygame.mixer.music.load(ruta_audio)
            archivo_cargado = True
        except Exception as e:
            archivo_cargado = False
            print(f"Error al cargar el archivo: {e}")

        # se crea la ventana del reproductor
        root = tk.Tk()
        root.title("Reproductor")
        root.geometry("400x300")
        root.resizable(False, False)

        if archivo_cargado:
            label = tk.Label(root, text=f"Audio cargado: \n{nombre_audio}", wraplength=380)
        else:
            label = tk.Label(root, text="No se pudo cargar el audio", fg="red")

        label.pack(pady=10)
        label_state = tk.Label(root, text="Reproductor inactivo", fg="gray")
        label_state.pack(pady=5)

        # se crean los botones de reproducción
        frame_btns = tk.Frame(root)
        frame_btns.pack(pady=15)

        btn_play = tk.Button(frame_btns, text="▶️ Reproducir", command=reproducir, state="normal" if archivo_cargado else "disabled")
        btn_play.grid(row=0, column=0, padx=5)
        btn_pause = tk.Button(frame_btns, text="⏸️ Pausar", command=pausar, state="normal" if archivo_cargado else "disabled")
        btn_pause.grid(row=0, column=1, padx=5)
        btn_continue = tk.Button(frame_btns, text="▶️ Continuar", command=continuar, state="normal" if archivo_cargado else "disabled")
        btn_continue.grid(row=0, column=2, padx=5)
        btn_stop = tk.Button(frame_btns, text="⏹️ Detener", command=detener, state="normal" if archivo_cargado else "disabled")
        btn_stop.grid(row=0, column=3, padx=5)

        # se crea el label para el volumen del audio
        label_volume = tk.Label(root, text="Volumen al 50%")
        label_volume.pack(pady=5)

        control_volume = ttk.Scale(root, from_=0, to=1, orient="horizontal", value=0.5, command=ajustar_volumen, length=250)  # type: ignore
        control_volume.pack()
        pygame.mixer.music.set_volume(0.5)

        root.mainloop()