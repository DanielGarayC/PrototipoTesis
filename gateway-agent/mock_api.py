import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer


ESTADOS = {}


class Handler(BaseHTTPRequestHandler):

    def do_POST(self):

        if self.path != "/api/v1/gateways/heartbeat":
            self.send_response(404)
            self.end_headers()
            return

        longitud = int(
            self.headers.get("Content-Length", 0)
        )

        body = self.rfile.read(longitud)

        try:
            payload = json.loads(body)

        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        gateway_id = payload.get("gateway_id")

        if not gateway_id:
            self.send_response(400)
            self.end_headers()
            return

        payload["received_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

        ESTADOS[gateway_id] = payload

        with open(
            "gateway_state.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                ESTADOS,
                f,
                indent=2
            )

        print("\nHeartbeat recibido:")
        print(json.dumps(payload, indent=2))

        response = {
            "status": "ok",
            "gateway_id": gateway_id
        }

        data = json.dumps(response).encode()

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/json"
        )
        self.send_header(
            "Content-Length",
            str(len(data))
        )
        self.end_headers()

        self.wfile.write(data)


if __name__ == "__main__":

    servidor = HTTPServer(
        ("127.0.0.1", 8080),
        Handler
    )

    print(
        "API local escuchando en "
        "http://127.0.0.1:8080"
    )

    servidor.serve_forever()