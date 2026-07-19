// 检测功能模块
class DetectionManager {
    constructor() {
        this.stream = null;
        this.isStreamDetecting = false;
        this.streamAnimationId = null;
        this.syncDetectInFlight = false;
        this.lastDetectRequestTime = 0;
        this.streamFrameIndex = 0;
        this.captureCanvas = null;
    }

    loadDetectionForm() {
        fetch(`${API_URL}/models/`)
            .then(response => response.json())
            .then(models => {
                const select = document.getElementById('model-select');
                if (!select) return;
                select.innerHTML = '<option value="">请选择模型</option>';
                models.forEach(model => {
                    if (model.task === 'detect') {
                        const option = document.createElement('option');
                        option.value = model.id;
                        option.textContent = `${model.name} (${model.type})`;
                        select.appendChild(option);
                    }
                });
            })
            .catch(error => {
                console.error('Error loading model options:', error);
            });
    }

    bindDetectionEvents() {
        const form = document.getElementById('detection-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const source = document.querySelector('input[name="detection-source"]:checked')?.value || 'file';
                if (source === 'display') {
                    this.startStreamDetection();
                } else {
                    this.submitDetection();
                }
            });
        }

        const confThreshold = document.getElementById('conf-threshold');
        const confValue = document.getElementById('conf-value');
        if (confThreshold && confValue) {
            confThreshold.addEventListener('input', function() {
                confValue.textContent = this.value;
            });
        }

        const iouThreshold = document.getElementById('iou-threshold');
        const iouValue = document.getElementById('iou-value');
        if (iouThreshold && iouValue) {
            iouThreshold.addEventListener('input', function() {
                iouValue.textContent = this.value;
            });
        }

        const sourceFile = document.getElementById('detection-source-file');
        const sourceDisplay = document.getElementById('detection-source-display');
        const filePanel = document.getElementById('detection-file-panel');
        const displayPanel = document.getElementById('detection-display-panel');

        const updateSourcePanels = () => {
            const value = document.querySelector('input[name="detection-source"]:checked')?.value || 'file';
            if (filePanel) filePanel.style.display = value === 'file' ? 'block' : 'none';
            if (displayPanel) displayPanel.style.display = value === 'display' ? 'block' : 'none';
        };

        if (sourceDisplay && !this.isDisplayCaptureSupported()) {
            sourceDisplay.disabled = true;
            const label = document.querySelector('label[for="detection-source-display"]');
            if (label) label.title = '请使用 Chrome 或 Edge，并通过 localhost 访问';
        }

        [sourceFile, sourceDisplay].filter(Boolean).forEach(radio => {
            radio.addEventListener('change', updateSourcePanels);
        });
        updateSourcePanels();

        const maxDim = document.getElementById('detection-display-max-dimension');
        const maxDimValue = document.getElementById('detection-display-max-dimension-value');
        if (maxDim && maxDimValue) {
            maxDim.addEventListener('input', () => { maxDimValue.textContent = maxDim.value; });
        }
        const targetFps = document.getElementById('detection-display-target-fps');
        const targetFpsValue = document.getElementById('detection-display-target-fps-value');
        if (targetFps && targetFpsValue) {
            targetFps.addEventListener('input', () => { targetFpsValue.textContent = targetFps.value; });
        }

        const pickBtn = document.getElementById('detection-pick-display-btn');
        if (pickBtn) {
            pickBtn.addEventListener('click', () => this.pickDisplaySource());
        }

        const stopBtn = document.getElementById('detection-stop-stream-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopStreamDetection());
        }
    }

    isDisplayCaptureSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
    }

    releaseDisplayStream() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    updateDisplaySourceLabel(mediaStream) {
        const labelEl = document.getElementById('detection-display-source-label');
        if (!labelEl) return;
        const track = mediaStream?.getVideoTracks?.()[0];
        labelEl.textContent = track?.label ? `已选择: ${track.label}` : (track ? '已选择共享源' : '尚未选择共享源');
    }

    setStreamStatus(html) {
        const el = document.getElementById('detection-stream-status');
        if (el) el.innerHTML = html;
    }

    pickDisplaySource() {
        if (!this.isDisplayCaptureSupported()) {
            alert('当前浏览器不支持屏幕/窗口采集，请使用 Chrome 或 Edge，并通过 localhost 访问。');
            return;
        }

        this.releaseDisplayStream();
        const videoElement = document.getElementById('detection-preview-video');

        navigator.mediaDevices.getDisplayMedia({ video: true, audio: false })
            .then(mediaStream => {
                this.stream = mediaStream;
                this.updateDisplaySourceLabel(mediaStream);

                mediaStream.getVideoTracks().forEach(track => {
                    track.onended = () => {
                        this.updateDisplaySourceLabel(null);
                        if (this.isStreamDetecting) {
                            this.stopStreamDetection();
                            alert('屏幕共享已结束');
                        } else {
                            this.releaseDisplayStream();
                            if (videoElement) {
                                videoElement.srcObject = null;
                                videoElement.style.display = 'none';
                            }
                        }
                    };
                });

                if (videoElement) {
                    videoElement.srcObject = mediaStream;
                    videoElement.style.display = 'block';
                    return videoElement.play();
                }
            })
            .then(() => {
                this.setStreamStatus('<span class="badge bg-success">已选择共享源，可点击「开始检测」</span>');
            })
            .catch(error => {
                let message = error.message || String(error);
                if (error.name === 'NotAllowedError') {
                    message = '已取消或拒绝屏幕共享';
                }
                alert('屏幕/窗口选择失败: ' + message);
                this.setStreamStatus(`<span class="badge bg-danger">${message}</span>`);
            });
    }

    captureFrameForDetection(videoElement, maxDimension) {
        if (!this.captureCanvas) {
            this.captureCanvas = document.createElement('canvas');
        }
        let sw = videoElement.videoWidth;
        let sh = videoElement.videoHeight;
        if (!sw || !sh) {
            return Promise.reject(new Error('视频尚未就绪'));
        }
        if (maxDimension && Math.max(sw, sh) > maxDimension) {
            const scale = maxDimension / Math.max(sw, sh);
            sw = Math.round(sw * scale);
            sh = Math.round(sh * scale);
        }
        this.captureCanvas.width = sw;
        this.captureCanvas.height = sh;
        const captureCtx = this.captureCanvas.getContext('2d');
        captureCtx.drawImage(videoElement, 0, 0, sw, sh);
        return new Promise((resolve, reject) => {
            this.captureCanvas.toBlob(blob => {
                if (!blob) {
                    reject(new Error('无法捕获当前帧'));
                    return;
                }
                resolve({
                    blob,
                    sourceWidth: sw,
                    sourceHeight: sh,
                    nativeWidth: videoElement.videoWidth,
                    nativeHeight: videoElement.videoHeight,
                    canvas: this.captureCanvas,
                });
            }, 'image/jpeg', 0.85);
        });
    }

    mapDetectionCoordinates(bbox, detectWidth, detectHeight, nativeWidth, nativeHeight) {
        if (!Array.isArray(bbox) || bbox.length < 4) {
            return {};
        }
        const [x1, y1, x2, y2] = bbox;
        const scaleX = nativeWidth / detectWidth;
        const scaleY = nativeHeight / detectHeight;
        const wx1 = Math.round(x1 * scaleX);
        const wy1 = Math.round(y1 * scaleY);
        const wx2 = Math.round(x2 * scaleX);
        const wy2 = Math.round(y2 * scaleY);
        const centerX = Math.round((wx1 + wx2) / 2);
        const centerY = Math.round((wy1 + wy2) / 2);

        const screenOffsetX = parseInt(document.getElementById('detection-window-screen-x')?.value || '0', 10) || 0;
        const screenOffsetY = parseInt(document.getElementById('detection-window-screen-y')?.value || '0', 10) || 0;

        return {
            bbox_detect: bbox.map(v => Math.round(v)),
            bbox_window: [wx1, wy1, wx2, wy2],
            center_window: [centerX, centerY],
            center_screen: [screenOffsetX + centerX, screenOffsetY + centerY],
            scale_to_window: [Number(scaleX.toFixed(4)), Number(scaleY.toFixed(4))],
        };
    }

    enrichDetectionsWithWindowCoords(detections, detectWidth, detectHeight, nativeWidth, nativeHeight) {
        return detections.map(detection => ({
            ...detection,
            ...this.mapDetectionCoordinates(
                detection.bbox,
                detectWidth,
                detectHeight,
                nativeWidth,
                nativeHeight
            ),
        }));
    }

    scaleDetectionsForCanvas(detections, sourceWidth, sourceHeight, canvasWidth, canvasHeight) {
        if (!sourceWidth || !sourceHeight || sourceWidth === canvasWidth && sourceHeight === canvasHeight) {
            return detections;
        }
        const scaleX = canvasWidth / sourceWidth;
        const scaleY = canvasHeight / sourceHeight;
        return detections.map(det => {
            if (!Array.isArray(det.bbox) || det.bbox.length < 4) return det;
            const [x1, y1, x2, y2] = det.bbox;
            return {
                ...det,
                bbox: [x1 * scaleX, y1 * scaleY, x2 * scaleX, y2 * scaleY],
            };
        });
    }

    renderAnnotatedImageDataUrl(sourceCanvas, detections) {
        const canvas = document.createElement('canvas');
        canvas.width = sourceCanvas.width;
        canvas.height = sourceCanvas.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(sourceCanvas, 0, 0);

        detections.forEach(detection => {
            if (!Array.isArray(detection.bbox) || detection.bbox.length < 4) return;
            const [x1, y1, x2, y2] = detection.bbox;
            const className = detection.class_name || detection.class || 'Unknown';
            const confidence = detection.confidence ?? 0;
            const hue = (String(className).length * 5) % 360;
            ctx.strokeStyle = `hsl(${hue}, 100%, 50%)`;
            ctx.lineWidth = 2;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
            const label = `${className} ${(confidence * 100).toFixed(1)}%`;
            ctx.fillStyle = `hsl(${hue}, 100%, 50%)`;
            const textWidth = ctx.measureText(label).width;
            ctx.fillRect(x1, Math.max(0, y1 - 20), textWidth + 10, 20);
            ctx.fillStyle = '#fff';
            ctx.font = '14px Arial';
            ctx.fillText(label, x1 + 5, Math.max(14, y1 - 5));
        });

        return canvas.toDataURL('image/jpeg', 0.9);
    }

    buildDetectionResultCard(title, imageDataUrl, detections, options = {}) {
        const showWindowCoords = !!options.showWindowCoords;
        const coordinateMeta = options.coordinateMeta || null;

        let rowsHtml = '';
        detections.forEach(detection => {
            const confidence = ((detection.confidence || 0) * 100).toFixed(2);
            const className = detection.class_name || detection.class || 'Unknown';

            if (showWindowCoords && detection.bbox_window) {
                const detectBox = detection.bbox_detect?.join(', ') || '-';
                const windowBox = detection.bbox_window.join(', ');
                const centerWindow = detection.center_window.join(', ');
                const centerScreen = detection.center_screen.join(', ');
                rowsHtml += `<tr>
                    <td>${className}</td>
                    <td>${confidence}%</td>
                    <td><small>[${detectBox}]</small></td>
                    <td><small>[${windowBox}]</small></td>
                    <td><strong>(${centerWindow})</strong></td>
                    <td><strong>(${centerScreen})</strong></td>
                </tr>`;
            } else {
                const bbox = Array.isArray(detection.bbox)
                    ? detection.bbox.map(v => Math.round(v)).join(', ')
                    : '-';
                rowsHtml += `<tr>
                    <td>${className}</td>
                    <td>${confidence}%</td>
                    <td>[${bbox}]</td>
                </tr>`;
            }
        });

        const colSpan = showWindowCoords ? 6 : 3;
        if (!rowsHtml) {
            rowsHtml = `<tr><td colspan="${colSpan}" class="text-center text-muted">本帧未检测到目标</td></tr>`;
        }

        const metaHtml = showWindowCoords && coordinateMeta ? `
            <div class="alert alert-secondary py-2 mb-3">
                <small>
                    <strong>坐标说明：</strong>
                    窗口内容尺寸 ${coordinateMeta.nativeWidth}×${coordinateMeta.nativeHeight} px，
                    送检尺寸 ${coordinateMeta.detectWidth}×${coordinateMeta.detectHeight} px，
                    缩放比 ${coordinateMeta.scaleX} × ${coordinateMeta.scaleY}。
                    <strong>窗口点击中心</strong> 可直接用于窗口客户区内的鼠标操作；
                    <strong>屏幕点击中心</strong> = 窗口坐标 + 下方「窗口屏幕偏移」。
                </small>
            </div>` : '';

        const tableHead = showWindowCoords ? `
            <tr>
                <th>类别</th>
                <th>置信度</th>
                <th>送检坐标</th>
                <th>窗口坐标 [x1,y1,x2,y2]</th>
                <th>窗口点击中心 (x,y)</th>
                <th>屏幕点击中心 (x,y)</th>
            </tr>` : `
            <tr><th>类别</th><th>置信度</th><th>位置 [x1,y1,x2,y2]</th></tr>`;

        return `<div class="card mb-4 detection-frame-result">
            <div class="card-header">${title}</div>
            <div class="card-body">
                ${metaHtml}
                <div class="text-center mb-3">
                    <img src="${imageDataUrl}" alt="检测结果" class="img-fluid">
                </div>
                <div class="table-responsive">
                    <table class="table table-striped table-sm">
                        <thead>${tableHead}</thead>
                        <tbody>${rowsHtml}</tbody>
                    </table>
                </div>
            </div>
        </div>`;
    }

    updateStreamFrameResult(frameIndex, imageDataUrl, detections, confThreshold, coordinateMeta) {
        const resultContainer = document.getElementById('detection-result');
        const resultContentContainer = document.getElementById('result-container');
        if (!resultContentContainer) return;

        resultContainer.style.display = 'block';
        const title = `第 ${frameIndex} 帧 — 检测到 ${detections.length} 个目标`;
        let html = this.buildDetectionResultCard(title, imageDataUrl, detections, {
            showWindowCoords: true,
            coordinateMeta,
        });

        if (detections.length === 0 && parseFloat(confThreshold) >= 0.7) {
            html += `<div class="alert alert-warning mt-2">
                当前置信度阈值为 <strong>${confThreshold}</strong>，偏高时大部分目标会被过滤。
                建议降至 <strong>0.25~0.5</strong> 后重新点击「开始检测」。
            </div>`;
        }

        resultContentContainer.innerHTML = html;
    }

    async parseErrorResponse(response, fallbackMessage) {
        const text = await response.text();
        try {
            const json = JSON.parse(text);
            if (typeof json.detail === 'string') return json.detail;
            if (Array.isArray(json.detail)) {
                return json.detail.map(item => item.msg || JSON.stringify(item)).join('; ');
            }
            return json.message || text || fallbackMessage;
        } catch (e) {
            return text || fallbackMessage;
        }
    }

    startStreamDetection() {
        const modelSelect = document.getElementById('model-select');
        const confThreshold = document.getElementById('conf-threshold');
        const iouThreshold = document.getElementById('iou-threshold');
        const videoElement = document.getElementById('detection-preview-video');
        const submitBtn = document.getElementById('detection-submit-btn');
        const stopBtn = document.getElementById('detection-stop-stream-btn');
        const resultContentContainer = document.getElementById('result-container');

        if (!modelSelect?.value) {
            alert('请选择模型');
            return;
        }
        const track = this.stream?.getVideoTracks?.()[0];
        if (!track || track.readyState !== 'live') {
            alert('请先点击「选择窗口/屏幕」并选择要共享的窗口');
            return;
        }
        if (this.isStreamDetecting) return;

        this.isStreamDetecting = true;
        this.streamFrameIndex = 0;
        this.syncDetectInFlight = false;
        this.lastDetectRequestTime = 0;

        if (submitBtn) submitBtn.disabled = true;
        if (stopBtn) stopBtn.style.display = 'inline-block';
        if (resultContentContainer) {
            resultContentContainer.innerHTML = '<div class="alert alert-info">窗口流检测已开始，下方将实时显示最新一帧的检测结果。</div>';
        }
        this.setStreamStatus('<span class="badge bg-warning">检测中...</span>');

        const maxDimension = parseInt(document.getElementById('detection-display-max-dimension')?.value || '1280', 10);
        const targetFps = parseInt(document.getElementById('detection-display-target-fps')?.value || '2', 10);
        const minInterval = 1000 / targetFps;

        const detectLoop = () => {
            if (!this.isStreamDetecting) return;

            const now = performance.now();
            if (this.syncDetectInFlight || (now - this.lastDetectRequestTime) < minInterval) {
                this.streamAnimationId = requestAnimationFrame(detectLoop);
                return;
            }

            this.lastDetectRequestTime = now;
            this.syncDetectInFlight = true;

            this.captureFrameForDetection(videoElement, maxDimension)
                .then(({ blob, sourceWidth, sourceHeight, nativeWidth, nativeHeight, canvas }) => {
                    const formData = new FormData();
                    formData.append('file', blob, `frame_${Date.now()}.jpg`);
                    formData.append('model_id', modelSelect.value);
                    formData.append('conf_thres', confThreshold.value);
                    formData.append('iou_thres', iouThreshold.value);

                    return authenticatedFetch(`${API_URL}/sync-detection/sync-detect`, {
                        method: 'POST',
                        body: formData,
                    }).then(async response => {
                        if (!response.ok) {
                            const detail = await this.parseErrorResponse(response, '帧检测失败');
                            throw new Error(detail);
                        }
                        return response.json().then(data => ({
                            data,
                            sourceWidth,
                            sourceHeight,
                            nativeWidth,
                            nativeHeight,
                            canvas,
                        }));
                    });
                })
                .then(({ data, sourceWidth, sourceHeight, nativeWidth, nativeHeight, canvas }) => {
                    let detections = data.detections || [];
                    detections = this.scaleDetectionsForCanvas(
                        detections,
                        sourceWidth,
                        sourceHeight,
                        canvas.width,
                        canvas.height
                    );
                    detections = this.enrichDetectionsWithWindowCoords(
                        detections,
                        canvas.width,
                        canvas.height,
                        nativeWidth,
                        nativeHeight
                    );
                    const coordinateMeta = {
                        nativeWidth,
                        nativeHeight,
                        detectWidth: canvas.width,
                        detectHeight: canvas.height,
                        scaleX: (nativeWidth / canvas.width).toFixed(4),
                        scaleY: (nativeHeight / canvas.height).toFixed(4),
                    };
                    this.streamFrameIndex += 1;
                    const imageDataUrl = this.renderAnnotatedImageDataUrl(canvas, detections);
                    this.updateStreamFrameResult(
                        this.streamFrameIndex,
                        imageDataUrl,
                        detections,
                        confThreshold.value,
                        coordinateMeta
                    );
                    this.setStreamStatus(`<span class="badge bg-success">检测中 — 已完成 ${this.streamFrameIndex} 帧</span>`);
                })
                .catch(error => {
                    console.error('窗口流帧检测失败:', error);
                    this.setStreamStatus(`<span class="badge bg-danger">${error.message}</span>`);
                })
                .finally(() => {
                    this.syncDetectInFlight = false;
                    if (this.isStreamDetecting) {
                        this.streamAnimationId = requestAnimationFrame(detectLoop);
                    }
                });
        };

        this.streamAnimationId = requestAnimationFrame(detectLoop);
    }

    stopStreamDetection() {
        this.isStreamDetecting = false;
        if (this.streamAnimationId) {
            cancelAnimationFrame(this.streamAnimationId);
            this.streamAnimationId = null;
        }
        this.syncDetectInFlight = false;

        const submitBtn = document.getElementById('detection-submit-btn');
        const stopBtn = document.getElementById('detection-stop-stream-btn');
        if (submitBtn) submitBtn.disabled = false;
        if (stopBtn) stopBtn.style.display = 'none';
        this.setStreamStatus(`<span class="badge bg-secondary">已停止，共检测 ${this.streamFrameIndex} 帧</span>`);
    }

    async submitDetection() {
        const modelSelect = document.getElementById('model-select');
        const fileInput = document.getElementById('detection-file');
        const confThreshold = document.getElementById('conf-threshold');
        const iouThreshold = document.getElementById('iou-threshold');
        const resultContainer = document.getElementById('detection-result');
        const resultContentContainer = document.getElementById('result-container');

        if (!modelSelect.value || !fileInput.files[0]) {
            alert('请选择模型和上传文件');
            return;
        }

        const file = fileInput.files[0];
        const isVideo = /\.(mp4|avi|mov|mkv|webm|flv|wmv|m4v)$/i.test(file.name);

        resultContainer.style.display = 'block';
        if (isVideo) {
            resultContentContainer.innerHTML = `
                <div class="text-center my-5">
                    <div class="spinner-border text-primary" role="status"></div>
                    <p class="mt-3 mb-1">视频检测中，正在逐帧推理，请耐心等待...</p>
                    <p class="text-muted small mb-1">文件：${file.name}</p>
                    <p class="text-muted small">长视频可能需要数分钟。进度日志：docker logs myolotrain_web -f</p>
                </div>`;
        } else {
            resultContentContainer.innerHTML = '<div class="text-center my-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3">正在处理，请稍候...</p></div>';
        }

        const formData = new FormData();
        formData.append('model_id', modelSelect.value);
        formData.append('file', fileInput.files[0]);
        formData.append('conf_thres', confThreshold.value);
        formData.append('iou_thres', iouThreshold.value);

        try {
            const response = await authenticatedFetch(`${API_URL}/detection/`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const detail = await this.parseErrorResponse(response, '检测失败');
                throw new Error(detail);
            }

            const result = await response.json();
            const resultResponse = await authenticatedFetch(`${API_URL}/detection/${result.id}/result`);

            if (!resultResponse.ok) {
                const detail = await this.parseErrorResponse(resultResponse, '获取检测结果失败');
                throw new Error(detail);
            }

            const resultData = await resultResponse.json();

            if (resultData.status !== 'completed' || !resultData.results || resultData.results.length === 0) {
                resultContentContainer.innerHTML = `<div class="alert alert-warning">${resultData.message || '未找到检测结果'}</div>`;
                return;
            }

            let resultHtml = '';

            resultData.results.forEach(result => {
                if (result.media_type === 'video' || result.video_url) {
                    resultHtml += `<div class="card mb-4">
                        <div class="card-header">视频检测完成：共 ${result.frame_count || 0} 帧，累计检出 ${result.total_detections || 0} 个目标</div>
                        <div class="card-body">
                            ${result.video_url ? `
                            <div class="text-center mb-3">
                                <video src="${result.video_url}" controls class="w-100" style="max-height: 480px;"></video>
                                <div class="form-text mt-2">标注结果视频（带检测框）</div>
                            </div>` : '<div class="alert alert-warning">未生成标注视频，请查看服务端日志</div>'}`;

                    (result.sample_frames || []).forEach(sample => {
                        resultHtml += `<div class="mt-4">
                            <h6>采样帧 #${sample.frame_index}（${sample.count} 个目标）</h6>
                            <div class="table-responsive">
                                <table class="table table-striped table-sm">
                                    <thead>
                                        <tr><th>类别</th><th>置信度</th><th>位置 [x1,y1,x2,y2]</th></tr>
                                    </thead>
                                    <tbody>`;
                        (sample.detections || []).forEach(detection => {
                            const confidence = (detection.confidence * 100).toFixed(2);
                            const bbox = detection.bbox.map(v => Math.round(v)).join(', ');
                            resultHtml += `<tr>
                                <td>${detection.class_name}</td>
                                <td>${confidence}%</td>
                                <td>[${bbox}]</td>
                            </tr>`;
                        });
                        resultHtml += `</tbody></table></div></div>`;
                    });

                    resultHtml += `</div></div>`;
                    return;
                }

                resultHtml += this.buildDetectionResultCard(
                    `检测到 ${result.count} 个目标`,
                    result.image_url,
                    result.detections || []
                );
            });

            resultContentContainer.innerHTML = resultHtml;
        } catch (error) {
            console.error('Error in detection:', error);
            resultContentContainer.innerHTML = `<div class="alert alert-danger">检测失败: ${error.message}</div>`;
        }
    }
}

window.detectionManager = new DetectionManager();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DetectionManager;
}
