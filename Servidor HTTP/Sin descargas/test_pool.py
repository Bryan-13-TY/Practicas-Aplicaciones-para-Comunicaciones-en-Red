import threading
import requests

def hacer_peticion():
    try:
        r = requests.get("http://127.0.0.1:8080/prueba.txt")
        print(r.status_code)
    except Exception as e:
        print("Error:", e)

hilos = []

for _ in range(30):
    t = threading.Thread(target=hacer_peticion)
    t.start()
    hilos.append(t)

for t in hilos:
    t.join()