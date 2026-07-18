"""应用与 Uvicorn 日志配置。"""
import logging
import os


def configure_app_logging() -> None:
    """初始化应用日志；默认不输出 HTTP 请求访问日志。"""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

    if os.getenv("UVICORN_ACCESS_LOG", "false").lower() != "true":
        logging.getLogger("uvicorn.access").disabled = True


def get_uvicorn_log_config() -> dict:
    """返回 uvicorn.run 的日志相关参数。"""
    access_log = os.getenv("UVICORN_ACCESS_LOG", "false").lower() == "true"
    log_level = os.getenv("UVICORN_LOG_LEVEL", "info").lower()
    return {
        "access_log": access_log,
        "log_level": log_level,
    }
