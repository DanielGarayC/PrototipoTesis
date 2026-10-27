import argparse
import json
import os
import shutil
import socket
import sys
import time
from datetime import datetime, timezone

import psutil
import requests


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def cargar_config(ruta):
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f"No existe config: {ruta}")

    with open(ruta, "r", encoding="utf-8") as f:
        config = json.load(f)

    requeridos = [
        "project_id",
        "gateway_id",
        "heartbeat_url",
        "heartbeat_interval_seconds",
        "queue_directory"
    ]

    faltantes = [k for k in requeridos if k not in config]

    if faltantes:
        raise ValueError(
            f"Faltan campos en config.json: {faltantes}"
        )

    return config


def contar_backlog(carpeta):
    if not os.path.isdir(carpeta):
        return 0

    return sum(
        1
        for nombre in os.listdir(carpeta)
        if nombre.lower().endswith(".dxd")
    )


def obtener_ultimo_archivo(carpeta):
    if not os.path.isdir(carpeta):
        return None

    archivos = [
        os.path.join(carpeta, nombre)
        for nombre in os.listdir(carpeta)
        if nombre.lower().endswith(".dxd")
    ]

    if not archivos:
        return None

    ultimo = max(archivos, key=os.path.getmtime)

    return os.path.basename(ultimo)


def obtener_disco(carpeta):
    ruta = carpeta

    while not os.path.exists(ruta):
        padre = os.path.dirname(ruta)

        if padre == ruta:
            return None

        ruta = padre

    total, usado, libre = shutil.disk_usage(ruta)

    if total == 0:
        return None

    return round(usado * 100 / total, 2)


def construir_heartbeat(config):
    carpeta = config["queue_directory"]

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = obtener_disco(carpeta)
    backlog = contar_backlog(carpeta)
    last_file = obtener_ultimo_archivo(carpeta)

    return {
        "project_id": config["project_id"],
        "gateway_id": config["gateway_id"],

        "hostname": socket.gethostname(),

        "cpu_percent": cpu,
        "ram_percent": ram,
        "disk_used_percent": disk,

        "backlog": backlog,
        "last_file": last_file,

        "sent_at": utc_now()
    }

def enviar_heartbeat(config, payload):
    response = requests.post(
        config["heartbeat_url"],
        json=payload,
        timeout=10
    )

    response.raise_for_status()

    return response


def ejecutar_una_vez(config, dry_run=False):
    payload = construir_heartbeat(config)

    print("\nHeartbeat generado:")
    print(json.dumps(payload, indent=2))

    if dry_run:
        print("\nDRY RUN: no se envió nada.")
        return

    response = enviar_heartbeat(config, payload)

    print(
        f"\nHeartbeat enviado correctamente "
        f"(HTTP {response.status_code})"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        default="config.json"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Envía un heartbeat y termina"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera el heartbeat pero no lo envía"
    )

    args = parser.parse_args()

    try:
        config = cargar_config(args.config)

    except Exception as e:
        print(f"ERROR CONFIG: {e}", file=sys.stderr)
        return 1

    if args.once or args.dry_run:
        try:
            ejecutar_una_vez(
                config,
                dry_run=args.dry_run
            )
            return 0

        except Exception as e:
            print(f"ERROR HEARTBEAT: {e}", file=sys.stderr)
            return 2

    intervalo = config["heartbeat_interval_seconds"]

    print(
        f"Gateway Agent iniciado\n"
        f"Gateway: {config['gateway_id']}\n"
        f"Proyecto: {config['project_id']}\n"
        f"Intervalo: {intervalo} s\n"
    )

    while True:

        try:
            ejecutar_una_vez(config)

        except Exception as e:
            print(
                f"[{utc_now()}] Error enviando heartbeat: {e}",
                file=sys.stderr
            )

        time.sleep(intervalo)


if __name__ == "__main__":
    sys.exit(main())