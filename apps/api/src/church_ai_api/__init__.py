"""Great Church AI API package."""

__version__ = "0.2.0"

__all__ = ["__version__", "create_app"]


def __getattr__(name: str):  # pragma: no cover - thin lazy re-export
    if name == "create_app":
        from church_ai_api.main import create_app

        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
