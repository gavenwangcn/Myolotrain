#!/bin/bash
# Myolotrain 一键启动脚本

cd "$(dirname "$0")"

echo "============================================================"
echo "Myolotrain 启动脚本"
echo "============================================================"

# 配置Docker路径（如果Docker Desktop已安装）
if [ -d "/Applications/Docker.app" ]; then
    export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
    echo "✓ Docker路径已配置"
fi

# 检查并启动PostgreSQL
echo "检查PostgreSQL..."
if ! docker ps | grep -q postgres-yolo; then
    if docker ps -a | grep -q postgres-yolo; then
        echo "启动PostgreSQL容器..."
        docker start postgres-yolo
    else
        echo "创建PostgreSQL容器..."
        docker run -d --name postgres-yolo \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=postgres \
            -e POSTGRES_DB=yolov8_platform \
            -p 5432:5432 postgres:13
    fi
    echo "等待PostgreSQL启动..."
    sleep 5
else
    echo "✓ PostgreSQL容器正在运行"
fi

# 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "错误: 虚拟环境不存在，请先运行: python3.12 setup_venv.py"
    exit 1
fi

source venv/bin/activate

# 检查数据库连接
echo "检查数据库连接..."
python3.12 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='postgres'
    )
    conn.close()
    print('✓ 数据库连接成功')
except Exception as e:
    print('✗ 数据库连接失败:', e)
    exit(1)
" || exit 1

# 初始化数据库（如果需要）
echo "检查数据库..."
python3.12 init_db.py 2>&1 | tail -3

# 检查并停止占用8000端口的进程
echo "检查端口8000..."
PORT_PID=$(lsof -ti :8000 2>/dev/null)
if [ ! -z "$PORT_PID" ]; then
    echo "发现端口8000被进程 $PORT_PID 占用，正在停止..."
    kill -9 $PORT_PID 2>/dev/null
    sleep 2
    echo "✓ 已停止占用端口的进程"
fi

# 检查并停止运行中的run.py进程
echo "检查运行中的服务..."
RUN_PIDS=$(ps aux | grep "python3.12 run.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$RUN_PIDS" ]; then
    echo "发现运行中的服务进程，正在停止..."
    echo "$RUN_PIDS" | xargs kill -9 2>/dev/null
    sleep 2
    echo "✓ 已停止运行中的服务"
fi

# 启动服务
echo ""
echo "============================================================"
echo "启动Web服务..."
echo "============================================================"
echo "服务地址:"
echo "  - Web界面: http://localhost:8000"
echo "  - TensorBoard: http://localhost:6006"
echo ""
echo "默认登录: admin / admin@123"
echo ""
echo "按 Ctrl+C 停止服务"
echo "============================================================"
echo ""

python3.12 run.py

