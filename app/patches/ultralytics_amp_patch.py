"""
Ultralytics AMP 补丁：跳过 check_amp 对外网 yolov13n.pt / yolo11n.pt 的下载。

iMoonLab/yolov13 fork 在 AMP 自检时会下载 yolov13n.pt，离线环境可能失败或拖慢训练。
本补丁保留 GPU 黑名单检查，不再下载任何外部模型；训练照常进行。
"""
import logging
import re

logger = logging.getLogger(__name__)

_PATCH_FLAG = "_myolotrain_amp_patch_applied"


def _offline_safe_check_amp(model):
    import torch
    from ultralytics.utils import colorstr
    from ultralytics.utils import checks

    device = next(model.parameters()).device
    prefix = colorstr("AMP: ")
    warning_msg = (
        "If you experience zero-mAP or NaN losses you can disable AMP in training settings."
    )

    if device.type in {"cpu", "mps"}:
        return False

    pattern = re.compile(
        r"(nvidia|geforce|quadro|tesla).*?(1660|1650|1630|t400|t550|t600|t1000|t1200|t2000|k40m)",
        re.IGNORECASE,
    )
    gpu = torch.cuda.get_device_name(device)
    if bool(pattern.search(gpu)):
        checks.LOGGER.warning(
            f"{prefix}checks failed ❌. AMP training on {gpu} GPU may cause "
            f"NaN losses or zero-mAP results, so AMP will be disabled during training."
        )
        return False

    checks.LOGGER.info(
        f"{prefix}checks skipped (offline-safe, no external model download). {warning_msg}"
    )
    return True


def apply_patch() -> None:
    try:
        from ultralytics.utils import checks
    except ImportError:
        logger.warning("ultralytics not installed; AMP patch skipped")
        return

    if getattr(checks, _PATCH_FLAG, False):
        return

    checks.check_amp = _offline_safe_check_amp
    setattr(checks, _PATCH_FLAG, True)
    logger.info("Applied ultralytics AMP patch: skip external model download in check_amp")
