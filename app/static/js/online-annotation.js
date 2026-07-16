// 在线标注模块
class OnlineAnnotation {
    constructor() {
        this.currentSortField = '';
        this.currentSortDirection = 'asc';
    }

    // 加载标注页面
    loadAnnotationPage() {
        console.log('Loading annotation page...');
        
        // 加载标注项目列表
        this.loadAnnotationProjects();
        
        // 绑定标注页面事件
        this.bindAnnotationEvents();
    }

    // 加载标注项目列表
    loadAnnotationProjects() {
        authenticatedFetch(`${API_URL}/annotation/projects/`)
            .then(response => response.json())
            .then(projects => {
                const tableBody = document.getElementById('annotation-projects-table-body');
                if (!tableBody) {
                    console.error('annotation-projects-table-body element not found');
                    return;
                }

                tableBody.innerHTML = '';

                if (projects.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="8" class="text-center">暂无标注项目</td></tr>';
                    return;
                }

                projects.forEach(project => {
                    const row = document.createElement('tr');
                    
                    // 获取项目统计信息
                    authenticatedFetch(`${API_URL}/annotation/projects/${project.id}/stats`)
                        .then(response => response.json())
                        .then(stats => {
                            const progressPercentage = stats.progress_percentage || 0;
                            
                            row.innerHTML = `
                                <td>${project.name}</td>
                                <td>${project.description || '-'}</td>
                                <td>${project.classes.length}</td>
                                <td>${stats.total_images || 0}</td>
                                <td>${stats.completed_images || 0}</td>
                                <td style="padding-top: 2px;">
                                    <div class="progress" style="width: 100px;">
                                        <div class="progress-bar" role="progressbar" style="width: ${progressPercentage}%" aria-valuenow="${progressPercentage}" aria-valuemin="0" aria-valuemax="100">
                                            ${Math.round(progressPercentage)}%
                                        </div>
                                    </div>
                                </td>
                                <td><span class="badge ${this.getStatusBadgeClass(project.status)}">${this.getStatusText(project.status)}</span></td>
                                <td>
                                    <div class="btn-group">
                                        <a href="/static/annotation.html?project_id=${project.id}" target="_blank" class="btn btn-sm btn-primary">开始标注</a>
                                        <button class="btn btn-sm btn-info" onclick="onlineAnnotation.scanProjectImages('${project.id}')">扫描图片</button>
                                        <button class="btn btn-sm btn-success" onclick="onlineAnnotation.exportAnnotations('${project.id}')">导出标注</button>
                                        <button class="btn btn-sm btn-warning" onclick="onlineAnnotation.exportToDataset('${project.id}')">导出为数据集</button>
                                        <button class="btn btn-sm btn-danger" onclick="onlineAnnotation.deleteAnnotationProject('${project.id}')">删除</button>
                                    </div>
                                </td>
                            `;
                        })
                        .catch(error => {
                            console.error('Error loading project stats:', error);
                            row.innerHTML = `
                                <td>${project.name}</td>
                                <td>${project.description || '-'}</td>
                                <td>${project.classes.length}</td>
                                <td>-</td>
                                <td>-</td>
                                <td>-</td>
                                <td><span class="badge bg-secondary">未知</span></td>
                                <td>
                                    <div class="btn-group">
                                        <a href="/static/annotation.html?project_id=${project.id}" target="_blank" class="btn btn-sm btn-primary">开始标注</a>
                                        <button class="btn btn-sm btn-info" onclick="onlineAnnotation.scanProjectImages('${project.id}')">扫描图片</button>
                                        <button class="btn btn-sm btn-success" onclick="onlineAnnotation.exportAnnotations('${project.id}')">导出</button>
                                        <button class="btn btn-sm btn-warning" onclick="onlineAnnotation.exportToDataset('${project.id}')">导出为数据集</button>
                                        <button class="btn btn-sm btn-danger" onclick="onlineAnnotation.deleteAnnotationProject('${project.id}')">删除</button>
                                    </div>
                                </td>
                            `;
                        });
                    
                    tableBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error loading annotation projects:', error);
                const tableBody = document.getElementById('annotation-projects-table-body');
                if (tableBody) {
                    tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">加载标注项目失败</td></tr>';
                }
            });
    }

    // 绑定标注页面事件
    bindAnnotationEvents() {
        const createProjectBtn = document.getElementById('create-annotation-project-btn');
        if (createProjectBtn) {
            createProjectBtn.addEventListener('click', () => this.showCreateAnnotationProjectModal());
        }
        
        const projectSelect = document.getElementById('annotation-project-select');
        if (projectSelect) {
            projectSelect.addEventListener('change', function() {
                if (this.value) {
                    // 这里需要实现加载标注项目功能
                    console.log('Loading annotation project:', this.value);
                }
            });
        }
    }

    // 显示创建标注项目模态框
    showCreateAnnotationProjectModal() {
        const modalTitle = document.querySelector('.modal-title');
        const modalBody = document.querySelector('.modal-body');
        const modalSubmit = document.getElementById('modalSubmit');

        modalTitle.textContent = '创建标注项目';

        // 获取模板内容
        const template = document.getElementById('create-annotation-project-template');
        if (!template) {
            console.error('create-annotation-project-template not found');
            return;
        }

        modalBody.innerHTML = template.innerHTML;

        // 加载数据集选项
        this.loadDatasetOptionsForAnnotation();
        
        // 绑定图片来源选择事件
        this.bindImageSourceEvents();

        modal.show();

        modalSubmit.onclick = () => this.submitCreateAnnotationProject();
    }

    // 绑定图片来源选择事件
    bindImageSourceEvents() {
        const imageSourceRadios = document.querySelectorAll('input[name="image-source"]');
        const datasetContainer = document.getElementById('dataset-source-container');
        const directoryContainer = document.getElementById('directory-source-container');
        const uploadContainer = document.getElementById('upload-source-container');
        const folderContainer = document.getElementById('folder-source-container');
        
        imageSourceRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                // 隐藏所有容器
                if (datasetContainer) datasetContainer.style.display = 'none';
                if (directoryContainer) directoryContainer.style.display = 'none';
                if (uploadContainer) uploadContainer.style.display = 'none';
                if (folderContainer) folderContainer.style.display = 'none';
                
                // 显示选中的容器（用箭头函数，保留 OnlineAnnotation 实例的 this）
                if (radio.value === 'dataset') {
                    if (datasetContainer) datasetContainer.style.display = 'block';
                } else if (radio.value === 'directory') {
                    if (directoryContainer) directoryContainer.style.display = 'block';
                    this.bindDirectoryBrowseButton();
                } else if (radio.value === 'upload') {
                    if (uploadContainer) uploadContainer.style.display = 'block';
                } else if (radio.value === 'folder') {
                    if (folderContainer) folderContainer.style.display = 'block';
                }
            });
        });
        
        // 打开弹窗时若已选「服务器目录」，立刻绑定浏览按钮
        const checked = document.querySelector('input[name="image-source"]:checked');
        if (checked && checked.value === 'directory') {
            this.bindDirectoryBrowseButton();
        }
        
        // 默认显示上传容器
        if (uploadContainer) uploadContainer.style.display = 'block';
    }

    // 绑定目录浏览按钮（在当前弹窗内嵌套选择，避免 Bootstrap 双层 modal 被挡住）
    bindDirectoryBrowseButton() {
        const browseBtn = document.getElementById('browse-image-directory-btn');
        const directoryInput = document.getElementById('annotation-image-directory');
        const scanResultDiv = document.getElementById('directory-scan-result');
        const imageCountSpan = document.getElementById('directory-image-count');
        const container = document.getElementById('directory-source-container');
        
        if (!browseBtn || !container) return;
        
        // 每次打开创建弹窗都会重建 DOM，必须重新绑定
        browseBtn.onclick = () => {
            this.showInlineDirectoryPicker(container, directoryInput, scanResultDiv, imageCountSpan);
        };
    }

    // 在「创建标注项目」弹窗内部显示目录选择器（不另开一层 modal）
    showInlineDirectoryPicker(container, directoryInput, scanResultDiv, imageCountSpan) {
        let panel = document.getElementById('annotation-inline-dir-browser');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'annotation-inline-dir-browser';
            panel.className = 'border rounded p-2 mt-2 bg-light';
            container.appendChild(panel);
        }
        panel.style.display = 'block';
        panel.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <strong><i class="bi bi-folder2-open"></i> 选择服务器目录</strong>
                <button type="button" class="btn btn-sm btn-outline-secondary" id="inline-dir-close">关闭</button>
            </div>
            <div class="small text-muted mb-2">Docker 环境下浏览的是容器内路径（如 /app/app/static）</div>
            <ol class="breadcrumb mb-2" id="inline-dir-breadcrumb"><li class="breadcrumb-item active">加载中...</li></ol>
            <div class="list-group" id="inline-dir-list" style="max-height: 260px; overflow-y: auto;">
                <div class="list-group-item text-muted">加载中...</div>
            </div>
            <div class="mt-2 d-flex gap-2">
                <button type="button" class="btn btn-primary btn-sm" id="inline-dir-select" disabled>使用当前目录</button>
            </div>
        `;

        let currentPath = '';
        const listEl = document.getElementById('inline-dir-list');
        const breadcrumbEl = document.getElementById('inline-dir-breadcrumb');
        const selectBtn = document.getElementById('inline-dir-select');

        document.getElementById('inline-dir-close').onclick = () => {
            panel.style.display = 'none';
        };

        const loadDir = async (path = '') => {
            listEl.innerHTML = '<div class="list-group-item text-muted">加载中...</div>';
            try {
                const response = await fetch(`/api/annotation/browse-directories?path=${encodeURIComponent(path)}`);
                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || `HTTP ${response.status}`);
                }
                const data = await response.json();
                currentPath = data.current_path || '';
                selectBtn.disabled = !currentPath;

                breadcrumbEl.innerHTML = '';
                const rootLi = document.createElement('li');
                rootLi.className = 'breadcrumb-item';
                rootLi.innerHTML = '<a href="#">根目录</a>';
                rootLi.querySelector('a').onclick = (e) => { e.preventDefault(); loadDir(''); };
                breadcrumbEl.appendChild(rootLi);
                if (currentPath) {
                    const curLi = document.createElement('li');
                    curLi.className = 'breadcrumb-item active';
                    curLi.textContent = currentPath;
                    breadcrumbEl.appendChild(curLi);
                }

                listEl.innerHTML = '';
                const items = data.items || [];
                if (items.length === 0) {
                    listEl.innerHTML = '<div class="list-group-item text-muted">此目录为空</div>';
                    return;
                }
                items.forEach(item => {
                    const row = document.createElement('button');
                    row.type = 'button';
                    row.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                    row.innerHTML = `<span><i class="bi bi-folder text-primary me-2"></i>${item.name}</span><span class="badge bg-secondary">进入</span>`;
                    row.onclick = () => loadDir(item.path);
                    listEl.appendChild(row);
                });
            } catch (error) {
                console.error('加载目录失败:', error);
                listEl.innerHTML = `<div class="list-group-item text-danger">加载失败: ${error.message}</div>`;
            }
        };

        selectBtn.onclick = () => {
            if (!currentPath) return;
            directoryInput.value = currentPath;
            panel.style.display = 'none';
            // 扫描图片数量
            fetch(`/api/annotation/scan-directory-images?directory_path=${encodeURIComponent(currentPath)}`)
                .then(r => r.json())
                .then(data => {
                    if (imageCountSpan) imageCountSpan.textContent = data.image_count ?? 0;
                    if (scanResultDiv) {
                        scanResultDiv.style.display = 'block';
                        const alertEl = scanResultDiv.querySelector('.alert');
                        if (alertEl) {
                            alertEl.className = data.is_valid ? 'alert alert-success' : 'alert alert-warning';
                        }
                    }
                })
                .catch(err => console.error('扫描图片失败:', err));
        };

        // Docker 容器内优先从 /app 开始，便于找到挂载目录
        loadDir('/app');
    }

    // 提交创建标注项目
    submitCreateAnnotationProject() {
        const name = document.getElementById('annotation-project-name').value;
        const description = document.getElementById('annotation-project-description').value;
        const classesText = document.getElementById('annotation-classes').value;
        const imageSource = document.querySelector('input[name="image-source"]:checked').value;
        
        if (!name || !classesText) {
            alert('请填写项目名称和类别列表');
            return;
        }
        
        const classes = classesText.split('\n').filter(c => c.trim()).map(c => c.trim());
        
        if (imageSource === 'upload') {
            const zipFile = document.getElementById('annotation-images-zip').files[0];
            if (!zipFile) {
                alert('请选择图片ZIP文件');
                return;
            }
            this.createProjectWithImageUpload(name, description, classes, zipFile);
        } else {
            this.createProjectWithExistingImages(name, description, classes, imageSource);
        }
    }

    // 使用上传图片创建项目
    createProjectWithImageUpload(name, description, classes, zipFile) {
        const progressContainer = document.getElementById('annotation-upload-progress');
        const progressBar = document.getElementById('annotation-progress-bar');
        const statusDiv = document.getElementById('annotation-upload-status');
        const modalSubmit = document.getElementById('modalSubmit');
        
        // 显示进度
        progressContainer.style.display = 'block';
        modalSubmit.disabled = true;
        modalSubmit.textContent = '创建中...';
        
        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description);
        formData.append('classes', JSON.stringify(classes));
        formData.append('images_zip', zipFile);
        
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_URL}/annotation/projects/upload`, true);
        
        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressBar.style.width = percentComplete + '%';
                progressBar.textContent = Math.round(percentComplete) + '%';
                statusDiv.textContent = '上传中...';
            }
        };
        
        xhr.onload = () => {
            if (xhr.status === 200 || xhr.status === 201) {
                statusDiv.textContent = '创建成功！';
                setTimeout(() => {
                    modal.hide();
                    this.loadAnnotationProjects();
                    alert('标注项目创建成功！');
                }, 1000);
            } else {
                try {
                    const response = JSON.parse(xhr.responseText);
                    alert('创建失败: ' + (response.detail || '未知错误'));
                } catch (e) {
                    alert('创建失败: ' + xhr.statusText);
                }
                modalSubmit.disabled = false;
                modalSubmit.textContent = '确定';
                progressContainer.style.display = 'none';
            }
        };
        
        xhr.onerror = function() {
            alert('上传失败，请检查网络连接');
            modalSubmit.disabled = false;
            modalSubmit.textContent = '确定';
            progressContainer.style.display = 'none';
        };
        
        xhr.send(formData);
    }

    // 使用现有图片创建项目
    createProjectWithExistingImages(name, description, classes, imageSource) {
        const requestData = {
            name: name,
            description: description,
            classes: classes
        };
        
        let apiEndpoint = `${API_URL}/annotation/projects/`;
        
        if (imageSource === 'dataset') {
            const datasetId = document.getElementById('annotation-dataset-id').value;
            if (!datasetId) {
                alert('请选择数据集');
                return;
            }
            requestData.dataset_id = datasetId;
        } else if (imageSource === 'directory') {
            const imageDirectory = document.getElementById('annotation-image-directory').value;
            if (!imageDirectory) {
                alert('请选择图片目录');
                return;
            }
            requestData.image_directory = imageDirectory;
            apiEndpoint = `${API_URL}/annotation/projects/from-directory`;
        }
        
        authenticatedFetch(apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || '创建项目失败'); });
            }
            return response.json();
        })
        .then(data => {
            modal.hide();
            this.loadAnnotationProjects();
            alert('标注项目创建成功！');
        })
        .catch(error => {
            console.error('Error creating annotation project:', error);
            alert('创建标注项目失败: ' + error.message);
        });
    }

    // 加载数据集选项用于标注项目
    loadDatasetOptionsForAnnotation() {
        fetch(`${API_URL}/datasets/`)
            .then(response => response.json())
            .then(datasets => {
                const select = document.getElementById('annotation-dataset-id');
                if (!select) return;
                
                // 清空现有选项（保留第一个默认选项）
                while (select.options.length > 1) {
                    select.remove(1);
                }
                
                datasets.forEach(dataset => {
                    if (dataset.status === 'available') {
                        const option = document.createElement('option');
                        option.value = dataset.id;
                        option.textContent = dataset.name;
                        select.appendChild(option);
                    }
                });
                
                // 绑定数据集选择事件
                select.addEventListener('change', function() {
                    if (this.value) {
                        // 根据选择的数据集自动填充信息
                        const selectedDataset = datasets.find(d => d.id === this.value);
                        if (selectedDataset) {
                            // 自动填充类别
                            const classesTextarea = document.getElementById('annotation-classes');
                            if (classesTextarea && selectedDataset.classes) {
                                classesTextarea.value = selectedDataset.classes.join('\n');
                            }
                            
                            // 自动填充图片目录
                            const imageDirectoryInput = document.getElementById('annotation-image-directory');
                            if (imageDirectoryInput) {
                                imageDirectoryInput.value = `datasets/${selectedDataset.name}/train/images`;
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('Error loading datasets for annotation:', error);
            });
    }

    // 扫描项目图片
    scanProjectImages(projectId) {
        if (!confirm('确定要扫描项目图片吗？这将重新扫描图片目录并更新图片列表。')) {
            return;
        }
        
        authenticatedFetch(`${API_URL}/annotation/projects/${projectId}/scan`, {
            method: 'POST'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || '扫描失败'); });
            }
            return response.json();
        })
        .then(data => {
            alert(data.message || '图片扫描完成');
            this.loadAnnotationProjects(); // 刷新项目列表
        })
        .catch(error => {
            console.error('Error scanning project images:', error);
            alert('扫描项目图片失败: ' + error.message);
        });
    }

    // 导出标注数据
    exportAnnotations(projectId) {
        const exportRequest = {
            format: 'yolo',
            include_images: true,
            split_data: false
        };
        
        authenticatedFetch(`${API_URL}/annotation/projects/${projectId}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(exportRequest)
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    try {
                        const err = JSON.parse(text);
                        throw new Error(err.detail || '导出失败');
                    } catch (e) {
                        throw new Error('导出失败: ' + response.statusText);
                    }
                });
            }
            
            // 检查响应类型
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/zip')) {
                // 处理ZIP文件下载
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `annotations_project_${projectId}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    return { message: '标注数据导出成功，文件已下载' };
                });
            } else {
                // 处理JSON响应
                return response.json();
            }
        })
        .then(data => {
            alert(data.message || '标注数据导出成功');
            if (data.export_path) {
                console.log('Export path:', data.export_path);
            }
        })
        .catch(error => {
            console.error('Error exporting annotations:', error);
            alert('导出标注数据失败: ' + error.message);
        });
    }

    // 删除标注项目
    deleteAnnotationProject(projectId) {
        if (!confirm('确定要删除这个标注项目吗？这将删除所有相关的标注数据。')) {
            return;
        }
        
        authenticatedFetch(`${API_URL}/annotation/projects/${projectId}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || '删除失败'); });
            }
            return response.json();
        })
        .then(data => {
            alert(data.message || '标注项目删除成功');
            this.loadAnnotationProjects(); // 刷新项目列表
        })
        .catch(error => {
            console.error('Error deleting annotation project:', error);
            alert('删除标注项目失败: ' + error.message);
        });
    }

    // 导出为数据集
    exportToDataset(projectId) {
        const datasetName = prompt('请输入数据集名称:');
        if (!datasetName) {
            return;
        }
        
        const datasetDescription = prompt('请输入数据集描述(可选):') || '';
        
        const formData = new FormData();
        formData.append('dataset_name', datasetName);
        formData.append('dataset_description', datasetDescription);
        
        authenticatedFetch(`${API_URL}/annotation/projects/${projectId}/export-to-dataset`, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || '导出失败'); });
            }
            return response.json();
        })
        .then(data => {
            alert(data.message || '导出为数据集成功');
            console.log('Dataset ID:', data.dataset_id);
        })
        .catch(error => {
            console.error('Error exporting to dataset:', error);
            alert('导出为数据集失败: ' + error.message);
        });
    }

    // 获取状态文本
    getStatusText(status) {
        switch (status) {
            case 'processing':
                return '处理中';
            case 'available':
                return '可用';
            case 'error':
                return '错误';
            case 'pending':
                return '未训练';
            case 'running':
                return '运行中';
            case 'training':
                return '训练中';
            case 'completed':
                return '已完成';
            case 'failed':
                return '失败';
            case 'cancelled':
                return '已取消';
            case 'active':
                return '进行中';
            case 'inactive':
                return '已完成';
            default:
                return status;
        }
    }

    // 获取状态徽章样式
    getStatusBadgeClass(status) {
        switch (status) {
            case 'processing':
            case 'pending':
                return 'bg-warning';
            case 'available':
            case 'completed':
            case 'inactive':
                return 'bg-success';
            case 'error':
            case 'failed':
                return 'bg-danger';
            case 'running':
            case 'training':
            case 'active':
                return 'bg-primary';
            case 'cancelled':
                return 'bg-secondary';
            default:
                return 'bg-secondary';
        }
    }
}

// 创建全局实例
window.onlineAnnotation = new OnlineAnnotation();

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OnlineAnnotation;
}
