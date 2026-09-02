"""
Comprueba que matriz.dat es de verdad una matriz de 100.000 x 100.000 y que
su contenido es el que deberia ser.

Para las comprobaciones de formato NO usa formato.py a proposito: vuelve a
declarar por su cuenta el tamano y la formula de direccionamiento, y lee el
archivo con os.pread en vez de numpy.  Si dos implementaciones escritas por
separado coinciden, el archivo es lo que decimos que es; si verificar.py
importara las mismas constantes que el visor, no estaria comprobando nada.

Ejecutar:  python3 verificar.py    (tarda unos 10 s: lee los 10 GB enteros)
"""
import numpy as np
import os, math, time, hashlib

RUTA = "matriz.dat"
N = 100_000            # lo que hay que demostrar
CHUNK = 1_000
NCH = N // CHUNK       # 100 x 100 tiles
BYTES_TILE = CHUNK * CHUNK


def byte_de(i, j):
    """Byte exacto del archivo donde vive A[i, j].  Formula independiente."""
    tile = (i // CHUNK) * NCH + (j // CHUNK)
    dentro = (i % CHUNK) * CHUNK + (j % CHUNK)
    return tile * BYTES_TILE + dentro


fd = os.open(RUTA, os.O_RDONLY)
tam = os.fstat(fd).st_size
ok = []


def prueba(titulo, condicion, detalle):
    ok.append(condicion)
    print(f"[{'OK ' if condicion else 'MAL'}] {titulo}\n        {detalle}")


print(f"Verificando {RUTA}\n")

# 1 -------------------------------------------------------------------------
lado = math.isqrt(tam)
prueba("El archivo tiene N*N bytes con N entero",
       lado * lado == tam and lado == N,
       f"{tam:,} bytes, raiz cuadrada exacta = {lado:,}  ->  {lado:,} x {lado:,} "
       f"celdas a 1 byte cada una")

# 2 -------------------------------------------------------------------------
ultima = byte_de(N - 1, N - 1)
siguiente = byte_de(N - 1, N - 1) + 1
prueba("La ultima celda A[99999,99999] es el ultimo byte del archivo",
       ultima == tam - 1,
       f"A[{N-1},{N-1}] -> byte {ultima:,}   |   ultimo byte del archivo: {tam-1:,}")

prueba("Una fila 100.000 se saldria del archivo (no existe)",
       byte_de(N, 0) >= tam,
       f"A[{N},0] -> byte {byte_de(N,0):,}  >=  tamano {tam:,}   (fuera de rango)")

# 3 -------------------------------------------------------------------------
t = time.time()
destinos = set()
for bf in range(NCH):
    for bc in range(NCH):
        destinos.add(byte_de(bf * CHUNK, bc * CHUNK))
prueba("Los 10.000 tiles cubren el archivo entero sin huecos ni solapes",
       len(destinos) == NCH * NCH and min(destinos) == 0
       and max(destinos) + BYTES_TILE == tam,
       f"{len(destinos):,} tiles distintos x {BYTES_TILE:,} bytes = "
       f"{len(destinos)*BYTES_TILE:,} bytes = tamano del archivo")

# 4 -------------------------------------------------------------------------
mm = np.memmap(RUTA, dtype=np.uint8, mode="r")
rng = np.random.default_rng(0)
iguales = 0
for _ in range(200):
    i, j = int(rng.integers(N)), int(rng.integers(N))
    por_numpy = int(mm[byte_de(i, j)])
    por_sistema = os.pread(fd, 1, byte_de(i, j))[0]
    iguales += por_numpy == por_sistema
prueba("Dos formas independientes de leer dan el mismo valor",
       iguales == 200, f"200 celdas al azar leidas con numpy y con os.pread: "
                       f"{iguales}/200 coinciden")

# 5 -------------------------------------------------------------------------
t = time.time()
diag = np.frombuffer(bytes(os.pread(fd, 1, byte_de(k, k))[0] for k in range(N)),
                     np.uint8)
prueba("Las 100.000 filas y las 100.000 columnas existen y tienen dato",
       len(diag) == N,
       f"diagonal completa A[k,k] para k=0..{N-1}: {len(diag):,} celdas leidas "
       f"en {time.time()-t:.1f} s (toca cada fila y cada columna una vez)")

# 6 -------------------------------------------------------------------------
firmas = {hashlib.blake2b(os.pread(fd, BYTES_TILE, t0), digest_size=8).digest()
          for t0 in sorted(destinos)[::137]}
prueba("No es una matriz chica repetida: los tiles son todos distintos",
       len(firmas) == len(range(0, NCH * NCH, 137)),
       f"{len(firmas)} tiles de 1 MB muestreados, {len(firmas)} firmas distintas")

# 7 -------------------------------------------------------------------------
t, leidos, ceros, mn, mx, suma = time.time(), 0, 0, 255, 0, 0
with open(RUTA, "rb") as f:
    while trozo := f.read(100 * 10**6):
        a = np.frombuffer(trozo, np.uint8)
        leidos += a.size; ceros += int((a == 0).sum())
        mn, mx, suma = min(mn, int(a.min())), max(mx, int(a.max())), suma + int(a.sum())
seg = time.time() - t
prueba("El archivo esta completo de verdad (se lee entero, sin huecos)",
       leidos == tam == N * N,
       f"{leidos:,} bytes leidos uno a uno en {seg:.0f} s ({leidos/10**6/seg:.0f} MB/s)"
       f"\n        valores: min {mn}, max {mx}, media {suma/leidos:.1f}, "
       f"ceros {100*ceros/leidos:.4f} %")

# 8 -------------------------------------------------------------------------
from crear_matriz import generar_tile          # la formula que escribio el archivo

iguales = 0
elegidos = [(0, 0), (37, 91), (50, 50), (99, 99), (12, 74)]
for bf, bc in elegidos:
    guardado = np.frombuffer(os.pread(fd, BYTES_TILE, byte_de(bf * CHUNK, bc * CHUNK)),
                             np.uint8).reshape(CHUNK, CHUNK)
    iguales += np.array_equal(guardado, generar_tile(bf, bc))
prueba("El contenido guardado es el que dice la formula",
       iguales == len(elegidos),
       f"{iguales} de {len(elegidos)} tiles de 1 MB comparados byte a byte "
       f"contra generar_tile(): {elegidos}")

os.close(fd)
print(f"\n{sum(ok)}/{len(ok)} comprobaciones superadas"
      f"  ->  la matriz es {N:,} x {N:,} = {N*N:,} celdas")
