import socket
import threading
import time
import os
from pathlib import Path

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5000
TAMANO_PAQUETE = 1024

cond = threading.Condition() # variable de condición
# monitos de acceso
estado = {"activo": True, "detener": False} # indica si se puede transmitir o si se debe detener

def hilo_de_transmision(nombre_archivo: str) -> None:
    """Envía el archivo por UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    archivo = os.path.basename(nombre_archivo)
    sock.sendto(archivo.encode(), (SERVER_IP, SERVER_PORT))

    # bucle de transmisión
    with open(nombre_archivo, "rb") as f: # se abre el archivo en modo binario
        while True:
            with cond: # bloque la condición
                while not estado["activo"] and not estado["detener"]: # no puede enviar datos
                    # el hilo se suspende
                    cond.wait()

                if estado["detener"]: # si la transmisión se detiene
                    print(">> Transmisión detenida por el usuario")
                    sock.sendto(b"__ABORT__", (SERVER_IP, SERVER_PORT))
                    sock.close()
                    return
            
            # lectura y envío de fragmentos
            data = f.read(TAMANO_PAQUETE)
            if not data: # si ya no hay más datos por enviar
                break

            sock.sendto(data, (SERVER_IP, SERVER_PORT))
            time.sleep(0.01)

    sock.sendto(b"__FIN__", (SERVER_IP, SERVER_PORT))
    sock.close()
    print(">> Transmisión finalizada correctamente")


def main():
    """Hilo principal para el menú."""
    nombre_archivo = input("Ingrese el archivo a enviar: ").strip()
    if not os.path.exists(nombre_archivo):
        print(">> El archivo no existe")
        return
    
    hilo = threading.Thread(target=hilo_de_transmision, args=(nombre_archivo,))
    hilo.start()
    
    print("""
Menú:

1.- Pausar transmisión
2.- Reanudar transmisión
3.- Detener transmisión 
""")
    
    while hilo.is_alive(): # mientras el hilo transmisor este activo
        opcion = input("Opción: ").strip()

        with cond: # cambios sincronizados
            if opcion == "1":
                estado["activo"] = False # no puede transmitir 
                print(">> Transmisión pausada.")
            elif opcion == "2":
                estado["activo"] = True # puede transmitir
                cond.notify_all() # despierta al hilo
                print(">> Transmisión reanudada.")
            elif opcion == "3":
                estado["detener"] = True # se detiene la transmisión
                cond.notify_all()
                print(">> Deteniendo transmisión...")
                break
            else:
                print(">> Opción no válida.")
    
    hilo.join() # espera a que el hilo termine
    print(">> Cliente finalizado")

if __name__ == "__main__":
    main()