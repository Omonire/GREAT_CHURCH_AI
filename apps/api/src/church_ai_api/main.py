from flask import Flask, jsonify

from church_ai_api.api.ws import socket
from church_ai_api.config import get_settings

settings = get_settings()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    socket.init_app(app)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=settings.api_host, port=settings.api_port)
