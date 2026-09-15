import hashlib

bloques = [
    "Juan le da 5 dolares a Pedro",
    "Pedro le da 3 dolares a Maria",
    "Maria le da 2 dolares a Juan",
    "Juan le da 1 dolar a Maria",
    "Maria le da 1 dolar a Pedro"
]


def hash(data):
    """Recibe un string y devuelve su hash SHA-256 en hexadecimal."""
    return hashlib.sha256(data.encode()).hexdigest()


def construir_niveles(bloques):
    """Construye todos los niveles del árbol, desde las hojas hasta la raíz."""
    nivel_actual = [hash(bloque) for bloque in bloques]
    niveles = []

    while True:
        if len(nivel_actual) % 2 == 1 and len(nivel_actual) > 1:
            nivel_actual = nivel_actual + [nivel_actual[-1]]

        niveles.append(nivel_actual)

        if len(nivel_actual) == 1:
            break

        nuevo_nivel = []
        for i in range(0, len(nivel_actual), 2):
            nuevo_nivel.append(hash(nivel_actual[i] + nivel_actual[i + 1]))
        nivel_actual = nuevo_nivel

    return niveles


def obtener_raiz(niveles):
    return niveles[-1][0]


def obtener_prueba(niveles, indice):
    """Genera la prueba de inclusión (hash hermano, posición) para una hoja."""
    prueba = []
    idx = indice

    for nivel in niveles[:-1]:
        if idx % 2 == 0:
            idx_hermano, posicion = idx + 1, "derecha"
        else:
            idx_hermano, posicion = idx - 1, "izquierda"
        prueba.append((nivel[idx_hermano], posicion))
        idx = idx // 2

    return prueba


def verificar_prueba(dato, prueba, raiz):
    """Recalcula el camino desde el dato hasta la raíz y compara."""
    hash_actual = hash(dato)
    for hash_hermano, posicion in prueba:
        if posicion == "derecha":
            hash_actual = hash(hash_actual + hash_hermano)
        else:
            hash_actual = hash(hash_hermano + hash_actual)
    return hash_actual == raiz


def app():
    niveles = construir_niveles(bloques)
    raiz = obtener_raiz(niveles)
    print(f"Raíz original: {raiz}")

    # Modificar un bloque y comparar raíces
    bloques_modificados = bloques.copy()
    bloques_modificados[1] = "Pedro le da 30 dolares a Maria"
    raiz_modificada = obtener_raiz(construir_niveles(bloques_modificados))
    print(f"Raíz modificada: {raiz_modificada}")

    # Prueba de inclusión para el bloque 3
    indice_bloque = 2
    prueba = obtener_prueba(niveles, indice_bloque)

    valida = verificar_prueba(bloques[indice_bloque], prueba, raiz)
    invalida = verificar_prueba("Maria le da 999 dolares a Juan", prueba, raiz)
    print(f"Verificación con dato correcto: {'VÁLIDA' if valida else 'INVÁLIDA'}")
    print(f"Verificación con dato incorrecto: {'VÁLIDA' if invalida else 'INVÁLIDA'}")


app()