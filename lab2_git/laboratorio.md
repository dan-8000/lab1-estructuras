# Árbol de Merkle - Laboratorio 2

Implementación simple de un Árbol de Merkle en Python usando SHA-256.

## ¿Qué hace el script?

1. Construye el árbol a partir de 5 bloques de datos (transacciones simuladas).
2. Modifica uno de los bloques y muestra que la raíz cambia por completo.
3. Genera una prueba de inclusión para un bloque específico.
4. Verifica esa prueba con el dato correcto (debe ser válida).
5. Verifica esa misma prueba con un dato falso (debe fallar).

## Métodos

### `hash(data)`
Recibe un string y devuelve su hash SHA-256 en hexadecimal. Es la función base que se usa para todo: hashear las hojas y hashear la combinación de nodos hijos.

### `construir_niveles(bloques)`
Construye el árbol completo, nivel por nivel, desde las hojas hasta la raíz.
- El primer nivel son los hashes de cada bloque (las hojas).
- Si un nivel tiene un número impar de elementos, se duplica el último para poder combinarlos de dos en dos.
- Cada nivel siguiente se forma concatenando pares de hashes del nivel anterior y volviéndolos a hashear.
- Se detiene cuando queda un solo hash: la raíz.
- Devuelve una lista con todos los niveles (de hojas a raíz), necesaria más adelante para generar pruebas de inclusión.

### `obtener_raiz(niveles)`
Devuelve el último nivel (la raíz), que es el hash que representa a todo el conjunto de datos.

### `obtener_prueba(niveles, indice)`
Genera la prueba de inclusión (Merkle path) para la hoja en la posición `indice`.
Recorre el árbol desde la hoja hasta la raíz y, en cada nivel, guarda el hash del "hermano" necesario para recalcular el hash del nivel superior, junto con su posición (`izquierda` o `derecha`).

### `verificar_prueba(dato, prueba, raiz)`
Verifica que un dato realmente pertenece al árbol, sin necesidad de recorrerlo entero:
1. Hashea el dato de entrada.
2. Va combinando ese hash con cada hash de la prueba, en el orden y posición indicados.
3. Si el resultado final coincide con la raíz, la prueba es **válida**; si no coincide (por ejemplo, si el dato fue alterado), es **inválida**.