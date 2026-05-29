import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# Заглушаем шум от SQLAlchemy и uvicorn
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import auth_backend, fastapi_users
from app.core.config import settings
from app.api.chat import router as chat_router
from app.api.day_tasks import router as day_tasks_router
from app.api.marks import router as marks_router
from app.api.pile import router as pile_router
from app.api.review import router as review_router
from app.api.settings import router as settings_router
from app.api.themes import router as themes_router
from app.api.week_tasks import router as week_tasks_router
from app.api.weeks import router as weeks_router
from app.api.years import router as years_router
from app.schemas.user import UserCreate, UserRead, UserUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Календарь 52", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/api/v1/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/v1/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/v1/users",
    tags=["users"],
)
app.include_router(chat_router)
app.include_router(years_router)
app.include_router(weeks_router)
app.include_router(marks_router)
app.include_router(week_tasks_router)
app.include_router(day_tasks_router)
app.include_router(themes_router)
app.include_router(pile_router)
app.include_router(review_router)
app.include_router(settings_router)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
