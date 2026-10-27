""" SE UTILIZÓ ESTE SCRIPT PARA PF-01 hasta PF-03
generar_manifest.py
--------------------
Corre del lado del GATEWAY, antes de subir un archivo por SFTP.
Genera un manifest.json junto al archivo, con checksum calculado EN
ORIGEN (no al llegar al servidor) — esto es lo que permite validar
integridad extremo a extremo en 02_Validacion del flujo NiFi.

Mantiene un contador persistente de secuencia por gateway (guardado en
un pequeño archivo de estado), para poder detectar archivos faltantes
más adelante (si sequence_number salta de 1541 a 1543, falta el 1542).

USO:
    python generar_manifest.py --archivo C:\\datos\\DATA_20260802_120000.dxd \
        --project_id ANDAHUAYLILLAS --gateway_id GW-01 \
        --event_type periodic --expected_interval_seconds 3600

Genera:
    C:\\datos\\DATA_20260802_120000.dxd.manifest.json

Convención de event_type:
    - Si el archivo empieza con "EVT_" se marca automáticamente como
      "critical", salvo que se pase --event_type explícito.
"""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone


def calcular_checksum(ruta_archivo: str) -> str:
    h = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def siguiente_secuencia(ruta_estado: str, gateway_id: str) -> int:
    """Lee/actualiza un contador persistente por gateway, para poder
    detectar archivos faltantes comparando saltos en la secuencia."""
    estado = {}
    if os.path.exists(ruta_estado):
        try:
            with open(ruta_estado, "r", encoding="utf-8") as f:
                estado = json.load(f)
        except (json.JSONDecodeError, OSError):
            estado = {}

    actual = estado.get(gateway_id, 0) + 1
    estado[gateway_id] = actual

    with open(ruta_estado, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2)

    return actual


def main():
    parser = argparse.ArgumentParser(description="Genera manifest.json en origen para un archivo a enviar")
    parser.add_argument("--archivo", required=True, help="Ruta completa al archivo .dxd")
    parser.add_argument("--project_id", required=True)
    parser.add_argument("--gateway_id", required=True)
    parser.add_argument("--event_type", default=None,
                         help="'periodic' o 'critical'. Si se omite, se infiere del nombre "
                              "del archivo (EVT_ -> critical, si no -> periodic)")
    parser.add_argument("--expected_interval_seconds", type=int, default=3600)
    parser.add_argument("--estado_secuencia", default=None,
                         help="Ruta del archivo de estado del contador de secuencia. "
                              "Default: secuencia_gateways.json en la misma carpeta del script")
    args = parser.parse_args()

    if not os.path.exists(args.archivo):
        print(f"ERROR: no existe el archivo {args.archivo}")
        raise SystemExit(1)

    nombre_archivo = os.path.basename(args.archivo)

    if args.event_type is None:
        event_type = "critical" if nombre_archivo.startswith("EVT_") else "periodic"
    else:
        event_type = args.event_type

    if args.estado_secuencia is None:
        carpeta_script = os.path.dirname(os.path.abspath(__file__))
        args.estado_secuencia = os.path.join(carpeta_script, "secuencia_gateways.json")

    sequence_number = siguiente_secuencia(args.estado_secuencia, args.gateway_id)

    capture_timestamp = datetime.now().astimezone().isoformat()
    file_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}_{args.gateway_id}"

    manifest = {
        "project_id": args.project_id,
        "gateway_id": args.gateway_id,
        "file_id": file_id,
        "filename": nombre_archivo,
        "event_type": event_type,
        "sequence_number": sequence_number,
        "capture_timestamp": capture_timestamp,
        "file_size": os.path.getsize(args.archivo),
        "sha256": calcular_checksum(args.archivo),
        "expected_interval_seconds": args.expected_interval_seconds,
    }

    ruta_manifest = args.archivo + ".manifest.json"
    with open(ruta_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest generado: {ruta_manifest}")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()