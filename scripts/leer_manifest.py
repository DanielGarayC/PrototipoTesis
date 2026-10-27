#!/usr/bin/env python3
"""PF-04B: leer el manifiesto lateral de un archivo de datos terminado.

Uso: python3 leer_manifest.py /ruta/archivo.dxd
Exito: JSON compacto en stdout y codigo 0.
Fallo: {} en stdout, motivo en stderr y codigo 1.
No modifica archivos, no lee STDIN y no recalcula el checksum del .dxd.
Comprueba estructura y tipos; no autoriza proyectos/gateways ni deduplica.
En NiFi: Output Destination Attribute=manifest_json, Max Attribute Length=8192.
Los limites son decisiones del prototipo, no resultados de rendimiento.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


FIELDS = {
    "project_id", "gateway_id", "file_id", "filename", "event_type",
    "file_creation_timestamp", "file_size", "sha256",
}
MAX_INPUT_BYTES = 65536
MAX_OUTPUT_CHARS = 4096


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Clave JSON repetida: " + key)
        result[key] = value
    return result


def read_manifest(data_path):
    path = Path(data_path)
    if not path.is_file():
        raise ValueError("Archivo de datos no encontrado: " + str(path))
    manifest_path = Path(str(path) + ".manifest.json")
    with manifest_path.open("rb") as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("El manifiesto supera el limite de 65536 bytes")
    manifest = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
    if not isinstance(manifest, dict):
        raise ValueError("El manifiesto debe ser un objeto JSON")
    if set(manifest) != FIELDS:
        missing = sorted(FIELDS - set(manifest))
        extra = sorted(set(manifest) - FIELDS)
        raise ValueError("Campos incompatibles; faltan=" + str(missing) + "; sobran=" + str(extra))
    for key in FIELDS - {"file_size"}:
        value = manifest[key]
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(key + " debe ser texto no vacio y sin espacios externos")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError(key + " contiene caracteres de control")
    if manifest["filename"] != path.name:
        raise ValueError("filename del manifiesto no coincide con el archivo de datos")
    if manifest["event_type"] not in ("NORMAL", "CRITICAL"):
        raise ValueError("event_type debe ser NORMAL o CRITICAL")
    if type(manifest["file_size"]) is not int or manifest["file_size"] < 0:
        raise ValueError("file_size debe ser un entero no negativo")
    if re.fullmatch(r"[0-9a-f]{64}", manifest["sha256"]) is None:
        raise ValueError("sha256 debe tener 64 caracteres hexadecimales en minusculas")
    timestamp = datetime.fromisoformat(manifest["file_creation_timestamp"].replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("file_creation_timestamp debe incluir zona horaria")
    result = json.dumps(manifest, ensure_ascii=True, separators=(",", ":"))
    if len(result) > MAX_OUTPUT_CHARS:
        raise ValueError("La salida JSON supera el limite de 4096 caracteres")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", help="Ruta del .dxd, no del manifiesto")
    args = parser.parse_args()
    try:
        result = read_manifest(args.archivo)
    except (OSError, ValueError, RecursionError) as error:
        print("{}")
        print("ERROR_MANIFEST: " + str(error), file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
