# Myolotrain GPU版本Docker部署详细指南

## 概述

本文档详细记录了Myolotrain项目的GPU版本Docker镜像构建、打包和部署的完整过程。通过Docker容器化技术，我们成功实现了基于NVIDIA CUDA的GPU加速支持，使系统能够在容器环境中充分利用硬件资源进行深度学习模型训练和推理。

## Docker环境准备

### 系统要求
- Docker Engine 20.10+
- NVIDIA Driver 450.80.02+
- NVIDIA Container Toolkit
- Linux系统（推荐Ubuntu 20.04+）

### NVIDIA Docker环境配置

1. **安装NVIDIA Container Toolkit**
   ```bash
   # 添加nvidia-docker仓库
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

   # 安装nvidia-docker2
   sudo apt-get update
   sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

2. **验证安装**
   ```bash
   # 检查NVIDIA驱动
   nvidia-smi

   # 验证Docker NVIDIA支持
   docker info | grep -i nvidia
   ```

## Docker镜像构建过程

### 1. Dockerfile.gpu文件分析

项目提供了专门用于GPU支持的Dockerfile：
```dockerfile
FROM nvidia/cuda:12.0.1-cudnn8-runtime-ubuntu22.04

# 使用国内镜像源加速apt
RUN sed -i 's/archive.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

# 安装Python 3.12和系统依赖
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    build-essential \
    libpq-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 创建python3.12符号链接
RUN ln -sf /usr/bin/python3.12 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.12 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# 安装pip并升级setuptools
RUN python3.12 -m ensurepip --upgrade && \
    python3.12 -m pip install --upgrade pip setuptools

# 设置pip使用国内镜像源
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
# 安装基础依赖，并添加GPU版本的onnxruntime 1.21.0
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt onnxruntime-gpu==1.21.0 --break-system-packages

# PyTorch已经在requirements.txt中安装，这里不需要重复安装
# 如果需要特定版本，可以取消注释下面这行并使用国内镜像源
# RUN python3.12 -m pip install torch torchvision torchaudio --index-url https://pypi.tuna.tsinghua.edu.cn/simple --break-system-packages

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p app/static/uploads app/static/datasets app/static/models app/static/results app/static/annotations logs/tensorboard

# 暴露端口
EXPOSE 8000 6006

# 启动命令
CMD ["python3.12", "run.py"]
```

### 2. 构建过程中的问题及解决方案

**问题描述**：
在初次构建过程中，遇到了PyTorch从国外源下载超时的问题：
```
WARNING: Connection timed out while downloading.
```

**解决方案**：
修改Dockerfile.gpu文件，移除了重复的PyTorch安装命令，因为PyTorch已经在requirements.txt中声明，避免了从国外源下载导致的超时问题。

### 3. 执行构建命令

```bash
# 构建GPU版本Docker镜像
docker build -f Dockerfile.gpu -t myolotrain-gpu .
```

构建过程关键步骤：
1. 使用 Python 3.12 + PyTorch CUDA wheel 基础环境
2. 配置国内 APT 和 PyPI 镜像源加速下载
3. 安装 git 及系统依赖（用于从 GitHub 安装 YOLOv13 fork）
4. 安装 **Flash Attention 2.8.3**（匹配 PyTorch 2.6 + CUDA 12 + Python 3.12，构建时自动验证 import）
5. 通过 requirements.txt 安装 Python 依赖（含 iMoonLab/yolov13 ultralytics fork，支持 YOLOv8/11/13）
6. 复制应用代码到容器
7. 创建必要的目录结构

> **YOLOv13 说明**：镜像内置 [iMoonLab/yolov13](https://github.com/iMoonLab/yolov13) 分支版 ultralytics。首次训练 YOLOv13 时会自动从 GitHub Releases 下载预训练权重（如 `yolov13n.pt`）。模型测试、检测、导出 ONNX 等推理功能与 YOLOv8/11 用法相同。

> **Flash Attention 说明**：GPU 镜像在构建阶段预装 `flash-attn`，部署环境要求 **Ampere 及以上 GPU**（如 RTX 30/40、A100）。YOLOv13 训练时会自动启用 Flash Attention；YOLOv8/11 不使用该模块，功能不受影响。

## Docker Compose部署

### 1. docker-compose-gpu.yml配置文件

```yaml
version: '3'

services:
  db:
    image: postgres:13
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: yolov8_platform
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  web:
    build:
      context: .
      dockerfile: Dockerfile.gpu
    ports:
      - "8013:8000"
      - "6006:6006"
    depends_on:
      - db
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=yolov8_platform
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ./app/static:/app/app/static
      - ./logs:/app/logs
    restart: always
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  postgres_data:
```

### 2. 启动服务集群

```bash
# 使用docker-compose启动GPU版本服务
docker-compose -f docker-compose-gpu.yml up -d
```

启动过程：
1. 构建web服务镜像（如果尚未构建）
2. 启动PostgreSQL数据库容器
3. 启动web应用容器，配置GPU访问权限
4. 建立服务间网络连接
5. 挂载必要的数据卷

### 3. 服务状态验证

```bash
# 查看服务状态
docker-compose -f docker-compose-gpu.yml ps

# 查看web服务日志
docker-compose -f docker-compose-gpu.yml logs web

# 查看数据库服务日志
docker-compose -f docker-compose-gpu.yml logs db
```

## GPU支持验证

### 1. 容器内GPU功能测试

```bash
# 测试PyTorch GPU支持
docker run --rm --gpus all myolotrain-gpu python3.12 -c "
import torch
print(f'PyTorch版本: {torch.__version__}')
print(f'CUDA可用: {torch.cuda.is_available()}')
print(f'CUDA版本: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')
print(f'GPU数量: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    print(f'GPU型号: {torch.cuda.get_device_name(0)}')
"
```

预期输出：
```
PyTorch版本: 2.9.1+cu128
CUDA可用: True
CUDA版本: 12.8
GPU数量: 1
GPU型号: NVIDIA GeForce RTX 4090
```

### 2. 应用服务验证

```bash
# 测试Web应用可访问性
curl -I http://localhost:8013

# 测试登录页面
curl -s http://localhost:8013/login | head -5

# 测试API接口
curl -s http://localhost:8013/api/monitoring/system-resources | jq '.'

# 测试TensorBoard服务
curl -I http://localhost:6006
```

## 默认凭据信息

### 管理员账户
- **用户名**：`admin`
- **默认密码**：`admin@123`

### 密码修改工具
项目提供了两个工具脚本用于修改管理员密码：
- `/tools/change_admin_password.py`
- `/tools/update_admin_password.py`

## 访问地址

- **Web应用程序**：http://localhost:8013
- **TensorBoard监控**：http://localhost:6006
- **API接口**：http://localhost:8013/api/

## 数据持久化

通过Docker卷实现数据持久化：
- PostgreSQL数据存储在`postgres_data`卷中
- 应用静态文件挂载到本地`./app/static`目录
- 日志文件挂载到本地`./logs`目录

## 故障排除

### 1. GPU设备无法访问

**问题现象**：
```
NVIDIA Driver was not detected. GPU functionality will not be available.
```

**解决方案**：
- 确认已安装NVIDIA Container Toolkit
- 重启Docker服务
- 使用`--gpus all`参数运行容器

### 2. 构建过程中网络超时

**问题现象**：
```
WARNING: Connection timed out while downloading.
```

**解决方案**：
- 使用国内镜像源（已在Dockerfile中配置）
- 确保网络连接稳定
- 重试构建过程

### 3. 端口冲突

**问题现象**：
```
port is already allocated
```

**解决方案**：
- 修改docker-compose.yml中的端口映射
- 停止占用端口的其他服务
- 使用`docker-compose down`停止现有服务

## 总结

通过Docker容器化技术，我们成功实现了Myolotrain项目的GPU版本部署：

1. **容器化优势**：
   - 环境隔离，避免依赖冲突
   - 一键部署，简化安装过程
   - 资源限制，合理分配系统资源

2. **GPU支持**：
   - 完整的CUDA运行时环境
   - PyTorch GPU版本集成
   - NVIDIA容器运行时支持

3. **服务编排**：
   - 使用docker-compose管理多服务架构
   - 数据持久化通过Docker卷实现
   - 环境变量配置灵活

系统现已准备就绪，可通过Docker容器提供稳定的GPU加速深度学习服务。