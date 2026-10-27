"""Consulta local de pertenencia y habilitación. No autentica dispositivos."""
import logging
import os
from typing import Annotated

import pymysql
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

log = logging.getLogger("central.catalogo")
app = FastAPI(title="Catálogo local LIP", version="0.1.0")
Identifier = Annotated[str, Query(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]


def connect_db():
    """Una conexión por consulta; se cierra incluso si ocurre una excepción."""
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mysql"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "tesis_app"),
        password=os.environ["DB_PASSWORD"],
        database=os.environ.get("DB_NAME", "tesis_lip"),
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        autocommit=True, connect_timeout=3, read_timeout=5, write_timeout=5,
    )


def query_one(sql, params=()):
    with connect_db() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()


def unavailable(exc):
    # No registrar contraseña, cadena de conexión ni mensaje SQL completo.
    log.error("catalogo_no_disponible tipo=%s", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"error": "CATALOG_UNAVAILABLE", "retryable": True},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/health")
def health():
    try:
        query_one("SELECT 1 AS ok")
    except (pymysql.MySQLError, OSError, KeyError, ValueError) as exc:
        return unavailable(exc)
    return {"status": "ok", "database": "ok"}


def decide(row, project_id, gateway_id):
    reason = "OK"
    if row is None:
        reason = "UNKNOWN_GATEWAY"
    elif row["project_id"] != project_id:
        reason = "PROJECT_MISMATCH"
    elif row["project_enabled"] != 1:
        reason = "PROJECT_DISABLED"
    elif row["gateway_enabled"] != 1:
        reason = "GATEWAY_DISABLED"
    return {"allowed": reason == "OK", "reason": reason,
            "project_id": project_id, "gateway_id": gateway_id}


@app.get("/v1/origen")
def check_origin(project_id: Identifier, gateway_id: Identifier):
    try:
        row = query_one(
            """SELECT g.project_id, g.enabled AS gateway_enabled,
                      p.enabled AS project_enabled
               FROM gateways AS g
               JOIN projects AS p ON p.project_id = g.project_id
               WHERE g.gateway_id = %s""", (gateway_id,),
        )
    except (pymysql.MySQLError, OSError, KeyError, ValueError) as exc:
        return unavailable(exc)
    return JSONResponse(decide(row, project_id, gateway_id),
                        headers={"Cache-Control": "no-store"})
