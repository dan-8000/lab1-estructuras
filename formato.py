"""
Formato del archivo matriz.dat.  Lo comparten crear_matriz.py y visor.py.

La matriz de 100.000 x 100.000 se guarda como bytes crudos, un byte por celda
(uint8, valores 0-255).  Son 10^10 bytes = 10 GB exactos.

Lo importante es el ORDEN en que se guardan.  Un archivo normal guardaria la
matriz fila por fila, y entonces un bloque de 1000x1000 quedaria partido en
1000 pedazos separados 100.000 bytes entre si.  Aqui se guarda BLOQUE POR
BLOQUE (a esos bloques se les llama tiles), asi que cada bloque de 1000x1000
ocupa 1 MB seguido en el disco y se lee de una sola vez.

           archivo:  [ tile(0,0) | tile(0,1) | ... | tile(99,99) ]
                       1 MB        1 MB              1 MB
"""

RUTA = "matriz.dat"
RUTA_MAPA = "matriz_mapa.dat"

N = 100_000           # la matriz es N x N
CHUNK = 1_000         # cada tile es CHUNK x CHUNK celdas
SUB = 100             # para ver de cerca, cada tile se divide en sub-bloques
NCH = N // CHUNK      # 100 x 100 = 10.000 tiles
NSUB = CHUNK // SUB   # 10 x 10 sub-bloques por tile
BYTES_TILE = CHUNK * CHUNK    # 1.000.000 bytes por tile
BYTES_TOTAL = N * N           # 10.000.000.000 bytes en total


def posicion(bf, bc):
    """Byte del archivo donde empieza el tile (bf, bc)."""
    return (bf * NCH + bc) * BYTES_TILE


def byte_de(i, j):
    """Byte del archivo donde esta guardada la celda A[i, j]."""
    return (posicion(i // CHUNK, j // CHUNK)
            + (i % CHUNK) * CHUNK + (j % CHUNK))
