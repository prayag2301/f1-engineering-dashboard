from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import get_settings
from app.api.routes import router
from app.database import engine


def create_app():
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Evidence-backed F1 exterior reconstructions and reviewed weekly releases.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.API_V1_PREFIX)

    @app.middleware("http")
    async def privacy_headers(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(settings.API_V1_PREFIX + "/review"):
            response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health")
    def health():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "service": settings.APP_NAME}

    return app


app = create_app()
