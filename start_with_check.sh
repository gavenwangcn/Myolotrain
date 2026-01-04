#!/bin/bash
# 智能启动脚本 - 自动检查环境并启动

cd "$(dirname "$0")"

echo "============================================================"
echo "Myolotrain 智能启动"
echo "============================================================"

# 激活虚拟环境
if [ ! -d "venv" ]; then
    echo "错误: 虚拟环境不存在"
    exit 1
fi

source venv/bin/activate

# 检查PostgreSQL
echo "检查PostgreSQL..."
if ! command -v psql &> /dev/null && ! pg_isready -h localhost -p 5432 &> /dev/null; then
    echo ""
    echo "⚠️  PostgreSQL未安装或未运行"
    echo ""
    echo "请选择以下方式之一安装PostgreSQL："
    echo ""
    echo "【推荐】方法1：Postgres.app（最简单）"
    echo "  1. 访问: https://postgresapp.com/"
    echo "  2. 下载并安装Postgres.app"
    echo "  3. 启动Postgres.app，点击'Initialize'"
    echo "  4. 在Postgres.app菜单选择'Open psql'，运行: createuser -s postgres"
    echo ""
    echo "方法2：Homebrew（需要管理员权限）"
    echo "  sudo chown -R \$(whoami) /usr/local/Homebrew"
    echo "  brew install postgresql@14"
    echo "  brew services start postgresql@14"
    echo ""
    echo "方法3：Docker"
    echo "  docker run -d --name postgres-yolo \\"
    echo "    -e POSTGRES_USER=postgres \\"
    echo "    -e POSTGRES_PASSWORD=postgres \\"
    echo "    -e POSTGRES_DB=yolov8_platform \\"
    echo "    -p 5432:5432 postgres:13"
    echo ""
    echo "安装完成后，再次运行此脚本即可启动项目。"
    echo ""
    read -p "是否已安装PostgreSQL？(y/n): " answer
    if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
        echo "请先安装PostgreSQL后再启动项目。"
        exit 1
    fi
fi

# 检查PostgreSQL连接
echo "检查PostgreSQL连接..."
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
    print('✓ PostgreSQL连接成功')
except Exception as e:
    print('✗ PostgreSQL连接失败:', e)
    exit(1)
" || exit 1

# 初始化数据库
echo "初始化数据库..."
python3.12 init_db.py 2>&1 | grep -v "ERROR" || true

# 启动服务
echo ""
echo "============================================================"
echo "启动Web服务..."
echo "============================================================"
echo "服务地址:"
echo "  - Web界面: http://localhost:8000"
echo "  - TensorBoard: http://localhost:6006"
echo ""
echo "按 Ctrl+C 停止服务"
echo "============================================================"
echo ""

python3.12 run.py

