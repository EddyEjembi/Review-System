"""Application entry point.

Wires together the FastAPI app, routers, logging, and configuration.
Run locally with: `uvicorn app.main:app --reload`.
"""

from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.routes import businesses, health, new_user, reviews, users
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Build and return the FastAPI application instance."""
    load_dotenv()
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Persona-driven review generation system.",
    )

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(new_user.router, prefix="/new-user", tags=["new-user"])
    app.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
    app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=9000, reload=True)
