"""
Crea matriz.dat (10 GB) y matriz_mapa.dat.

Ejecutar:  python3 crear_matriz.py       (tarda unos 45 segundos)

Los tres problemas que resuelve este programa:

1. RAM.  La matriz completa nunca existe en memoria.  Cada proceso trabaja con
   un tile de 1 MB, lo escribe y lo descarta.  Con 8 procesos, el pico de
   memoria son unos 8 MB de datos, no 10 GB.

2. ESCRITURA LENTA.  Escribir los 10 GB tardaba 121 segundos; ahora tarda 45.
   Lo primero fue medir: el disco escribe a mas de 1 GB/s, asi que el disco
   nunca fue el problema, el tiempo se iba en CALCULAR los valores.  Dos
   cambios, en este orden:
     a) calcular cada tile por franjas de 100 filas, para que los arrays
        temporales quepan en la cache del procesador (ver generar_tile);
     b) repartir el trabajo en 100 tareas (una fila de tiles cada una) entre 8
        procesos, cada uno escribiendo directamente en su tramo del archivo
        con seek, sin mandarse datos entre ellos.
   El orden importa: sin (a), poner mas procesos no servia de nada, porque el
   limite era el ancho de banda de la memoria y no la CPU.

3. TRABAJO REPETIDO.  El promedio de cada tile, que es lo que va en
   matriz_mapa.dat, se calcula aqui mientras el tile todavia esta en RAM.
   Calcularlo despues obligaria a leer los 10 GB otra vez.
"""
import numpy as np
import os, time
from multiprocessing import Pool

from formato import (RUTA, RUTA_MAPA, CHUNK, NCH, BYTES_TILE, BYTES_TOTAL,
                     posicion)

FRANJA = 100      # filas que se calculan de golpe (ver generar_tile)
PROCESOS = 8      # nucleos fisicos de la maquina

# Constantes del hash splitmix64.  Convierten (i, j) en un numero
# pseudoaleatorio: la misma celda da siempre el mismo valor.
_K1, _K2 = np.uint64(0x9E3779B97F4A7C15), np.uint64(0xC2B2AE3D27D4EB4F)
_M1, _M2 = np.uint64(0xBF58476D1CE4E5B9), np.uint64(0x94D049BB133111EB)


def valores(i, j):
    """La formula de la matriz: A[i,j] a partir de sus coordenadas.

    i es un vector columna y j un vector fila, asi que numpy calcula los senos
    sobre unos pocos miles de numeros y arma el rectangulo por broadcasting.
    """
    x = i * _K1 + j * _K2
    x ^= x >> np.uint64(30); x *= _M1
    x ^= x >> np.uint64(27); x *= _M2
    x ^= x >> np.uint64(31)
    ruido = (x >> np.uint64(11)).astype(np.float64) / float(1 << 53)
    grande = np.sin(i / 6000.0) * np.cos(j / 6000.0)   # patron a gran escala
    detalle = np.sin(i / 70.0) * np.sin(j / 90.0)      # patron a escala de tile
    v = 0.5 + 0.28 * grande + 0.14 * detalle + 0.08 * (ruido - 0.5)
    return (v * 256).clip(0, 255).astype(np.uint8)


def generar_tile(bf, bc):
    """Los 1000x1000 valores del tile (bf, bc), por franjas de FRANJA filas.

    Calcular el tile de una sola vez obliga a numpy a crear una decena de
    arrays temporales de 8 MB, que no caben en la cache del procesador: el
    limite pasa a ser el ancho de banda de la memoria y ni siquiera mejora al
    usar varios procesos.  Calculandolo en franjas de 100 filas, cada temporal
    ocupa 800 KB, cabe en cache, y el mismo calculo va 3 veces mas rapido.
    """
    tile = np.empty((CHUNK, CHUNK), np.uint8)
    j = np.arange(bc * CHUNK, (bc + 1) * CHUNK, dtype=np.uint64)[None, :]
    for r in range(0, CHUNK, FRANJA):
        i = np.arange(bf * CHUNK + r, bf * CHUNK + r + FRANJA,
                      dtype=np.uint64)[:, None]
        tile[r:r + FRANJA] = valores(i, j)
    return tile


def escribir_fila(bf):
    """Tarea de un proceso: los 100 tiles de la fila bf (100 MB del archivo).

    Devuelve solo los 100 promedios (100 bytes), no los datos: lo pesado se
    escribe directo al disco desde el proceso que lo genero.
    """
    medias = np.empty(NCH, np.uint8)
    with open(RUTA, "r+b") as f:
        f.seek(posicion(bf, 0))
        for bc in range(NCH):
            tile = generar_tile(bf, bc)
            medias[bc] = tile.mean()      # el mapa sale gratis: ya esta en RAM
            f.write(tile)                 # numpy escribe sin copia intermedia
    return bf, medias


def main():
    print(f"Creando {RUTA}: {BYTES_TOTAL/10**9:.0f} GB en {NCH*NCH:,} tiles "
          f"de {BYTES_TILE/10**6:.0f} MB, con {PROCESOS} procesos")

    # Reservar los 10 GB de golpe.  Medido en btrfs no acelera la escritura,
    # pero si no hay espacio el programa falla aqui y no a los 40 segundos con
    # el archivo a medio escribir.
    with open(RUTA, "wb") as f:
        os.posix_fallocate(f.fileno(), 0, BYTES_TOTAL)

    mapa = np.empty((NCH, NCH), np.uint8)
    t0 = time.time()
    with Pool(PROCESOS) as pool:
        for hechas, (bf, medias) in enumerate(
                pool.imap_unordered(escribir_fila, range(NCH)), 1):
            mapa[bf] = medias
            gb = hechas * NCH * BYTES_TILE / 10**9
            print(f"\r  {hechas:3d}/{NCH} filas   {gb:5.2f} GB   "
                  f"{gb*1000/(time.time()-t0):4.0f} MB/s", end="", flush=True)

    mapa.tofile(RUTA_MAPA)   # 10 KB: el promedio de cada tile
    print(f"\nListo en {time.time()-t0:.0f} s.")
    print(f"  {RUTA}      {os.path.getsize(RUTA):,} bytes")
    print(f"  {RUTA_MAPA} {os.path.getsize(RUTA_MAPA):,} bytes")
    print("Ahora:  python3 visor.py")


if __name__ == "__main__":
    main()
