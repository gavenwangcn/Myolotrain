import logging
import os

os.environ.setdefault("TZ", "Asia/Shanghai")

import uvicorn
from app.core.logging_config import configure_app_logging, get_uvicorn_log_config
from app.db.init_db import init_db
# from app.services.tensorboard_service import tensorboard_manager

configure_app_logging()
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialization completed successfully")

        # # Start TensorBoard service
        # logger.info("Starting TensorBoard service...")
        # if tensorboard_manager.start():
        #     logger.info(f"TensorBoard service started successfully at {tensorboard_manager.get_url()}")
        # else:
        #     logger.warning("Failed to start TensorBoard service")

        # Start server
        logger.info("Starting server...")
        reload = os.getenv("UVICORN_RELOAD", "true").lower() == "true"
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=reload,
            **get_uvicorn_log_config(),
        )
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
