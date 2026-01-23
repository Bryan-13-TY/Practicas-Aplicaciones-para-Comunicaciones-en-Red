import pygame, tkinter as tk, warnings
from tkinter import ttk

warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
pygame.mixer.init()

def reproductor(ruta_cancion: str, nombre_cancion: str) -> None:
    """
    Interfaz del reproductor mp3.

    Parameters
    ----------
    rutaCancion : str
        Ruta del archivo .mp3 a reproducir.
    nombreCancion : str
        Nombre de la canción elegida por el cliente.
    """
    def reproducir() -> None:
        """
        Reproduce el archivo .mp3.
        """
        pygame.mixer.music.play()
        label_state.config(text="🎶 Reproduciendo canción...")

    def pausar() -> None:
        """
        Pausa la reproducción del archivo .mp3.
        """
        pygame.mixer.music.pause()
        label_state.config(text="Canción en pausa")

    def continuar() -> None:
        """
        Continua la reproducción del archivo .mp3.
        """
        pygame.mixer.music.unpause()
        label_state.config(text="Continuando canción...")

    def detener() -> None:
        """
        Detiene la reproducción del archivo .mp3.
        """
        pygame.mixer.music.stop()
        label_state.config(text="Canción detenida")

    def ajustarVolumen(valor: int) -> None:
        """
        Ajusta el volumen de la canción.

        Parameters
        ----------
        valor : int
            Valor inicial del volumen de la canción.
        """
        volumen = float(valor)

        pygame.mixer.music.set_volume(volumen)
        label_volume.config(text=f"Volumen al {int(volumen * 100)}%")

    try:
        pygame.mixer.music.load(ruta_cancion)
        archivoCargado = True
    except Exception as e:
        archivoCargado = False
        print(f"Error al cargar el archivo: {e}")

    ventana = tk.Tk()
    ventana.title("Reproductor MP3")
    ventana.geometry("400x300")
    ventana.resizable(False, False)

    if (archivoCargado):
        label = tk.Label(ventana, text=f"Canción cargada:\n{nombre_cancion}", wraplength=380)
    else:
        label = tk.Label(ventana, text="No se pudo cargar la canción", fg="red")
    
    label.pack(pady=10)
    label_state = tk.Label(ventana, text="Reproductor inactivo", fg="gray")
    label_state.pack(pady=5)

    # Se crean los botones
    frame_btns = tk.Frame(ventana)
    frame_btns.pack(pady=15)

    btn_play = tk.Button(frame_btns, text="▶️ Reproducir", command=reproducir, state="normal" if archivoCargado else "disabled")
    btn_play.grid(row=0, column=0, padx=5)
    btn_pause = tk.Button(frame_btns, text="⏸️ Pausar", command=pausar, state="normal" if archivoCargado else "disabled")
    btn_pause.grid(row=0, column=1, padx=5)
    btn_continue = tk.Button(frame_btns, text="▶️ Continuar", command=continuar, state="normal" if archivoCargado else "disabled")
    btn_continue.grid(row=0, column=2, padx=5)
    btn_stop = tk.Button(frame_btns, text="⏹️ Detener", command=detener, state="normal" if archivoCargado else "disabled")
    btn_stop.grid(row=0, column=3, padx=5)

    label_volume = tk.Label(ventana, text="Volumen al 50%")
    label_volume.pack(pady=5)

    controlVolumen = ttk.Scale(ventana, from_=0, to=1, orient="horizontal", value=0.5, command=ajustarVolumen, length=250)
    controlVolumen.pack()
    pygame.mixer.music.set_volume(0.5)

    # Ejecutamos la ventana del reproductor
    ventana.mainloop()