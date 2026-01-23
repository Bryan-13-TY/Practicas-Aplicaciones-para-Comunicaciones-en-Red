"""
Funciones para el cliente de la tienda en línea.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 28/09/2025

Descripción:
    Este archivo contiene todas las funciones que usa el cliente de la tienda en línea.
"""

import os, msvcrt

def listarTipo(articulos: dict, tipoArticulo: str) -> None:
    """
    Imprime todos los artículos del mismo tipo.

    Esta función recorre el diccionario con los artículos e imprime todos aquellos
    con el tipo "tipoArticulo" en un formato más legible.

    Parameters
    ----------
    articulos : dict
        Diccionario con los artículos.
    tipoArticulo: str
        Uno de los tipos de los artículos: "Abarrotes", "Bebidas", "Snacks", "Cuidado personal" y "Limpieza".
    """
    for item in articulos["articulos"]:
        if (item['tipo'] == tipoArticulo): # Si coincide con el tipo del artículo
            print(f"\nId: {item['id']}")
            print(f"Nombre: {item['nombre']}")
            print(f"Precio: ${item['precio']} MXN")
            print(f"Marca: {item['marca']}")
            print(f"Stock: {item['stock']} artículos disponibles")

def listarArticulos(articulos: dict) -> None:
    """
    Imprime todos los artículos de todos los tipos en formato más legible.

    Parameters
    ----------
    articulos: dict
        Diccionario con los artículos.
    """
    print("Lista de artículos de la tienda:\n")

    print("__Artículos de tipo Abarrotes__")
    listarTipo(articulos, "Abarrotes")
    print("\n__Artículos de tipo Bebidas__")
    listarTipo(articulos, "Bebidas")
    print("\n__Artículos de tipo Snacks__")
    listarTipo(articulos, "Snacks")
    print("\n__Artículos de tipo Cuidado personal__")
    listarTipo(articulos, "Cuidado personal")
    print("\n__Artículos de tipo Limpieza__")
    listarTipo(articulos, "Limpieza")

def limpiarTerminal() -> None:
    """
    Limpia la terminal de cualquier sistema operativo. 
    """
    os.system('cls' if os .name == 'nt' else 'clear')

def mostrarBusqueda(busqueda: dict) -> None:
    """
    Imprime los artículos resultantes después de la búsqueda por nombre o marca.

    Esta función recorre el diccionario con los artículos encontrados y los
    imprime en un formato más legible. 

    Parameters
    ----------
    busqueda: dict
        Diccionario con los artículos encontrados.
    """
    print("\nArtículo(s) encontrado(s):")
    
    for item in busqueda["articulos"]:
        print(f"\nId: {item['id']}")
        print(f"Tipo: {item['tipo']}")
        print(f"Nombre: {item['nombre']}")
        print(f"Precio: ${item['precio']} MXN")
        print(f"Marca: {item['marca']}")
        print(f"Stock: {item['stock']}")

def mostrarMensaje(mensaje: dict) -> None:
    """
    Imprime el mensaje guardado en el diccionario "mensaje".

    Parameters
    ----------
    mensaje : dict
        Diccionario de un solo elemento con el mensaje.
    """
    for msj in mensaje["mensaje"]:
        print(f">> {msj['msj']}")

def mostrarCarrito(carrito: dict) -> None:
    """
    Imprime los artículos en el carrito de compras

    Parameters
    ----------
    carrito : dict
        Diccionario con los artículos del carrito de compras
    """
    print("Articulos en el carrito:")

    for item in carrito["carrito"]:
        print(f"\nId: {item['id']}")
        print(f"Tipo: {item['tipo']}")
        print(f"Nombre: {item['nombre']}")
        print(f"Precio: ${item['precio']} MXN")
        print(f"Marca: {item['marca']}")
        print(f"Cantidad: {item['cantidad']}")
        print(f"Precio total: ${item['precioTotal']} MXN")

def esperarTecla():
    """
    Espera a que se presione cualquier tecla.
    """
    return msvcrt.getch().decode("utf-8")  # devuelve la tecla como string