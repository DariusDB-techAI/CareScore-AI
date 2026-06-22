from __future__ import annotations

import os
import socket

from .ngrok_helper import start_ngrok_tunnel


def get_app_host() -> str:
    return os.getenv("APP_HOST", "127.0.0.1").strip() or "127.0.0.1"


def get_app_port() -> int:
    return int(os.getenv("APP_PORT", "8001").strip() or "8001")


def get_app_debug() -> bool:
    return os.getenv("APP_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"}


def is_ngrok_enabled() -> bool:
    return os.getenv("NGROK_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def get_ngrok_authtoken() -> str:
    return os.getenv("NGROK_AUTHTOKEN", "").strip()


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def resolve_server_port(host: str, preferred_port: int, max_attempts: int = 20) -> int:
    if port_is_available(host, preferred_port):
        return preferred_port

    for port in range(preferred_port + 1, preferred_port + max_attempts + 1):
        if port_is_available(host, port):
            print(f"Cong {preferred_port} dang duoc su dung. App se chuyen sang cong {port}.")
            return port

    raise RuntimeError(f"Khong tim duoc cong trong khoang {preferred_port}-{preferred_port + max_attempts}.")


def start_public_tunnel(app_port: int) -> str | None:
    if not is_ngrok_enabled():
        return None
    return start_ngrok_tunnel(authtoken=get_ngrok_authtoken(), port=app_port)
