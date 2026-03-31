from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.database import engine, Base
from backend.api.routes import router as api_router

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="The most technically insightful open-source F1 engineering platform.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.on_event("startup")
    async def on_startup():
        Base.metadata.create_all(bind=engine)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": settings.APP_NAME}

    return app


app = create_app()
