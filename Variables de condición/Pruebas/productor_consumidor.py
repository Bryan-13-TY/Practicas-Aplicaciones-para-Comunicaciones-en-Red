import threading
import time
import random

buffer = []
MAX_SIZE = 5
cond = threading.Condition()

def productor():
    while True:
        with cond:
            while len(buffer) == MAX_SIZE:
                print("Buffer lleno, productor espera...")
                cond.wait()

            item = random.randint(1, 100)
            buffer.append(item)
            print(f"Producido: {item}")
            cond.notify() # Despierta al consumidor

        time.sleep(random.uniform(0.5, 1.5))


def consumidor():
    while True:
        with cond:
            while not buffer:
                print("Buffer vacío, consumidor espera...")
                cond.wait()

            item = buffer.pop(0)
            print(f"Consumido: {item}")
            cond.notify()

        time.sleep(random.uniform(0.5, 2))

# Crear e iniciar hilos
threading.Thread(target=productor, daemon=True).start()
threading.Thread(target=consumidor, daemon=True).start()

time.sleep(100) # Ejecuta por 10 segundos