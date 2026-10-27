"""
validar_checksum.py
--------------------
Invocado por NiFi (ExecuteStreamCommand) dentro del Process Group
02_Validacion. Recibe la ruta de un archivo recibido, busca su
manifest.json asociado (mismo nombre base + '.manifest.json'), y
valida:
  1. Que el manifest exista.
  2. Que el tamaño del archivo coincida con el declarado.
  3. Que el checksum SHA-256 coincida con el declarado en origen.

Imprime "OK" o "FAIL" en stdout (NiFi lo captura en el atributo
'validacion_resultado' gracias a 'Output Destination Attribute').
Además usa el código de salida (0 = válido, 1 = inválido) para que
quede registrado también en los logs de NiFi.

USO (invocado por NiFi):
    python3 validar_checksum.py /data/andahuaylillas/staging/DATA_20260802.dxd
"""

import hashlib
import json
import os
import sys


def calcular_checksum(ruta_archivo: str) -> str:
    h = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    if len(sys.argv) < 2:
        print("FAIL")
        sys.stderr.write("Uso: validar_checksum.py <ruta_archivo>\n")
        sys.exit(1)

    ruta_archivo = sys.argv[1]
    ruta_manifest = ruta_archivo + ".manifest.json"

    if not os.path.exists(ruta_archivo):
        print("FAIL")
        sys.stderr.write(f"Archivo no encontrado: {ruta_archivo}\n")
        sys.exit(1)

    if not os.path.exists(ruta_manifest):
        # Sin manifest no se puede validar integridad extremo a extremo.
        # Se marca como FAIL para que vaya a cuarentena y se revise
        # manualmente, en vez de asumir que está bien.
        print("FAIL")
        sys.stderr.write(f"Manifest no encontrado: {ruta_manifest}\n")
        sys.exit(1)

    try:
        with open(ruta_manifest, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print("FAIL")
        sys.stderr.write(f"Manifest inválido o ilegible: {e}\n")
        sys.exit(1)

    tamano_declarado = manifest.get("file_size")
    checksum_declarado = manifest.get("sha256")
    tamano_real = os.path.getsize(ruta_archivo)

    if tamano_declarado is None or checksum_declarado is None:
        print("FAIL")
        sys.stderr.write("Manifest incompleto: falta file_size o sha256\n")
        sys.exit(1)

    if tamano_real != tamano_declarado:
        print("FAIL")
        sys.stderr.write(
            f"Tamaño no coincide: esperado {tamano_declarado}, real {tamano_real}\n")
        sys.exit(1)

    checksum_real = calcular_checksum(ruta_archivo)
    if checksum_real != checksum_declarado:
        print("FAIL")
        sys.stderr.write(
            f"Checksum no coincide: esperado {checksum_declarado}, real {checksum_real}\n")
        sys.exit(1)

    print("OK")
    sys.exit(0)


if __name__ == "__main__":
    main()