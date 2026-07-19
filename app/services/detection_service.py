import os
import uuid
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import detection_task, model
from app.models.detection_task import DetectionTask
from app.schemas.detection_task import DetectionTaskCreate, DetectionTaskUpdate

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}


def _is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def _boxes_to_detections(result) -> List[Dict[str, Any]]:
    detections = []
    boxes = result.boxes
    if boxes is None:
        return detections
    for box in boxes:
        detections.append({
            'class': int(box.cls.item()),
            'class_name': result.names[int(box.cls.item())],
            'confidence': float(box.conf.item()),
            'bbox': box.xyxy.tolist()[0],
        })
    return detections


def _save_image_results(results, output_dir: Path) -> None:
    import json
    for i, result in enumerate(results):
        result_path = output_dir / f"result_{i}.jpg"
        result.save(filename=str(result_path))
        json_path = output_dir / f"result_{i}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(_boxes_to_detections(result), f, indent=2)


def _run_video_detection(
    yolo_model,
    input_path: Path,
    output_dir: Path,
    conf: float,
    iou: float,
    task_id: str,
) -> Dict[str, Any]:
    import json

    logger.info(
        "Detection task %s: video file %s, starting frame-by-frame inference",
        task_id, input_path.name,
    )

    frame_count = 0
    total_detections = 0
    sample_frames: List[Dict[str, Any]] = []

    results = yolo_model.predict(
        source=str(input_path),
        conf=conf,
        iou=iou,
        stream=True,
        save=True,
        project=str(output_dir),
        name="annotated",
        exist_ok=True,
        verbose=False,
    )

    for result in results:
        frame_count += 1
        detections = _boxes_to_detections(result)
        total_detections += len(detections)

        if frame_count == 1 or frame_count % 100 == 0:
            logger.info(
                "Detection task %s: video progress %d frames processed, current frame objects=%d",
                task_id, frame_count, len(detections),
            )

        if frame_count == 1 or frame_count % 500 == 0:
            sample_frames.append({
                "frame_index": frame_count,
                "detections": detections,
                "count": len(detections),
            })

    annotated_videos = [
        p for p in output_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS and p.name != input_path.name
    ]
    annotated_videos.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    video_url = None
    if annotated_videos:
        video_rel_path = annotated_videos[0].relative_to(settings.STATIC_DIR)
        video_url = f"/static/{video_rel_path.as_posix()}"

    summary = {
        "media_type": "video",
        "frame_count": frame_count,
        "total_detections": total_detections,
        "sample_frames": sample_frames[:20],
        "video_url": video_url,
    }
    with open(output_dir / "video_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(
        "Detection task %s: video completed, frames=%d, total_objects=%d, output=%s",
        task_id, frame_count, total_detections, video_url or "none",
    )
    return summary

async def create_detection_task(
    db: Session,
    model_id: str,
    file: UploadFile,
    parameters: Dict[str, Any]
) -> DetectionTask:
    """
    Create a new detection task
    """
    # Check if model exists
    db_model = model.get(db, id=model_id)
    if not db_model:
        raise HTTPException(
            status_code=404,
            detail="Model not found",
        )

    # Generate unique ID for the detection task
    task_id = str(uuid.uuid4())

    # Create input and output directories
    input_dir = settings.UPLOADS_DIR / task_id
    output_dir = settings.RESULTS_DIR / task_id
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Save the uploaded file
    file_extension = Path(file.filename).suffix
    input_path = input_dir / f"input{file_extension}"
    with open(input_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Create detection task with all required fields
    obj_in_data = {
        "model_id": model_id,
        "parameters": parameters,
        "input_path": str(input_path),
        "output_path": str(output_dir),
        "status": "pending"
    }

    # 使用create_with_fields方法创建完整的记录
    db_task = detection_task.create_with_fields(db, obj_in=obj_in_data)

    # 在实际实现中，这将由后台任务处理
    # 现在，我们将执行实际的检测过程
    try:
        from ultralytics import YOLO

        model_path = db_model.path
        logger.info("Detection task %s: loading model %s for file %s", task_id, model_path, input_path)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        yolo_model = YOLO(model_path)

        conf = parameters.get('conf_thres', 0.25)
        iou = parameters.get('iou_thres', 0.45)
        is_video = _is_video_file(input_path)
        media_type = 'video' if is_video else 'image'
        logger.info(
            "Detection task %s: running inference media=%s conf=%s iou=%s",
            task_id, media_type, conf, iou,
        )

        if is_video:
            summary = _run_video_detection(yolo_model, input_path, output_dir, conf, iou, task_id)
            updated_parameters = {
                **parameters,
                "media_type": "video",
                "frame_count": summary["frame_count"],
                "total_detections": summary["total_detections"],
            }
        else:
            results = yolo_model(str(input_path), conf=conf, iou=iou, verbose=False)
            _save_image_results(results, output_dir)
            updated_parameters = {**parameters, "media_type": "image"}

        db_task = detection_task.update(db, db_obj=db_task, obj_in={
            "status": "completed",
            "parameters": updated_parameters,
        })
        logger.info("Detection task %s: completed successfully", task_id)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error("Detection task %s failed: %s", task_id, error_msg)
        logger.error(traceback.format_exc())
        db_task = detection_task.update(db, db_obj=db_task, obj_in={
            "status": "failed",
            "parameters": {**parameters, "error": error_msg}
        })
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {error_msg}",
        )

    return db_task

def get_detection_task(db: Session, task_id: str) -> DetectionTask:
    """
    Get a detection task by ID
    """
    db_task = detection_task.get(db, id=task_id)
    if not db_task:
        raise HTTPException(
            status_code=404,
            detail="Detection task not found",
        )
    return db_task

def get_detection_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[DetectionTask]:
    """
    Get all detection tasks
    """
    return detection_task.get_multi(db, skip=skip, limit=limit)

def get_detection_result(db: Session, task_id: str) -> Dict[str, Any]:
    """
    Get the detection result for a task
    """
    # 获取任务信息
    db_task = detection_task.get(db, id=task_id)
    if not db_task:
        raise HTTPException(
            status_code=404,
            detail="Detection task not found",
        )

    # 检查任务状态
    if db_task.status != "completed":
        return {
            "status": db_task.status,
            "message": f"Detection task is {db_task.status}",
            "results": None
        }

    # 获取输出目录
    output_dir = Path(db_task.output_path)
    if not output_dir.exists():
        return {
            "status": "error",
            "message": "Output directory not found",
            "results": None
        }

    # 视频结果
    summary_path = output_dir / "video_summary.json"
    if summary_path.exists():
        import json
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)

        results = [{
            "media_type": "video",
            "video_url": summary.get("video_url"),
            "frame_count": summary.get("frame_count", 0),
            "total_detections": summary.get("total_detections", 0),
            "sample_frames": summary.get("sample_frames", []),
            "count": summary.get("total_detections", 0),
        }]
        return {
            "status": "completed",
            "message": f"Video detection completed: {summary.get('frame_count', 0)} frames processed",
            "results": results,
            "input_image": str(Path(db_task.input_path).name),
            "media_type": "video",
        }

    # 图片结果
    result_images = list(output_dir.glob("result_*.jpg"))
    result_jsons = list(output_dir.glob("result_*.json"))

    if not result_images or not result_jsons:
        return {
            "status": "error",
            "message": "No detection results found",
            "results": None
        }

    # 构建结果对象
    results = []
    for i, (img_path, json_path) in enumerate(zip(sorted(result_images), sorted(result_jsons))):
        # 读取JSON结果
        try:
            import json
            with open(json_path, 'r') as f:
                detections = json.load(f)

            # 构建相对URL路径
            img_rel_path = img_path.relative_to(settings.STATIC_DIR)
            img_url = f"/static/{img_rel_path.as_posix()}"

            results.append({
                "image_url": img_url,
                "detections": detections,
                "count": len(detections)
            })
        except Exception as e:
            print(f"Error loading detection result {json_path}: {e}")

    return {
        "status": "completed",
        "message": "Detection completed successfully",
        "results": results,
        "input_image": str(Path(db_task.input_path).name)
    }
