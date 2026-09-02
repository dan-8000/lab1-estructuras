# Matriz de 100.000 x 100.000 en disco

Estudiante: Daniel

Trabajo para Estructuras de Datos. El problema es manejar una matriz de
100.000 x 100.000 celdas (10.000 millones de celdas, 10 GB) sin que el
programa se quede sin memoria RAM y sin tardar una eternidad en escribirla
al disco.

La matriz se guarda de verdad en un archivo. No se genera al vuelo cada vez
que se mira: se escribe una sola vez y despues se lee del disco.

## Los tres problemas y como se resuelven

**1. Consumo excesivo de RAM.** La matriz completa no cabe comoda en memoria
(10 GB), y menos si el computador tiene 8 o 16 GB. La solucion es no cargarla
nunca entera:

- La matriz se parte en 10.000 bloques de 1000 x 1000 celdas (1 MB cada uno).
  A esos bloques les decimos *tiles*.
- Para verla se usa `np.memmap`, que no copia el archivo a memoria sino que lo
  mapea. El sistema operativo trae del disco solo las paginas de 4 KB que se
  tocan y las suelta cuando necesita memoria.
- Medido: con el archivo de 10 GB abierto y despues de navegar por varias
  zonas, el programa tiene 5,2 MB de la matriz en RAM. Eso es el 0,054 %.

Una consecuencia interesante es que el programa NO tiene ninguna cache escrita
a mano. No hace falta: la cache la hace el sistema operativo y la hace mejor.

**2. Escritura lenta a disco.** Escribir los 10 GB tardaba 121 segundos. Ahora
tarda 45. Lo que se hizo:

- Lo primero fue medir donde estaba el problema. El disco escribe a mas de
  1 GB/s, o sea que el disco nunca fue el cuello de botella: el tiempo se iba
  en *calcular* los valores.
- Calcular un tile de 1000 x 1000 de una sola vez obliga a numpy a crear una
  decena de arrays temporales de 8 MB. Eso no cabe en la cache del procesador,
  asi que el limite pasa a ser el ancho de banda de la memoria. Se comprobo
  que ni siquiera mejoraba usando 16 procesos: el escalado era de 0,9x.
- Calculando el tile en franjas de 100 filas, cada temporal ocupa 800 KB y si
  cabe en cache. El mismo calculo, sin cambiar un solo valor del resultado,
  paso de 8,9 ms a 4,1 ms por tile (2,2 veces mas rapido).
- Ya con el calculo en cache, repartirlo entre 8 procesos si sirve. Cada
  proceso escribe directamente en su tramo del archivo con `seek`, asi que no
  se manda ni un byte de datos entre procesos.
- Se probaron 4, 8, 12 y 16 procesos: el mejor es 8, que son los nucleos
  fisicos. Con 16 (usando hyperthreading) empeora, porque el problema es de
  memoria y no de CPU.

**3. Optimizacion en la lectura y el almacenamiento.** Aqui lo importante es el
orden en que se guardan los datos:

- Un archivo normal guardaria la matriz fila por fila. Con ese orden, leer un
  bloque de 1000 x 1000 significa leer 1000 pedazos separados 100.000 bytes
  entre si. Guardandola por tiles, ese mismo bloque es 1 MB seguido y se lee
  de una sola vez.
- El mapa general (la vista de toda la matriz de un vistazo) no se saca de los
  10 GB. Se guarda aparte en `matriz_mapa.dat`, que son 10 KB con el promedio
  de cada tile. Sacarlo del archivo grande costaba 10.000 lecturas dispersas:
  7,5 segundos y 497 MB arrastrados a RAM. Leyendo los 10 KB: 0 ms.
- El promedio de cada tile se calcula mientras se crea la matriz, cuando el
  tile ya esta en memoria. Calcularlo despues obligaria a leer los 10 GB otra
  vez.

## Archivos del repositorio

| Archivo | Que hace |
|---|---|
| `formato.py` | Define el formato del archivo: cuanto mide la matriz, de que tamaño son los tiles y en que byte empieza cada uno. Lo usan el creador y el visor, para que el formato este escrito en un solo lugar. |
| `crear_matriz.py` | Crea `matriz.dat` (10 GB) y `matriz_mapa.dat` (10 KB) usando 8 procesos. Tarda unos 45 segundos. |
| `visor.py` | Interfaz para ver la matriz en tres niveles de zoom, con las coordenadas reales en los ejes y un panel que muestra cuanta RAM y cuanto disco se estan usando. |
| `verificar.py` | Comprueba que el archivo es de verdad una matriz de 100.000 x 100.000 y que su contenido es correcto. Nueve comprobaciones. |
| `matriz.dat` | Los datos. NO esta en el repositorio (10 GB), se genera con `crear_matriz.py`. |
| `matriz_mapa.dat` | El mapa general, 10 KB. Tambien se genera. |

## Como ejecutarlo

Hace falta Python 3 con numpy y matplotlib.

    pip install numpy matplotlib

Primero se crea la matriz (una sola vez, unos 45 segundos, ocupa 10 GB):

    python3 crear_matriz.py

Despues ya se puede abrir el visor:

    python3 visor.py

Y para comprobar que todo esta bien:

    python3 verificar.py

## Como se usa el visor

La ventana tiene tres paneles, de menos a mas zoom:

1. **Mapa**: los 10.000 tiles de un vistazo. Cada cuadrito es un bloque de
   1000 x 1000 celdas.
2. **Tile**: un bloque de 1000 x 1000, dividido con una rejilla en 10 x 10
   sub-bloques.
3. **Sub-bloque**: 100 x 100 celdas, donde ya se distingue cada celda.

Debajo aparece una tabla con los valores exactos alrededor de la celda
seleccionada, y una linea con el estado de la memoria y del disco.

Controles:

- Click en cualquiera de los tres paneles: baja hasta esa coordenada.
- Rueda del raton sobre el mapa: acercar o alejar, para poder darle a un tile
  concreto.
- Caja de abajo: escribir por ejemplo `73512, 41299` y pulsar Enter.
- Boton de la casita en la barra de matplotlib: volver a la vista completa.

## Como verificar el contenido de la matriz

Con `python3 verificar.py`. Es un programa aparte que a proposito NO importa
las constantes de `formato.py`: vuelve a escribir por su cuenta el tamaño y la
formula de direccionamiento, y lee el archivo con `os.pread` en vez de numpy.
Si dos implementaciones hechas por separado dan el mismo resultado, entonces el
archivo es lo que decimos que es.

Las nueve comprobaciones:

1. El archivo mide 10.000.000.000 bytes y su raiz cuadrada es exactamente
   100.000, o sea que a un byte por celda son 100.000 x 100.000 celdas.
2. La celda `A[99999,99999]` cae justo en el ultimo byte del archivo.
3. La celda `A[100000,0]` caeria un byte despues del final, o sea que no
   existe. Entre esta comprobacion y la anterior queda claro que son
   exactamente 100.000 filas, ni una mas ni una menos.
4. Los 10.000 tiles cubren el archivo entero sin huecos ni solapes.
5. Leer una celda con numpy y con `os.pread` da el mismo valor (200 celdas al
   azar).
6. Se lee la diagonal completa `A[k,k]` para los 100.000 valores de k, que toca
   cada fila una vez y cada columna una vez.
7. Se sacan las firmas de 73 tiles repartidos por el archivo y salen las 73
   distintas, o sea que no es una matriz chica repetida para inflar el tamaño.
8. Se leen los 10 GB enteros para comprobar que no hay huecos ni zonas en
   blanco, y se sacan el minimo, el maximo y el promedio.
9. Se comparan cinco tiles byte a byte contra la formula que los genero, para
   comprobar que el contenido es correcto y no solo el tamaño.

Tambien se puede comprobar por fuera, sin creerle a ningun programa:

    stat -c%s matriz.dat        # 10000000000
    wc -c < matriz.dat          # 10000000000, contando de verdad
    du -h matriz.dat            # lo que ocupa en el disco
    tail -c 1 matriz.dat | xxd  # el ultimo byte, que es A[99999,99999]

## Que valores tiene la matriz

Cada celda guarda un byte (0 a 255) que sale de una formula sobre sus
coordenadas: un hash de (i, j) para el ruido, mas dos ondas para que se vea un
patron al alejarse. La formula esta en `crear_matriz.py`, en la funcion
`valores()`.

Se uso una formula en vez de datos reales por dos razones practicas: no hay que
descargar 10 GB de datos de ningun lado, y como cada celda depende solo de sus
coordenadas, se puede comprobar en cualquier momento si un valor guardado es el
correcto (comprobacion 8).

## Datos medidos

Todo lo de aqui esta medido en la maquina donde se hizo el trabajo (AMD Ryzen
AI 7 350, 8 nucleos, disco NVMe con btrfs):

| Cosa | Antes | Ahora |
|---|---|---|
| Crear los 10 GB | 121 s | 45 s |
| Generar un tile de 1 MB | 8,9 ms | 4,1 ms |
| Dibujar el mapa general | 7500 ms | 0 ms |
| RAM arrastrada al dibujar el mapa | 497 MB | 0 MB |
| RAM de la matriz despues de navegar | - | 5,2 MB (0,054 %) |
| Leer un tile de 1 MB y dibujarlo | - | 143 ms |
| Leer una celda suelta al azar | - | 0,38 ms |
