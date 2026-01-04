#!/bin/bash
# 快速启动脚本

echo "============================================================"
echo "Myolotrain 快速启动脚本"
echo "============================================================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "错误: 虚拟环境不存在，请先运行: python3.12 setup_venv.py"
    exit 1
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查PostgreSQL
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
except psycopg2.OperationalError as e:
    print('✗ PostgreSQL连接失败:', e)
    print('')
    print('请先安装并启动PostgreSQL:')
    print('  1. 查看 INSTALL_POSTGRES.md 了解安装方法')
    print('  2. 或运行: python3.12 check_env.py 检查环境')
    exit(1)
" || exit 1

# 初始化数据库（如果需要）
echo "检查数据库..."
python3.12 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='yolov8_platform'
    )
    conn.close()
    print('✓ 数据库 yolov8_platform 已存在')
except psycopg2.OperationalError:
    print('初始化数据库...')
    import subprocess
    result = subprocess.run(['python3.12', 'init_db.py'], capture_output=True, text=True)
    if result.returncode == 0:
        print('✓ 数据库初始化成功')
    else:
        print('✗ 数据库初始化失败')
        print(result.stderr)
        exit(1)
" || exit 1

# 启动服务
echo ""
echo "============================================================"
echo "启动Web服务..."
echo "============================================================"
echo "服务将在以下地址启动:"
echo "  - Web界面: http://localhost:8000"
echo "  - TensorBoard: http://localhost:6006"
echo ""
echo "按 Ctrl+C 停止服务"
echo "============================================================"
echo ""

python3.12 run.py

