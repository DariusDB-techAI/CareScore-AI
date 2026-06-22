from __future__ import annotations

from dotenv import load_dotenv
from flask import Flask
from flask_sock import Sock

from services.hub_config import get_app_debug, get_app_host, get_app_port, is_ngrok_enabled, resolve_server_port, start_public_tunnel
from services.hub_conversations import build_memory_service
from services.hub_routes import register_routes
from services.hub_ws import register_ws
from services.paths import PROJECT_ROOT


PROJECT_DIR = PROJECT_ROOT
load_dotenv(PROJECT_DIR / ".env")


def create_app() -> Flask:
    flask_app = Flask(__name__)
    websocket = Sock(flask_app)
    memory_service = build_memory_service(PROJECT_DIR)
    register_routes(flask_app, memory_service)
    register_ws(websocket, memory_service)
    return flask_app


app = create_app()


if __name__ == "__main__":
    app_host = get_app_host()
    app_port = resolve_server_port(app_host, get_app_port())
    app_debug = get_app_debug()

    if is_ngrok_enabled():
        try:
            app_public_url = start_public_tunnel(app_port)
            if app_public_url:
                print(f"Ngrok App URL: {app_public_url}")
                print(f"Cho may khac dung URL nay de vao app: {app_public_url}")
        except RuntimeError as exc:
            print(f"Canh bao: {exc}")
            print(f"App se tiep tuc chay local tai http://{app_host}:{app_port}")

    app.run(
        host=app_host,
        port=app_port,
        debug=app_debug,
        use_reloader=False if is_ngrok_enabled() else app_debug,
    )
