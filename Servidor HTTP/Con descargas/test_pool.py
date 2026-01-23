import socket
import threading
import time

HOST = "127.0.0.1"
PORT_PRIMARIO = 8080
PORT_SECUNDARIO = 8081

TOTAL_CONEXIONES = 20 # más que POOL_MAX* 2 para forzar saturación
TIEMPO_VIVO = 10 # segundos que cada conexión permanece abierta

def cliente(id_cliente):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT_PRIMARIO))

        request = (
            "GET / HTTP/1.1\r\n"
            f"Host: {HOST}\r\n"
            "Connection: keep-alive\r\n\r\n"
        )
        sock.sendall(request.encode())

        respuesta = sock.recv(1024).decode(errors="ignore")
        primera_linea = respuesta.splitlines()[0] if respuesta else "SIN RESPUESTA"

        print(f"[CLIENTE {id_cliente}] {primera_linea}")

        time.sleep(TIEMPO_VIVO)
        sock.close()
    except Exception as e:
        print(f"[CLIENTE {id_cliente}] ERROR: {e}")


def main():
    hilos = []

    print("Iniciando prueba de pool de conexiones...\n")

    for i in range(TOTAL_CONEXIONES):
        t = threading.Thread(target=cliente, args=(i,))
        hilos.append(t)
        t.start()
        time.sleep(0.2) # escalamos ligeramente las conexiones

    for t in hilos:
        t.join()

    print("\nPrueba finalizada.")

if __name__ == "__main__":
    main()