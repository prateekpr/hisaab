# app/main.py
import logging
import time
from fastapi import FastAPI
from app import models, database
from app.auth import router as auth_router
from app.routers import users as users_router
from app.routers import expenses as expenses_router
from app.routers import groups as groups_router
from app.routers import settlements as settlements_router

# ---------------- Logging Configuration ---------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)

# ---------------- FastAPI Initialization ---------------- #
app = FastAPI()

# Register routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router.router, prefix="/users", tags=["users"])
app.include_router(expenses_router.router, prefix="/expenses", tags=["expenses"])
app.include_router(groups_router.router)
app.include_router(settlements_router.router, prefix="/settlements", tags=["settlements"])

# ---------------- Startup Tasks ---------------- #
try:
    models.Base.metadata.create_all(bind=database.engine)
    logger.info("✅ Tables created successfully!")
    logger.info("🚀 Application startup complete!")
except Exception as e:
    logger.critical(f"Application failed to start: {e}")
    raise
