# 部署说明

## 环境要求

- Python 3.12+
- PostgreSQL 13+
- Docker (可选，用于数据库)

## 快速部署步骤

### 1. 创建虚拟环境

```bash
python3.12 -m venv venv
```

**激活虚拟环境：**

- Linux/Mac:
  ```bash
  source venv/bin/activate
  ```

- Windows:
  ```bash
  venv\Scripts\activate
  ```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

#### 方式一：使用 Docker（推荐）

```bash
docker run -d --name postgres-yolo \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=yolov8_platform \
    -p 5432:5432 \
    postgres:13
```

#### 方式二：本地安装 PostgreSQL

参考 `INSTALL_POSTGRES.md` 文件

### 4. 初始化数据库

```bash
python init_db.py
```

### 5. 启动服务

```bash
python run.py
```

或者使用启动脚本：

```bash
./start.sh
```

### 6. 访问服务

- Web界面: http://localhost:8000
- TensorBoard: http://localhost:6006
- 默认登录: admin / admin@123

## 配置说明

### 数据库配置

编辑 `app/core/config.py` 中的数据库连接配置：

```python
SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/yolov8_platform"
```

### 环境变量

可以通过环境变量覆盖配置：

- `DATABASE_URL`: 数据库连接字符串
- `SECRET_KEY`: JWT密钥
- `DEBUG`: 调试模式

## 功能说明

### 已实现的功能

1. **场景检测提取关键帧**
   - 自动检查是否已提取
   - 已提取则直接展示
   - 未提取则自动提取并展示

2. **运动检测查看详情**
   - 在图片上绘制运动区域边界框
   - 彩色标注不同区域
   - 显示详细信息表格

3. **YOLO 模型支持**
   - 支持 YOLOv8、YOLO11、YOLOv13 模型
   - 模型上传、训练与推理（模型测试）

## 常见问题

### 1. 数据库连接失败

- 检查 PostgreSQL 是否运行
- 检查数据库配置是否正确
- 检查防火墙设置

### 2. 端口被占用

修改 `run.py` 中的端口配置，或使用启动脚本自动处理

### 3. 依赖安装失败

- 确保使用 Python 3.12+
- 升级 pip: `pip install --upgrade pip`
- 使用国内镜像: `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 文件结构

```
Myolotrain-master/
├── app/                    # 应用主目录
│   ├── api/               # API 端点
│   ├── core/              # 核心配置
│   ├── db/                # 数据库相关
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑
│   ├── static/            # 静态文件（前端）
│   └── utils/             # 工具函数
├── tools/                 # 工具脚本
├── datasets_import/      # 示例数据集
├── requirements.txt       # Python 依赖
├── docker-compose.yml     # Docker 配置
├── Dockerfile            # Docker 镜像
├── init_db.py            # 数据库初始化
├── run.py                # 启动脚本
└── start.sh              # 启动脚本（带检查）
```

## 技术支持

如有问题，请查看：
- `README.md` - 项目说明
- `INSTALL_POSTGRES.md` - PostgreSQL 安装指南
- `DOCKER_DEPLOYMENT.md` - Docker 部署指南

