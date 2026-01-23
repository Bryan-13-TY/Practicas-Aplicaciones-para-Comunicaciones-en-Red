import threading
import time

cond = threading.Condition()
ready = False

def worker() -> None:
    global ready
    with cond: # Bloquea el lock interno de la condición
        print("Hilo esperando...")
        while not ready:
            cond.wait() # Espera hasta que otro hilo llame a notify
        
        print("¡Hilo esperando y continuando!")

def notifier() -> None:
    global ready
    time.sleep(20)
    with cond:
        ready = True
        print("Notificador: enviando señal...")
        cond.notify() # Despierta un hilo que esté esperando

def main() -> None:
    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=notifier)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

if __name__ == "__main__":
    main()