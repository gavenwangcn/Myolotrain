#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检查脚本 - 检查项目启动所需的所有依赖
"""

import sys
import subprocess
import os

def check_python_version():
    """检查Python版本"""
    print("=" * 60)
    print("1. 检查Python版本...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 12:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro} (符合要求)")
        return True
    else:
        print(f"   ✗ Python {version.major}.{version.minor}.{version.micro} (需要3.12+)")
        return False

def check_venv():
    """检查虚拟环境"""
    print("\n2. 检查虚拟环境...")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"   ✓ 虚拟环境已激活: {sys.prefix}")
        return True
    else:
        venv_path = os.path.join(os.getcwd(), "venv")
        if os.path.exists(venv_path):
            print(f"   ⚠ 虚拟环境存在但未激活: {venv_path}")
            print(f"   请运行: source venv/bin/activate")
            return False
        else:
            print("   ✗ 虚拟环境不存在")
            print("   请运行: python3.12 setup_venv.py")
            return False

def check_dependencies():
    """检查关键依赖"""
    print("\n3. 检查关键依赖...")
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'psycopg2',
        'ultralytics',
        'torch'
    ]
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✓ {package}")
        except ImportError:
            print(f"   ✗ {package} (未安装)")
            missing.append(package)
    
    if missing:
        print(f"\n   缺少依赖: {', '.join(missing)}")
        print("   请运行: pip install -r requirements.txt")
        return False
    return True

def check_postgresql():
    """检查PostgreSQL"""
    print("\n4. 检查PostgreSQL...")
    
    # 检查psql命令
    try:
        result = subprocess.run(['which', 'psql'], capture_output=True, text=True)
        if result.returncode == 0:
            psql_path = result.stdout.strip()
            print(f"   ✓ psql 找到: {psql_path}")
        else:
            print("   ✗ psql 未找到 (PostgreSQL可能未安装)")
            print("   请参考 INSTALL_POSTGRES.md 安装PostgreSQL")
            return False
    except Exception as e:
        print(f"   ✗ 检查psql时出错: {e}")
        return False
    
    # 检查PostgreSQL服务
    try:
        result = subprocess.run(['pg_isready', '-h', 'localhost', '-p', '5432'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✓ PostgreSQL 服务正在运行")
            return True
        else:
            print("   ✗ PostgreSQL 服务未运行")
            print("   请启动PostgreSQL服务:")
            print("   - Postgres.app: 打开应用程序")
            print("   - Homebrew: brew services start postgresql@14")
            print("   - Docker: docker start postgres-yolo")
            return False
    except FileNotFoundError:
        print("   ✗ pg_isready 未找到 (PostgreSQL可能未安装)")
        print("   请参考 INSTALL_POSTGRES.md 安装PostgreSQL")
        return False
    except Exception as e:
        print(f"   ✗ 检查PostgreSQL服务时出错: {e}")
        return False

def check_database_connection():
    """检查数据库连接"""
    print("\n5. 检查数据库连接...")
    try:
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
            print("   ✓ 可以连接到PostgreSQL")
            return True
        except psycopg2.OperationalError as e:
            print(f"   ✗ 无法连接到PostgreSQL: {e}")
            print("   请检查:")
            print("   1. PostgreSQL服务是否运行")
            print("   2. 用户名和密码是否正确 (默认: postgres/postgres)")
            print("   3. 端口是否正确 (默认: 5432)")
            return False
    except ImportError:
        print("   ✗ psycopg2 未安装")
        return False
    except Exception as e:
        print(f"   ✗ 检查数据库连接时出错: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Myolotrain 环境检查")
    print("=" * 60)
    
    results = []
    results.append(check_python_version())
    results.append(check_venv())
    results.append(check_dependencies())
    results.append(check_postgresql())
    results.append(check_database_connection())
    
    print("\n" + "=" * 60)
    print("检查结果总结")
    print("=" * 60)
    
    if all(results):
        print("\n✓ 所有检查通过！可以启动项目")
        print("\n启动命令:")
        print("  source venv/bin/activate")
        print("  python3.12 run.py")
        return 0
    else:
        print("\n✗ 部分检查未通过，请根据上述提示修复问题")
        print("\n详细安装指南请参考:")
        print("  - INSTALL_POSTGRES.md (PostgreSQL安装)")
        print("  - README.md (完整文档)")
        return 1

if __name__ == "__main__":
    sys.exit(main())

