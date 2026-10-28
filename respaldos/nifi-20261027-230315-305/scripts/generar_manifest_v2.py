#!/usr/bin/env python3
"""Generador de manifiestos para el prototipo (Python 3.8+; sin dependencias).

Ejecutar sobre un archivo terminado e inmutable, antes de enviarlo.
El timestamp es el primer registro para gestion, NO el instante de adquisicion.
Conservar el archivo y su manifiesto juntos durante pendientes y reintentos.
Si ya existe un manifiesto compatible, se comprueba y se reutiliza sin escribirlo.
Un manifiesto antiguo, incompleto o incompatible produce error; no se reemplaza.

El bloqueo evita dos generadores cooperantes simultaneos para la misma ruta.
Si el proceso termina abruptamente puede quedar .manifest.json.lock: revisar que
no haya otro generador activo antes de retirarlo manualmente. La escritura
temporal protege la publicacion local del JSON, no coordina aun la recepcion SFTP.
Codigos: 0 creado/reutilizado; 1 fallo operativo; 2 argumentos incorrectos.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4


FIELDS = {
    "project_id", "gateway_id", "file_id", "filename", "event_type",
    "file_creation_timestamp", "file_size", "sha256",
}


def identifier(value):
    if not value or value != value.strip():
        raise argparse.ArgumentTypeError("Identificador vacio o con espacios externos")
    return value


def fingerprint(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size, after.st_mtime_ns, after.st_ino
    ):
        raise ValueError("El archivo cambio mientras se calculaba SHA-256")
    return after.st_size, digest.hexdigest()


def check_existing(manifest, expected):
    if not isinstance(manifest, dict) or set(manifest) != FIELDS:
        raise ValueError("Manifiesto existente incompatible con los ocho campos actuales")
    if type(manifest["file_size"]) is not int:
        raise ValueError("file_size debe ser un entero")
    for key, value in expected.items():
        if manifest[key] != value:
            raise ValueError("El manifiesto existente no coincide en: " + key)
    if not isinstance(manifest["file_id"], str):
        raise ValueError("file_id debe ser texto")
    if UUID(manifest["file_id"]).version != 4:
        raise ValueError("Esta version del generador espera un file_id UUID v4")
    timestamp = manifest["file_creation_timestamp"]
    if not isinstance(timestamp, str):
        raise ValueError("file_creation_timestamp debe ser texto")
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("file_creation_timestamp debe incluir zona horaria")


def generate(args):
    path = Path(args.archivo).expanduser().absolute()
    if not path.is_file():
        raise ValueError("No existe un archivo regular en: " + str(path))
    target = Path(str(path) + ".manifest.json")
    lock = Path(str(target) + ".lock")
    try:
        lock_fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("Existe un bloqueo; revise si hay otro generador activo: " + str(lock))
    os.close(lock_fd)
    temporary = None
    try:
        first_registered = datetime.now(timezone.utc).isoformat()
        size, digest = fingerprint(path)
        expected = {
            "project_id": args.project_id,
            "gateway_id": args.gateway_id,
            "filename": path.name,
            "event_type": args.event_type,
            "file_size": size,
            "sha256": digest,
        }
        if target.exists():
            with target.open("r", encoding="utf-8-sig") as source:
                manifest = json.load(source)
            check_existing(manifest, expected)
            return "REUTILIZADO", target, manifest

        manifest = {
            "project_id": args.project_id,
            "gateway_id": args.gateway_id,
            "file_id": str(uuid4()),
            "filename": path.name,
            "event_type": args.event_type,
            "file_creation_timestamp": first_registered,
            "file_size": size,
            "sha256": digest,
        }
        # Escribir en la misma carpeta y cerrar antes de publicar el JSON final.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(target.parent),
            prefix=target.name + ".", suffix=".tmp", delete=False
        ) as output:
            temporary = Path(output.name)
            json.dump(manifest, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        if target.exists():
            raise ValueError("Aparecio un manifiesto durante la generacion; no se reemplaza")
        os.replace(str(temporary), str(target))
        temporary = None
        return "CREADO", target, manifest
    finally:
        try:
            if temporary is not None:
                temporary.unlink()
        finally:
            lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", required=True)
    parser.add_argument("--project_id", required=True, type=identifier)
    parser.add_argument("--gateway_id", required=True, type=identifier)
    parser.add_argument("--event_type", required=True, choices=("NORMAL", "CRITICAL"))
    args = parser.parse_args()
    try:
        status, path, manifest = generate(args)
    except (OSError, ValueError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    print(status + ": " + str(path))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
