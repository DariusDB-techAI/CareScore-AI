from __future__ import annotations

from typing import Any


def start_ngrok_tunnel(*, authtoken: str, port: int) -> str | None:
    if not authtoken.strip():
        raise RuntimeError("NGROK_ENABLED=1 nhung chua co NGROK_AUTHTOKEN trong environment.")

    try:
        from pyngrok import ngrok
        from pyngrok.exception import PyngrokError
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            'Chua cai pyngrok. Hay chay "pip install pyngrok" hoac "pip install -r requirements.txt".'
        ) from exc

    try:
        ngrok.set_auth_token(authtoken)
        tunnel: Any = ngrok.connect(addr=port, proto="http")
        return getattr(tunnel, "public_url", None)
    except PyngrokError as exc:
        raise RuntimeError(
            "Khong mo duoc ngrok tunnel. Token hien tai khong hop le hoac chua phai ngrok authtoken."
        ) from exc
