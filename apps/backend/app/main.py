"""ReunionAI FastAPI application factory and entrypoint."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build the FastAPI application with the health endpoint registered."""
    app = FastAPI(title="ReunionAI API", version="0.1.0")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
