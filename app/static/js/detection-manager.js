// 检测功能模块
class DetectionManager {
    constructor() {
        // 构造函数
    }

    // 加载检测表单
    loadDetectionForm() {
        // 加载模型选项
        fetch(`${API_URL}/models/`)
            .then(response => response.json())
            .then(models => {
                const select = document.getElementById('model-select');
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

    // 绑定检测页面事件
    bindDetectionEvents() {
        // 绑定表单提交事件
        const form = document.getElementById('detection-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitDetection();
            });
        }

        // 绑定滑块值显示
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
    }

    // 提交检测请求
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

        resultContainer.style.display = 'block';
        resultContentContainer.innerHTML = '<div class="text-center my-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-3">正在处理，请稍候...</p></div>';

        const formData = new FormData();
        formData.append('model_id', modelSelect.value);
        formData.append('file', fileInput.files[0]);
        formData.append('conf_thres', confThreshold.value);
        formData.append('iou_thres', iouThreshold.value);

        const parseErrorResponse = async (response, fallbackMessage) => {
            const text = await response.text();
            try {
                const json = JSON.parse(text);
                if (typeof json.detail === 'string') {
                    return json.detail;
                }
                if (Array.isArray(json.detail)) {
                    return json.detail.map(item => item.msg || JSON.stringify(item)).join('; ');
                }
                return json.message || text || fallbackMessage;
            } catch (e) {
                return text || fallbackMessage;
            }
        };

        try {
            const response = await authenticatedFetch(`${API_URL}/detection/`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const detail = await parseErrorResponse(response, '检测失败');
                throw new Error(detail);
            }

            const result = await response.json();
            const resultResponse = await authenticatedFetch(`${API_URL}/detection/${result.id}/result`);

            if (!resultResponse.ok) {
                const detail = await parseErrorResponse(resultResponse, '获取检测结果失败');
                throw new Error(detail);
            }

            const resultData = await resultResponse.json();
            console.log('Detection result:', resultData);

            if (resultData.status !== 'completed' || !resultData.results || resultData.results.length === 0) {
                resultContentContainer.innerHTML = `<div class="alert alert-warning">${resultData.message || '未找到检测结果'}</div>`;
                return;
            }

            let resultHtml = '';

            resultData.results.forEach(result => {
                resultHtml += `<div class="card mb-4">
                    <div class="card-header">检测到 ${result.count} 个目标</div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <img src="${result.image_url}" alt="检测结果" class="img-fluid">
                        </div>
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>类别</th>
                                        <th>置信度</th>
                                        <th>位置</th>
                                    </tr>
                                </thead>
                                <tbody>`;

                result.detections.forEach(detection => {
                    const confidence = (detection.confidence * 100).toFixed(2);
                    const bbox = detection.bbox.map(v => Math.round(v)).join(', ');

                    resultHtml += `<tr>
                        <td>${detection.class_name}</td>
                        <td>${confidence}%</td>
                        <td>[${bbox}]</td>
                    </tr>`;
                });

                resultHtml += `</tbody>
                            </table>
                        </div>
                    </div>
                </div>`;
            });

            resultContentContainer.innerHTML = resultHtml;
        } catch (error) {
            console.error('Error in detection:', error);
            resultContentContainer.innerHTML = `<div class="alert alert-danger">检测失败: ${error.message}</div>`;
        }
    }
}

// 创建全局实例
window.detectionManager = new DetectionManager();

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DetectionManager;
}
