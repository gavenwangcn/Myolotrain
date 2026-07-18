"""
NumPy 兼容补丁：YOLOv13(ultralytics) 仍调用已移除的 np.trapz。
NumPy 2.0+ 改为 np.trapezoid，在此做别名以兼容两边。
"""
import logging

logger = logging.getLogger(__name__)


def apply_patch() -> None:
    import numpy as np

    if hasattr(np, "trapz"):
        return
    if hasattr(np, "trapezoid"):
        np.trapz = np.trapezoid  # type: ignore[attr-defined]
        logger.info("Applied NumPy compat patch: np.trapz -> np.trapezoid")
    else:
        logger.warning("NumPy has neither trapz nor trapezoid; AP metrics may fail")
