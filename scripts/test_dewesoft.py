#!/usr/bin/env python3

import argparse
import os
import sys

import dwdatareader as dw


CHUNK_ROWS = 1000


def log(mensaje):
    """
    Los mensajes de diagnóstico van a stderr.
    stdout queda reservado exclusivamente para el TXT.
    """
    print(mensaje, file=sys.stderr, flush=True)


def parsear_canales(texto):
    try:
        indices = [int(x.strip()) for x in texto.split(",") if x.strip()]
    except ValueError:
        raise ValueError(
            f"Lista de canales inválida: {texto}. "
            "Formato esperado: 0,1,2,3,4"
        )

    if not indices:
        raise ValueError("No se especificó ningún canal.")

    if len(indices) != len(set(indices)):
        raise ValueError("La lista de canales contiene índices repetidos.")

    return indices


def main():
    parser = argparse.ArgumentParser(
        description="Convierte canales de un archivo Dewesoft DXD a TXT."
    )

    parser.add_argument(
        "archivo",
        help="Ruta del archivo .dxd"
    )

    parser.add_argument(
        "canales",
        nargs="?",
        default="0,1,2,3,4",
        help="Índices separados por coma. Default: 0,1,2,3,4"
    )

    args = parser.parse_args()

    ruta = os.path.abspath(args.archivo)

    # ---------------------------------------------------------
    # Validaciones de entrada
    # ---------------------------------------------------------

    if not os.path.isfile(ruta):
        log(f"ERROR: archivo no encontrado: {ruta}")
        return 2

    if not ruta.lower().endswith(".dxd"):
        log(f"ERROR: el archivo no tiene extensión .dxd: {ruta}")
        return 2

    try:
        indices = parsear_canales(args.canales)
    except ValueError as e:
        log(f"ERROR: {e}")
        return 2

    # ---------------------------------------------------------
    # Lectura DXD
    # ---------------------------------------------------------

    try:
        with dw.DWFile(ruta) as archivo_dxd:

            canales_disponibles = list(archivo_dxd.values())

            valores_por_canal = []
            nombres_canales = []

            for indice in indices:

                if indice < 0 or indice >= len(canales_disponibles):
                    log(
                        f"ERROR: índice de canal fuera de rango: {indice}. "
                        f"Canales disponibles: {len(canales_disponibles)}"
                    )
                    return 3

                canal = canales_disponibles[indice]

                # Los DWBinaryChannel u otros tipos pueden no ser apropiados
                # para esta operación.
                if not hasattr(canal, "scaled"):
                    log(
                        f"ERROR: el canal {indice} ({canal.name}) "
                        "no soporta lectura scaled()."
                    )
                    return 3

                try:
                    _, valores = canal.scaled()
                except Exception as e:
                    log(
                        f"ERROR leyendo canal {indice} "
                        f"({canal.name}): {e}"
                    )
                    return 3

                if len(valores) == 0:
                    log(
                        f"ERROR: canal {indice} ({canal.name}) "
                        "no contiene muestras."
                    )
                    return 3

                valores_por_canal.append(valores)
                nombres_canales.append(canal.name)

            # -------------------------------------------------
            # Validación de número de muestras
            # -------------------------------------------------

            cantidades = [len(v) for v in valores_por_canal]

            if len(set(cantidades)) != 1:
                log(
                    "ERROR: los canales seleccionados tienen diferente "
                    f"cantidad de muestras: {cantidades}"
                )
                return 4

            numero_muestras = cantidades[0]

            log(
                f"Conversión iniciada: {os.path.basename(ruta)} | "
                f"canales={nombres_canales} | "
                f"muestras={numero_muestras}"
            )

            # -------------------------------------------------
            # Generación TXT
            #
            # IMPORTANTE:
            # stdout contiene SOLAMENTE los datos.
            #
            # Se mantiene el formato del conversor C:
            # - sin encabezado
            # - columnas separadas por espacio
            # - 12 decimales
            # -------------------------------------------------

            buffer = []

            for fila in range(numero_muestras):

                linea = " ".join(
                    f"{float(valores[fila]):.12f}"
                    for valores in valores_por_canal
                )

                buffer.append(linea)

                if len(buffer) >= CHUNK_ROWS:
                    sys.stdout.write("\n".join(buffer))
                    sys.stdout.write("\n")
                    buffer.clear()

            if buffer:
                sys.stdout.write("\n".join(buffer))
                sys.stdout.write("\n")

            sys.stdout.flush()

            log(
                f"Conversión completada correctamente: "
                f"{numero_muestras} filas."
            )

            return 0

    except Exception as e:
        log(f"ERROR abriendo/procesando DXD: {e}")
        return 5


if __name__ == "__main__":
    sys.exit(main())