# 设计：实时检测屏幕/窗口采集（A1）

日期：2026-07-18  
状态：已确认（待实现）  
范围：模型测试 → 实时目标检测

## 1. 背景与目标

平台「模型测试 / 实时检测」当前仅支持：摄像头、视频文件、RTSP/RTMP 流媒体。  
用户需要在 **Windows 宿主机浏览器** 中选择游戏或程序窗口作为检测源（类似 OBS 预览），将画面送给 **Docker 内 GPU** 做 YOLO 推理，用于验证模型对游戏画面的实时识别效果。

**成功标准：**

- 用户可选择屏幕或应用窗口作为视频源
- 预览区能实时看到采集画面（确认非黑屏、非空流）
- 在预览画面上叠加检测框，可调 conf/iou、选择模型
- 停止后释放采集轨道，不残留系统「正在共享屏幕」状态

## 2. 方案选择（A1）

采用浏览器 **Screen Capture API**（`navigator.mediaDevices.getDisplayMedia`）：

- 采集发生在 Windows 浏览器（非 Docker 内）
- 推理仍走现有后端检测 API
- 本阶段不做：进程枚举、静默绑 exe、本机采集助手（那是 A2）

## 3. 界面设计

位置：`模型测试` → `实时检测` 视频源单选项。

新增选项：

| 控件 | 说明 |
|------|------|
| 单选「屏幕/窗口」 | 与摄像头 / 视频文件 / 流媒体并列 |
| 简短说明文案 | 开始后弹出系统选择器；建议游戏使用窗口/无边框模式；独占全屏可能黑屏 |
| 最大边长（可选，默认 1280） | 抽帧前等比缩放，控制上传体积与延迟 |
| 目标推送 FPS（可选，默认 5） | 限制送检频率，避免打满异步检测接口 |

**预览（必须）：**

- 复用现有 `#video-element`：`video.srcObject = mediaStream`
- 选窗成功后立即显示实时画面（OBS 式预览）
- 检测框绘制在现有 `#detection-canvas` 上，与摄像头模式一致（预览 + 叠加画框）
- 若约 2～3 秒预览仍为黑屏：状态区提示改窗口模式或改选整个显示器

## 4. 架构与数据流

```
[Windows 浏览器]
  getDisplayMedia → MediaStream
       ↓
  #video-element（实时预览）
       ↓ 节流抽帧 + 可选缩放
  canvas.toBlob(JPEG)
       ↓
  POST 检测 API（见 §5）
       ↓
  解析 boxes → 画到 #detection-canvas
       ↓
[Docker YOLO / GPU]
```

组件边界：

| 单元 | 职责 | 依赖 |
|------|------|------|
| UI 源切换 | 显示/隐藏屏幕采集选项 | `index.html` + `video-processor.js` |
| 采集控制 | 申请/停止 `getDisplayMedia`，绑定/解绑 preview | MediaDevices API |
| 抽帧循环 | 与摄像头共用检测循环；按 FPS 节流 | 现有 `detectFrame` 模式 |
| 检测 API | 帧 → 检测结果 | 现有后端，优先低延迟路径 |

## 5. 检测 API 策略

现有摄像头路径：`POST /detection/` 创建异步任务再轮询结果，延迟偏高。

**本功能约定：**

- 屏幕/窗口采集默认走 **`POST /sync-detect`（或等价同步接口）**，降低实时延迟
- 请求字段与现有一致：`file`、`model_id`、`conf_thres`、`iou_thres`
- 若同步接口鉴权/CORS 与现网不一致，实现时对齐摄像头所用 `authenticatedFetch`
- 不在本阶段新建 WebSocket；若后续 FPS 仍不够再单独立项

## 6. 行为细节

**开始：**

1. 校验已选模型
2. 用户点击「开始检测」（用户手势）后调用 `getDisplayMedia({ video: true, audio: false })`
3. 绑定到 `#video-element`，`play()`，更新状态为「预览中/检测中」
4. 启动抽帧检测循环（节流）

**停止：**

1. 停止检测循环
2. `stream.getTracks().forEach(t => t.stop())`
3. `video.srcObject = null`，清空 canvas
4. 恢复按钮状态

**用户在系统 UI 点击「停止共享」：**

- 监听 `track.onended`，自动走停止逻辑并提示「屏幕共享已结束」

## 7. 错误处理

| 情况 | 处理 |
|------|------|
| 浏览器不支持 `getDisplayMedia` | 禁用该选项并提示换 Chrome/Edge |
| 用户取消选择器 | 不进入检测，提示已取消 |
| 权限拒绝 | 提示允许屏幕共享 |
| 预览黑屏 | 文案引导：窗口模式 / 采整屏 |
| 检测 API 失败 | 保留预览，状态显示错误，不强制断流（连续失败 N 次可停） |

## 8. 非目标（明确不做）

- 枚举 HWND / 按进程名自动附着（需 A2 本机助手）
- Docker 容器内抓宿主机窗口
- 对抗游戏反作弊或强制采集独占全屏
- 改动训练模块

## 9. 测试要点

- localhost:8013 下 Chrome/Edge：能选出窗口并看到预览
- 预览有画面后，检测框能叠加；停止后系统共享指示消失
- 切换到摄像头/文件源互不干扰
- 取消选择器、停止共享、API 失败三类路径可用

## 10. 主要改动文件（预期）

- `app/static/index.html` — 视频源选项与说明
- `app/static/js/video-processor.js` — `getDisplayMedia`、预览、节流、停止与 `onended`
- 视需要微调同步检测调用处（复用 `sync_detection`），无需新后端采集服务
