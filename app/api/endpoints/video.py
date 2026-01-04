"""
视频处理 API 端点 - 提供视频处理和分析功能
"""
import os
import json
import uuid
import cv2
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.db.session import get_db
from app.core.config import settings
from app.services.opencv_service import opencv_service
from app.utils.file_utils import save_upload_file_temp, get_temp_file_path

router = APIRouter()

# 临时文件目录
TEMP_DIR = Path(settings.TEMP_DIR) / "video"
os.makedirs(TEMP_DIR, exist_ok=True)

# 处理后的视频目录
PROCESSED_DIR = Path(settings.STATIC_DIR) / "processed_videos"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 提取的帧目录
FRAMES_DIR = Path(settings.STATIC_DIR) / "video_frames"
os.makedirs(FRAMES_DIR, exist_ok=True)

# 视频数据集目录
VIDEO_DATASETS_DIR = Path(settings.STATIC_DIR) / "video_datasets"
os.makedirs(VIDEO_DATASETS_DIR, exist_ok=True)


@router.post("/info")
async def get_video_info(
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """获取视频信息"""
    temp_file = None
    try:
        # 保存上传的视频
        temp_file = await save_upload_file_temp(video, TEMP_DIR)
        
        # 获取视频信息
        video_info = opencv_service.get_video_info(temp_file)
        
        # 添加文件信息
        video_info["filename"] = video.filename
        video_info["size"] = os.path.getsize(temp_file)
        video_info["size_mb"] = round(video_info["size"] / (1024 * 1024), 2)
        
        return video_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频信息失败: {str(e)}")
    finally:
        # 清理临时文件
        if temp_file and os.path.exists(str(temp_file)):
            try:
                os.remove(str(temp_file))
            except:
                pass


@router.post("/extract-frames")
async def extract_frames(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    interval: float = Form(1.0),
    max_frames: Optional[int] = Form(None),
    resize_width: Optional[int] = Form(None),
    resize_height: Optional[int] = Form(None),
    start_time: float = Form(0.0),
    end_time: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    """从视频中提取帧"""
    temp_file = None
    try:
        # 保存上传的视频
        temp_file = await save_upload_file_temp(video, TEMP_DIR)
        
        # 创建输出目录
        extraction_id = str(uuid.uuid4())
        output_dir = FRAMES_DIR / extraction_id
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置调整大小参数
        resize = None
        if resize_width is not None and resize_height is not None:
            resize = (resize_width, resize_height)
        
        # 在后台任务中提取帧
        def extract_frames_task(temp_file_path: str):
            try:
                result = opencv_service.extract_frames(
                    video_path=temp_file_path,
                    output_dir=output_dir,
                    interval=interval,
                    max_frames=max_frames,
                    resize=resize,
                    start_time=start_time,
                    end_time=end_time
                )
                
                # 保存结果信息
                with open(output_dir / "info.json", "w") as f:
                    json.dump({
                        "video_filename": video.filename,
                        "extraction_id": extraction_id,
                        "parameters": {
                            "interval": interval,
                            "max_frames": max_frames,
                            "resize": resize,
                            "start_time": start_time,
                            "end_time": end_time
                        },
                        "result": result
                    }, f, indent=2)
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            except Exception as e:
                # 记录错误
                with open(output_dir / "error.txt", "w") as f:
                    f.write(f"提取帧失败: {str(e)}")
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        # 添加后台任务
        if temp_file:
            background_tasks.add_task(extract_frames_task, str(temp_file))
        
        # 返回任务信息
        return {
            "success": True,
            "message": "帧提取任务已启动",
            "extraction_id": extraction_id,
            "output_dir": str(output_dir)
        }
    except Exception as e:
        # 清理临时文件
        if temp_file and os.path.exists(str(temp_file)):
            try:
                os.remove(str(temp_file))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"启动帧提取任务失败: {str(e)}")


@router.get("/extraction-status/{extraction_id}")
async def get_extraction_status(extraction_id: str):
    """获取帧提取任务状态"""
    output_dir = FRAMES_DIR / extraction_id
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="提取任务不存在")
    
    # 检查是否有错误
    error_file = output_dir / "error.txt"
    if error_file.exists():
        with open(error_file, "r") as f:
            error_message = f.read()
        return {
            "status": "failed",
            "error": error_message
        }
    
    # 检查是否完成（优先检查info.json）
    info_file = output_dir / "info.json"
    if info_file.exists():
        try:
            with open(info_file, "r") as f:
                info = json.load(f)
            return {
                "status": "completed",
                "info": info
            }
        except json.JSONDecodeError:
            # 如果info.json文件损坏或为空，返回错误状态
            return {
                "status": "failed",
                "error": "结果文件损坏"
            }
    
    # 检查进度文件
    progress_file = output_dir / "progress.json"
    if progress_file.exists():
        try:
            with open(progress_file, "r") as f:
                # 检查文件是否为空
                content = f.read().strip()
                if not content:
                    # 如果文件为空，返回默认的处理中状态
                    return {
                        "status": "in_progress",
                        "progress": 0,
                        "extracted_frames": 0
                    }
                # 重置文件指针
                f.seek(0)
                progress_data = json.load(f)
            return progress_data
        except json.JSONDecodeError:
            # 如果progress.json文件损坏或为空，返回默认的处理中状态
            return {
                "status": "in_progress",
                "progress": 0,
                "extracted_frames": 0
            }
    
    # 任务仍在进行中
    return {
        "status": "in_progress"
    }


@router.delete("/frames/{extraction_id}")
async def delete_extracted_frames(extraction_id: str):
    """删除提取的帧缓存"""
    output_dir = FRAMES_DIR / extraction_id
    zip_file = FRAMES_DIR / f"frames_{extraction_id}.zip"
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="提取任务不存在")
    
    try:
        import shutil
        # 删除帧目录
        shutil.rmtree(output_dir)
        # 如果存在压缩包也删除
        if zip_file.exists():
            zip_file.unlink()
        return {"success": True, "message": "缓存已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除缓存失败: {str(e)}")


@router.get("/frames/{extraction_id}")
async def list_frames(extraction_id: str):
    """列出提取的关键帧"""
    # 支持两种格式：
    # 1. 直接是extraction_id（旧格式）
    # 2. scene_{task_id}_{scene_index}_{extraction_id}（新格式）
    frames_dir = FRAMES_DIR / extraction_id
    
    if not frames_dir.exists():
        # 尝试查找匹配的目录
        pattern = f"*_{extraction_id}"
        matching_dirs = list(FRAMES_DIR.glob(pattern))
        if matching_dirs:
            frames_dir = matching_dirs[0]
        else:
            raise HTTPException(status_code=404, detail="关键帧目录不存在")
    
    # 读取info.json
    info_file = frames_dir / "info.json"
    if info_file.exists():
        with open(info_file, "r") as f:
            info = json.load(f)
        
        # 获取实际的目录名用于URL
        actual_dir_name = frames_dir.name
        
        # 列出所有关键帧文件
        frame_files = []
        for frame_info in info.get("extracted_frames", []):
            frame_path = frames_dir / frame_info["filename"]
            if frame_path.exists():
                frame_files.append({
                    "filename": frame_info["filename"],
                    "time": frame_info["time"],
                    "frame_number": frame_info.get("frame_number"),
                    "url": f"/api/video/frames/{actual_dir_name}/{frame_info['filename']}"
                })
        
        return {
            "extraction_id": extraction_id,
            "scene_info": info.get("scene"),
            "frames": frame_files,
            "ready": True
        }
    else:
        # 如果没有info.json，列出目录中的所有图片文件
        actual_dir_name = frames_dir.name
        frame_files = []
        for file_path in frames_dir.glob("*.jpg"):
            frame_files.append({
                "filename": file_path.name,
                "url": f"/api/video/frames/{actual_dir_name}/{file_path.name}"
            })
        
        return {
            "extraction_id": extraction_id,
            "frames": frame_files,
            "ready": len(frame_files) > 0
        }


@router.post("/get-video-frame")
async def get_video_frame(
    video: UploadFile = File(...),
    frame_index: int = Form(...),
    db: Session = Depends(get_db)
):
    """从视频中获取指定帧的图片"""
    temp_file = None
    try:
        # 保存上传的视频
        temp_file = await save_upload_file_temp(video, TEMP_DIR)
        
        # 打开视频
        cap = cv2.VideoCapture(str(temp_file))
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="无法打开视频")
        
        # 获取视频总帧数
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_index < 0 or frame_index >= total_frames:
            cap.release()
            raise HTTPException(status_code=400, detail=f"帧索引无效，视频共有 {total_frames} 帧")
        
        # 设置到指定帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        
        # 读取帧
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise HTTPException(status_code=500, detail="无法读取视频帧")
        
        # 将帧转换为JPEG格式
        import io
        from fastapi.responses import StreamingResponse
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        frame_bytes = io.BytesIO(buffer.tobytes())
        
        # 清理临时文件
        try:
            os.remove(str(temp_file))
        except:
            pass
        
        return StreamingResponse(frame_bytes, media_type="image/jpeg")
    except Exception as e:
        # 清理临时文件
        if temp_file and os.path.exists(str(temp_file)):
            try:
                os.remove(str(temp_file))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"获取视频帧失败: {str(e)}")


@router.get("/frames/{extraction_id}/{filename}")
async def get_frame(extraction_id: str, filename: str, width: Optional[int] = None, height: Optional[int] = None):
    """获取提取的帧"""
    # 支持两种格式的目录名
    file_path = FRAMES_DIR / extraction_id / filename
    
    if not file_path.exists():
        # 尝试查找匹配的目录
        pattern = f"*_{extraction_id}"
        matching_dirs = list(FRAMES_DIR.glob(pattern))
        if matching_dirs:
            file_path = matching_dirs[0] / filename
        else:
            raise HTTPException(status_code=404, detail="帧不存在")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="帧不存在")
    
    # 如果指定了尺寸，则返回调整尺寸后的图片
    if width and height:
        try:
            from PIL import Image
            import io
            from fastapi.responses import StreamingResponse
            
            # 打开原始图片
            img = Image.open(file_path)
            
            # 调整尺寸
            img.thumbnail((width, height))
            
            # 将图片保存到内存中
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=85)
            img_io.seek(0)
            
            return StreamingResponse(img_io, media_type="image/jpeg")
        except Exception as e:
            # 如果处理失败，返回原始图片
            return FileResponse(path=file_path)
    
    return FileResponse(path=file_path)


@router.get("/download-frames/{extraction_id}")
async def download_frames(extraction_id: str):
    """下载所有提取的帧为ZIP文件"""
    output_dir = FRAMES_DIR / extraction_id
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="提取任务不存在")
    
    # 创建ZIP文件
    import zipfile
    import tempfile
    import shutil
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    try:
        # 在静态目录下创建ZIP文件
        zip_filename = f"frames_{extraction_id}.zip"
        zip_path = FRAMES_DIR / zip_filename
        
        # 如果ZIP文件已存在，先删除
        if zip_path.exists():
            zip_path.unlink()
        
        # 创建ZIP文件
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历所有帧文件
            for file_path in output_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    # 添加文件到ZIP，保持目录结构
                    zipf.write(file_path, file_path.name)
        
        # 返回ZIP文件
        # 注意：这里我们不使用background_tasks来删除文件，因为FileResponse需要文件存在
        # 文件将在下次下载时被覆盖删除
        return FileResponse(
            path=str(zip_path),
            media_type='application/zip',
            filename=zip_filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建ZIP文件失败: {str(e)}")


@router.post("/detect-scenes")
async def detect_scenes(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    threshold: float = Form(30.0),
    min_scene_length: int = Form(15),
    db: Session = Depends(get_db)
):
    """检测视频场景变化"""
    temp_file = None
    try:
        # 保存上传的视频
        temp_file = await save_upload_file_temp(video, TEMP_DIR)
        
        # 创建任务ID
        task_id = str(uuid.uuid4())
        output_dir = PROCESSED_DIR / f"scenes_{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # 在后台任务中检测场景
        def detect_scenes_task(temp_file_path: str):
            try:
                result = opencv_service.detect_scenes(
                    video_path=temp_file_path,
                    threshold=threshold,
                    min_scene_length=min_scene_length
                )
                
                # 保存结果信息
                with open(output_dir / "info.json", "w") as f:
                    json.dump({
                        "video_filename": video.filename,
                        "task_id": task_id,
                        "parameters": {
                            "threshold": threshold,
                            "min_scene_length": min_scene_length
                        },
                        "result": result
                    }, f, indent=2)
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            except Exception as e:
                # 记录错误
                with open(output_dir / "error.txt", "w") as f:
                    f.write(f"检测场景失败: {str(e)}")
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        # 添加后台任务
        if temp_file:
            background_tasks.add_task(detect_scenes_task, str(temp_file))
        
        # 返回任务信息
        return {
            "success": True,
            "message": "场景检测任务已启动",
            "task_id": task_id,
            "output_dir": str(output_dir)
        }
    except Exception as e:
        # 清理临时文件
        if temp_file and os.path.exists(str(temp_file)):
            try:
                os.remove(str(temp_file))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"启动场景检测任务失败: {str(e)}")


@router.get("/scene-detection-status/{task_id}")
async def get_scene_detection_status(task_id: str):
    """获取场景检测任务状态"""
    output_dir = PROCESSED_DIR / f"scenes_{task_id}"
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="场景检测任务不存在")
    
    # 检查是否有错误
    error_file = output_dir / "error.txt"
    if error_file.exists():
        with open(error_file, "r") as f:
            error_message = f.read()
        return {
            "status": "failed",
            "error": error_message
        }
    
    # 检查是否完成
    info_file = output_dir / "info.json"
    if info_file.exists():
        with open(info_file, "r") as f:
            info = json.load(f)
        return {
            "status": "completed",
            "info": info
        }
    
    # 任务仍在进行中
    return {
        "status": "in_progress"
    }


@router.get("/check-scene-keyframes/{task_id}/{scene_index}")
async def check_scene_keyframes(task_id: str, scene_index: int):
    """检查场景关键帧是否已提取"""
    # 查找该场景的关键帧目录（格式：scene_{task_id}_{scene_index}_*）
    pattern = f"scene_{task_id}_{scene_index}_*"
    matching_dirs = list(FRAMES_DIR.glob(pattern))
    
    if matching_dirs:
        # 找到已提取的关键帧，返回最新的
        latest_dir = max(matching_dirs, key=lambda p: p.stat().st_mtime)
        dir_name = latest_dir.name  # 完整的目录名
        
        # 检查关键帧文件
        info_file = latest_dir / "info.json"
        if info_file.exists():
            with open(info_file, "r") as f:
                info = json.load(f)
            
            frame_files = []
            for frame_info in info.get("extracted_frames", []):
                frame_path = latest_dir / frame_info["filename"]
                if frame_path.exists():
                    frame_files.append({
                        "filename": frame_info["filename"],
                        "time": frame_info["time"],
                        "frame_number": frame_info.get("frame_number"),
                        "url": f"/api/video/frames/{dir_name}/{frame_info['filename']}"
                    })
            
            if frame_files:
                return {
                    "exists": True,
                    "extraction_id": dir_name.split('_')[-1],  # 只返回extraction_id部分
                    "dir_name": dir_name,  # 完整的目录名用于访问
                    "frames": frame_files,
                    "scene_info": info.get("scene")
                }
    
    return {
        "exists": False
    }


@router.post("/extract-scene-keyframes")
async def extract_scene_keyframes(
    background_tasks: BackgroundTasks,
    task_id: str = Form(...),
    scene_index: int = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """从场景检测结果中提取关键帧"""
    temp_file = None
    try:
        # 保存上传的视频
        temp_file = await save_upload_file_temp(video, TEMP_DIR)
        
        # 读取场景检测结果
        output_dir = PROCESSED_DIR / f"scenes_{task_id}"
        info_file = output_dir / "info.json"
        
        if not info_file.exists():
            raise HTTPException(status_code=404, detail="场景检测结果不存在")
        
        with open(info_file, "r") as f:
            scene_info = json.load(f)
        
        if not scene_info.get("result") or not scene_info["result"].get("scenes"):
            raise HTTPException(status_code=404, detail="场景数据不存在")
        
        scenes = scene_info["result"]["scenes"]
        if scene_index < 0 or scene_index >= len(scenes):
            raise HTTPException(status_code=400, detail="场景索引无效")
        
        scene = scenes[scene_index]
        video_info = scene_info["result"]["video_info"]
        fps = video_info.get("fps", 30)
        
        # 创建输出目录（使用task_id和scene_index作为目录名的一部分，方便查找）
        extraction_id = str(uuid.uuid4())
        keyframes_dir = FRAMES_DIR / f"scene_{task_id}_{scene_index}_{extraction_id}"
        os.makedirs(keyframes_dir, exist_ok=True)
        
        # 在后台任务中提取关键帧
        def extract_keyframes_task(temp_file_path: str):
            try:
                # 从场景中提取关键帧（提取场景开始、中间、结束的帧）
                start_time = scene["start_time"]
                end_time = scene["end_time"]
                duration = scene["duration"]
                
                # 计算要提取的时间点：开始、1/3、2/3、结束
                time_points = [
                    start_time,
                    start_time + duration * 0.33,
                    start_time + duration * 0.67,
                    end_time
                ]
                
                # 打开视频
                cap = cv2.VideoCapture(str(temp_file_path))
                if not cap.isOpened():
                    raise ValueError(f"无法打开视频: {temp_file_path}")
                
                extracted_frames = []
                for i, time_point in enumerate(time_points):
                    # 设置视频位置
                    frame_number = int(time_point * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                    
                    # 读取帧
                    ret, frame = cap.read()
                    if ret:
                        # 保存帧
                        frame_filename = f"keyframe_{i+1}_{int(time_point)}s.jpg"
                        frame_path = keyframes_dir / frame_filename
                        cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        extracted_frames.append({
                            "filename": frame_filename,
                            "time": time_point,
                            "frame_number": frame_number
                        })
                
                cap.release()
                
                # 保存结果信息
                with open(keyframes_dir / "info.json", "w") as f:
                    json.dump({
                        "task_id": task_id,
                        "scene_index": scene_index,
                        "scene": scene,
                        "extraction_id": extraction_id,
                        "extracted_frames": extracted_frames,
                        "keyframes_dir": str(keyframes_dir)
                    }, f, indent=2)
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            except Exception as e:
                # 记录错误
                with open(keyframes_dir / "error.txt", "w") as f:
                    f.write(f"提取关键帧失败: {str(e)}")
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        # 添加后台任务
        if temp_file:
            background_tasks.add_task(extract_keyframes_task, str(temp_file))
        
        # 返回任务信息（包含extraction_id，但实际目录名包含task_id和scene_index）
        return {
            "success": True,
            "message": "关键帧提取任务已启动",
            "extraction_id": extraction_id,
            "task_id": task_id,
            "scene_index": scene_index,
            "keyframes_dir": str(keyframes_dir)
        }
    except Exception as e:
        # 清理临时文件
        if temp_file and os.path.exists(str(temp_file)):
            try:
                os.remove(str(temp_file))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"启动关键帧提取任务失败: {str(e)}")


@router.post("/detect-motion")
async def detect_motion(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    sensitivity: float = Form(20.0),
    blur_size: int = Form(21),
    min_area: int = Form(500),
    db: Session = Depends(get_db)
):
    """检测视频中的运动"""
    temp_file = None
    try:
        # 保存上传的视频
        temp_file = await save_upload_file_temp(video, TEMP_DIR)
        
        # 创建任务ID
        task_id = str(uuid.uuid4())
        output_dir = PROCESSED_DIR / f"motion_{task_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # 在后台任务中检测运动
        def detect_motion_task(temp_file_path: str):
            try:
                result = opencv_service.detect_motion(
                    video_path=temp_file_path,
                    sensitivity=sensitivity,
                    blur_size=blur_size,
                    min_area=min_area
                )
                
                # 保存结果信息
                with open(output_dir / "info.json", "w") as f:
                    json.dump({
                        "video_filename": video.filename,
                        "task_id": task_id,
                        "parameters": {
                            "sensitivity": sensitivity,
                            "blur_size": blur_size,
                            "min_area": min_area
                        },
                        "result": result
                    }, f, indent=2)
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            except Exception as e:
                # 记录错误
                with open(output_dir / "error.txt", "w") as f:
                    f.write(f"检测运动失败: {str(e)}")
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        # 添加后台任务
        if temp_file:
            background_tasks.add_task(detect_motion_task, str(temp_file))
        
        # 返回任务信息
        return {
            "success": True,
            "message": "运动检测任务已启动",
            "task_id": task_id,
            "output_dir": str(output_dir)
        }
    except Exception as e:
        # 清理临时文件
        if temp_file and os.path.exists(str(temp_file)):
            try:
                os.remove(str(temp_file))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"启动运动检测任务失败: {str(e)}")


@router.get("/motion-detection-status/{task_id}")
async def get_motion_detection_status(task_id: str):
    """获取运动检测任务状态"""
    output_dir = PROCESSED_DIR / f"motion_{task_id}"
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="运动检测任务不存在")
    
    # 检查是否有错误
    error_file = output_dir / "error.txt"
    if error_file.exists():
        with open(error_file, "r") as f:
            error_message = f.read()
        return {
            "status": "failed",
            "error": error_message
        }
    
    # 检查是否完成
    info_file = output_dir / "info.json"
    if info_file.exists():
        with open(info_file, "r") as f:
            info = json.load(f)
        return {
            "status": "completed",
            "info": info
        }
    
    # 任务仍在进行中
    return {
        "status": "in_progress"
    }


@router.post("/create-dataset")
async def create_dataset_from_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    dataset_name: str = Form(...),
    extraction_method: str = Form("interval"),
    interval: float = Form(1.0),
    scene_threshold: float = Form(30.0),
    motion_sensitivity: float = Form(20.0),
    max_frames: Optional[int] = Form(None),
    resize_width: Optional[int] = Form(None),
    resize_height: Optional[int] = Form(None),
    train_ratio: float = Form(0.7),
    val_ratio: float = Form(0.2),
    test_ratio: float = Form(0.1),
    db: Session = Depends(get_db)
):
    """从视频创建数据集"""
    temp_file = None
    try:
        # 验证分割比例
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.001:
            raise HTTPException(status_code=400, detail="分割比例总和必须为1.0")
        
        # 保存上传的视频
        temp_file = await save_upload_file_temp(video, TEMP_DIR)
        
        # 创建数据集目录
        dataset_id = str(uuid.uuid4())
        output_dir = VIDEO_DATASETS_DIR / dataset_id
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置调整大小参数
        resize = None
        if resize_width is not None and resize_height is not None:
            resize = (resize_width, resize_height)
        
        # 设置分割比例
        split_ratio = {
            "train": train_ratio,
            "val": val_ratio,
            "test": test_ratio
        }
        
        # 在后台任务中创建数据集
        def create_dataset_task(temp_file_path: str):
            try:
                result = opencv_service.create_dataset_from_video(
                    video_path=temp_file_path,
                    output_dir=output_dir,
                    extraction_method=extraction_method,
                    interval=interval,
                    scene_threshold=scene_threshold,
                    motion_sensitivity=motion_sensitivity,
                    max_frames=max_frames,
                    resize=resize,
                    split_ratio=split_ratio
                )
                
                # 保存结果信息
                with open(output_dir / "info.json", "w") as f:
                    json.dump({
                        "dataset_name": dataset_name,
                        "video_filename": video.filename,
                        "dataset_id": dataset_id,
                        "parameters": {
                            "extraction_method": extraction_method,
                            "interval": interval,
                            "scene_threshold": scene_threshold,
                            "motion_sensitivity": motion_sensitivity,
                            "max_frames": max_frames,
                            "resize": resize,
                            "split_ratio": split_ratio
                        },
                        "result": result
                    }, f, indent=2)
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                # 导入数据集到系统
                from app.services.dataset_service import import_external_dataset
                try:
                    # 导入数据集
                    db_dataset = import_external_dataset(
                        db=db,
                        name=dataset_name,
                        description=f"从视频 {video.filename} 创建的数据集",
                        directory_path=str(output_dir)
                    )
                    
                    # 更新信息文件
                    with open(output_dir / "info.json", "r") as f:
                        info = json.load(f)
                    
                    info["dataset_db_id"] = str(db_dataset.id)
                    info["import_status"] = "success"
                    
                    with open(output_dir / "info.json", "w") as f:
                        json.dump(info, f, indent=2)
                except Exception as e:
                    # 记录导入错误
                    with open(output_dir / "import_error.txt", "w") as f:
                        f.write(f"导入数据集失败: {str(e)}")
                    
                    # 更新信息文件
                    with open(output_dir / "info.json", "r") as f:
                        info = json.load(f)
                    
                    info["import_status"] = "failed"
                    info["import_error"] = str(e)
                    
                    with open(output_dir / "info.json", "w") as f:
                        json.dump(info, f, indent=2)
            except Exception as e:
                # 记录错误
                with open(output_dir / "error.txt", "w") as f:
                    f.write(f"创建数据集失败: {str(e)}")
                
                # 清理临时文件
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        # 添加后台任务
        if temp_file:
            background_tasks.add_task(create_dataset_task, str(temp_file))
        
        # 返回任务信息
        return {
            "success": True,
            "message": "数据集创建任务已启动",
            "dataset_id": dataset_id,
            "output_dir": str(output_dir)
        }
    except Exception as e:
        # 清理临时文件
        if temp_file and os.path.exists(str(temp_file)):
            try:
                os.remove(str(temp_file))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"启动数据集创建任务失败: {str(e)}")


@router.get("/dataset-creation-status/{dataset_id}")
async def get_dataset_creation_status(dataset_id: str):
    """获取数据集创建任务状态"""
    output_dir = VIDEO_DATASETS_DIR / dataset_id
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="数据集创建任务不存在")
    
    # 检查是否有错误
    error_file = output_dir / "error.txt"
    if error_file.exists():
        with open(error_file, "r") as f:
            error_message = f.read()
        return {
            "status": "failed",
            "error": error_message
        }
    
    # 检查是否完成
    info_file = output_dir / "info.json"
    if info_file.exists():
        with open(info_file, "r") as f:
            info = json.load(f)
        
        # 检查导入状态
        import_error_file = output_dir / "import_error.txt"
        if import_error_file.exists():
            with open(import_error_file, "r") as f:
                import_error = f.read()
            return {
                "status": "completed_with_import_error",
                "info": info,
                "import_error": import_error
            }
        
        # 检查是否有导入状态
        if "import_status" in info:
            if info["import_status"] == "success":
                return {
                    "status": "completed_and_imported",
                    "info": info
                }
            else:
                return {
                    "status": "completed_but_import_failed",
                    "info": info
                }
        
        return {
            "status": "completed",
            "info": info
        }
    
    # 任务仍在进行中
    return {
        "status": "in_progress"
    }
