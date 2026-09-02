"""
Visor de la matriz de 100.000 x 100.000 guardada en matriz.dat.

Ejecutar:  python3 visor.py      (antes hay que correr crear_matriz.py)

Muestra la matriz en tres niveles de zoom y, en todo momento, cuanta RAM se
esta usando de verdad.  La idea es que el archivo pesa 10 GB pero el programa
nunca pasa de unos pocos MB, porque:

  - np.memmap NO carga el archivo: lo mapea.  El nucleo trae del disco solo
    las paginas de 4 KB que se tocan, y las suelta cuando necesita memoria.
    Por eso el programa no lleva ninguna cache escrita a mano: la cache la
    hace el sistema operativo, y la hace mejor.

  - Como el archivo esta ordenado por tiles (ver formato.py), enseñar un
    bloque de 1000x1000 es UNA lectura de 1 MB seguido, no 1000 lecturas
    sueltas.

  - El mapa general no se saca de los 10 GB sino de matriz_mapa.dat, que son
    10 KB con el promedio de cada tile.  Sacarlo del archivo grande costaria
    10.000 lecturas dispersas: 7,5 segundos y medio giga de paginas en RAM.

CONTROLES
  click en cualquiera de los tres paneles -> baja a esa coordenada
  rueda del raton sobre el mapa           -> acercar / alejar
  caja "ir a i, j"                        -> escribir  73512, 41299  y Enter
  boton de la casita (barra de abajo)     -> volver a la vista completa
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox
from matplotlib.patches import Rectangle
import os, sys, time

from formato import (RUTA, RUTA_MAPA, N, CHUNK, SUB, NCH, NSUB,
                     BYTES_TILE, BYTES_TOTAL, posicion)

VENTANA = 8       # cuantas filas y columnas de valores exactos se listan

for archivo in (RUTA, RUTA_MAPA):
    if not os.path.exists(archivo):
        sys.exit(f"Falta {archivo}.  Ejecuta primero:  python3 crear_matriz.py")

# mode="r": solo lectura.  Esta linea no carga nada, solo mapea el archivo.
mm = np.memmap(RUTA, dtype=np.uint8, mode="r")
mapa = np.fromfile(RUTA_MAPA, np.uint8).reshape(NCH, NCH)


def leer_tile(bf, bc):
    """Vista de 1000x1000 sobre el archivo.  No copia nada."""
    o = posicion(bf, bc)
    return mm[o:o + BYTES_TILE].reshape(CHUNK, CHUNK)


def celda(i, j):
    """Un solo valor.  El nucleo trae solo la pagina de 4 KB que lo contiene."""
    return int(leer_tile(i // CHUNK, j // CHUNK)[i % CHUNK, j % CHUNK])


def ram_proceso():
    """RAM total de este proceso (RSS), en MB."""
    with open("/proc/self/statm") as f:
        paginas = int(f.read().split()[1])
    return paginas * os.sysconf("SC_PAGE_SIZE") / 2**20


def ram_de_la_matriz():
    """MB del archivo que el nucleo tiene ahora mismo cargados en RAM.

    /proc/self/smaps lista cada region mapeada y su Rss (lo que esta residente).
    """
    objetivo, total, dentro = os.path.abspath(RUTA), 0, False
    with open("/proc/self/smaps") as f:
        for linea in f:
            if "-" in linea.split(" ")[0]:                # cabecera de region
                dentro = linea.rstrip().endswith(objetivo)
            elif dentro and linea.startswith("Rss:"):
                total += int(linea.split()[1])            # viene en kB
    return total / 1024


# --------------------------------------------------------------- ventana ---
fig = plt.figure(figsize=(15, 8.2))
fig.canvas.manager.set_window_title(f"Matriz {N:,} x {N:,} en disco")
ax_mapa = fig.add_axes([0.04, 0.47, 0.26, 0.45])
ax_tile = fig.add_axes([0.37, 0.47, 0.26, 0.45])
ax_sub = fig.add_axes([0.70, 0.47, 0.26, 0.45])
ax_info = fig.add_axes([0.04, 0.02, 0.92, 0.28]); ax_info.axis("off")
ax_caja = fig.add_axes([0.115, 0.345, 0.11, 0.038])

# Nivel 1: los 10 KB del mapa, con los ejes en coordenadas de la matriz.
ax_mapa.imshow(mapa, cmap="viridis", vmin=0, vmax=255,
               extent=(0, N, N, 0), interpolation="nearest")
ax_mapa.set_title(f"1) Mapa: {NCH}x{NCH} tiles (promedio de cada uno)\n"
                  f"(rueda del raton = zoom)", fontsize=10)
marco = Rectangle((0, 0), CHUNK, CHUNK, fill=False, color="red", lw=1.5)
ax_mapa.add_patch(marco)
texto = ax_info.text(0, 1, "", va="top", family="monospace", fontsize=8.5)


def ir_a(i, j):
    """Centra los tres niveles en la celda (i, j), leyendo del disco."""
    i = min(max(int(i), 0), N - 1)
    j = min(max(int(j), 0), N - 1)
    bf, bc = i // CHUNK, j // CHUNK              # tile que la contiene
    sf, sc = (i % CHUNK) // SUB, (j % CHUNK) // SUB   # sub-bloque dentro del tile
    f0, c0 = bf * CHUNK, bc * CHUNK              # esquina del tile
    fs, cs = f0 + sf * SUB, c0 + sc * SUB        # esquina del sub-bloque

    t = time.time()
    tile = leer_tile(bf, bc)                     # 1 MB seguido del archivo
    sub = tile[sf * SUB:(sf + 1) * SUB, sc * SUB:(sc + 1) * SUB]   # vista, 0 bytes
    valor = int(tile[i - f0, j - c0])
    ms = (time.time() - t) * 1000

    # Nivel 2: el tile entero, con la rejilla de sub-bloques encima.
    ax_tile.clear()
    ax_tile.imshow(tile, cmap="viridis", vmin=0, vmax=255,
                   extent=(c0, c0 + CHUNK, f0 + CHUNK, f0))
    for k in range(1, NSUB):
        ax_tile.axhline(f0 + k * SUB, color="w", lw=0.4, alpha=0.4)
        ax_tile.axvline(c0 + k * SUB, color="w", lw=0.4, alpha=0.4)
    ax_tile.add_patch(Rectangle((cs, fs), SUB, SUB, fill=False, color="red", lw=1.5))
    ax_tile.set_title(f"2) Tile ({bf}, {bc}) = {CHUNK}x{CHUNK}  ->  1 MB seguido\n"
                      f"empieza en el byte {posicion(bf, bc):,}", fontsize=10)

    # Nivel 3: 100x100 celdas, ya se distingue una por una.
    ax_sub.clear()
    ax_sub.imshow(sub, cmap="viridis", vmin=sub.min(), vmax=sub.max(),
                  extent=(cs, cs + SUB, fs + SUB, fs))
    ax_sub.plot(j + 0.5, i + 0.5, "r+", markersize=12)
    ax_sub.set_title(f"3) Sub-bloque ({sf}, {sc}) = {SUB}x{SUB}  (color local)\n"
                     f"filas {fs}-{fs+SUB-1}  cols {cs}-{cs+SUB-1}", fontsize=10)

    for ax in (ax_mapa, ax_tile, ax_sub):
        ax.set_xlabel("columna j"); ax.set_ylabel("fila i")
    marco.set_xy((c0, f0))

    # Tabla de valores exactos: aqui no hay colores de por medio, son los bytes.
    vi, vj = min(i, N - VENTANA), min(j, N - VENTANA)
    tabla = ["VALORES EXACTOS  A[i, j]  (uint8, 0-255)",
             " " * 10 + "".join(f"j={vj+k:<8}" for k in range(VENTANA))]
    for k in range(VENTANA):
        tabla.append(f"i={vi+k:<8}" + "".join(
            f"{celda(vi + k, vj + c):<10d}" for c in range(VENTANA)))

    ocupado = os.stat(RUTA).st_blocks * 512
    en_ram = ram_de_la_matriz()
    texto.set_text(
        f"DISCO     {RUTA}: {BYTES_TOTAL/10**9:.2f} GB   |"
        f"  ocupado de verdad: {ocupado/10**9:.2f} GB   |"
        f"  {NCH*NCH:,} tiles de {BYTES_TILE/10**6:.0f} MB"
        f"  + mapa de {os.path.getsize(RUTA_MAPA)/1000:.0f} KB\n"
        f"POSICION  i={i}  j={j}   ->   tile ({bf}, {bc})   sub-bloque ({sf}, {sc})"
        f"   |  A[{i},{j}] = {valor}   |  leido en {ms:.1f} ms\n"
        f"RAM       proceso (RSS): {ram_proceso():.1f} MB   |"
        f"  de la matriz dentro de RAM: {en_ram:.1f} MB"
        f"  ({100*en_ram*2**20/BYTES_TOTAL:.4f} % del archivo, y el nucleo la"
        f" suelta si hace falta)\n\n" + "\n".join(tabla))
    fig.canvas.draw_idle()


def al_hacer_click(ev):
    """Los tres paneles usan coordenadas de la matriz: ev.xdata ES la columna."""
    if ev.xdata is None or str(getattr(fig.canvas.toolbar, "mode", "")):
        return                                   # no hacer nada si el zoom esta activo
    if ev.inaxes in (ax_mapa, ax_tile, ax_sub):
        ir_a(ev.ydata, ev.xdata)


def al_rodar(ev):
    """Rueda del raton sobre el mapa: acercar o alejar centrado en el cursor."""
    if ev.inaxes is not ax_mapa:
        return
    f = 0.75 if ev.button == "up" else 1 / 0.75
    x0, x1 = ax_mapa.get_xlim(); y0, y1 = ax_mapa.get_ylim()
    ax_mapa.set_xlim(ev.xdata + (x0 - ev.xdata) * f, ev.xdata + (x1 - ev.xdata) * f)
    ax_mapa.set_ylim(ev.ydata + (y0 - ev.ydata) * f, ev.ydata + (y1 - ev.ydata) * f)
    fig.canvas.draw_idle()


def buscar(txt):
    """Caja de busqueda: acepta  73512, 41299  o  73512 41299."""
    p = txt.replace(",", " ").replace(";", " ").split()
    if len(p) == 2 and all(v.lstrip("-").isdigit() for v in p):
        ir_a(int(p[0]), int(p[1]))


# matplotlib 3.11 falla al redimensionar la ventana si hay una caja de texto.
# Su manejador solo servia para dejar de escribir; se repone sin el fallo.
TextBox._resize = lambda self, event: self.stop_typing()

caja = TextBox(ax_caja, "ir a  i, j:  ", initial="73512, 41299")
caja.on_submit(buscar)
fig.canvas.mpl_connect("button_press_event", al_hacer_click)
fig.canvas.mpl_connect("scroll_event", al_rodar)
ir_a(73_512, 41_299)
plt.show()
