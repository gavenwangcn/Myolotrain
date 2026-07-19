#!/usr/bin/env python3
"""Docker 构建时 patch ultralytics，去掉 AMP 自检的外网模型下载。"""
from pathlib import Path


MARKER = "Myolotrain: offline-safe AMP check"


def patch_checks(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"Already patched: {path}")
        return

    replacements = [
        '        assert amp_allclose(YOLO("yolov13n.pt"), im)',
        '        assert amp_allclose(YOLO("yolo11n.pt"), im)',
    ]
    new_block = (
        f"        # {MARKER}\n"
        '        LOGGER.info(f"{prefix}checks skipped (offline-safe, no external model download). {warning_msg}")'
    )

    patched = False
    for old in replacements:
        if old in text:
            text = text.replace(old, new_block, 1)
            patched = True
            break

    if not patched:
        print(f"WARNING: AMP check download line not found in {path}")
        return

    path.write_text(text, encoding="utf-8")
    print(f"Patched {path}")


def main() -> None:
    import ultralytics

    checks_path = Path(ultralytics.__file__).resolve().parent / "utils" / "checks.py"
    patch_checks(checks_path)


if __name__ == "__main__":
    main()
