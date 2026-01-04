#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动安装PostgreSQL的脚本
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def download_postgres_app():
    """下载Postgres.app"""
    print("正在下载Postgres.app...")
    url = "https://github.com/PostgresApp/PostgresApp/releases/download/v2.9.1/Postgres-2.9.1-14.dmg"
    dmg_path = "/tmp/Postgres.dmg"
    
    try:
        print(f"从 {url} 下载...")
        urllib.request.urlretrieve(url, dmg_path)
        print(f"✓ 下载完成: {dmg_path}")
        print("\n请手动安装Postgres.app:")
        print(f"  1. 打开: {dmg_path}")
        print("  2. 将Postgres.app拖到Applications文件夹")
        print("  3. 双击启动Postgres.app")
        print("  4. 点击'Initialize'初始化数据库")
        print("  5. 在Postgres.app的终端中运行: createuser -s postgres")
        return True
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        return False

def try_brew_install():
    """尝试使用Homebrew安装"""
    print("尝试使用Homebrew安装PostgreSQL...")
    try:
        # 先尝试修复权限
        print("检查Homebrew权限...")
        result = subprocess.run(
            ["sudo", "chown", "-R", f"{os.getenv('USER')}", "/usr/local/Homebrew"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✓ 权限修复成功")
        else:
            print("⚠ 权限修复需要管理员密码，请手动运行:")
            print("  sudo chown -R $(whoami) /usr/local/Homebrew")
    except Exception as e:
        print(f"⚠ 权限修复失败: {e}")
    
    try:
        print("安装PostgreSQL...")
        result = subprocess.run(
            ["brew", "install", "postgresql@14"],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            print("✓ PostgreSQL安装成功")
            print("启动PostgreSQL服务...")
            subprocess.run(["brew", "services", "start", "postgresql@14"])
            return True
        else:
            print(f"✗ 安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ 安装过程出错: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("PostgreSQL 自动安装脚本")
    print("=" * 60)
    print()
    
    # 检查是否已安装
    if subprocess.run(["which", "psql"], capture_output=True).returncode == 0:
        print("✓ PostgreSQL已安装")
        # 检查服务是否运行
        result = subprocess.run(
            ["pg_isready", "-h", "localhost", "-p", "5432"],
            capture_output=True
        )
        if result.returncode == 0:
            print("✓ PostgreSQL服务正在运行")
            return 0
        else:
            print("⚠ PostgreSQL已安装但服务未运行")
            print("请启动PostgreSQL服务")
            return 1
    
    print("PostgreSQL未安装，尝试自动安装...")
    print()
    
    # 方法1: 尝试Homebrew
    if shutil.which("brew"):
        print("方法1: 使用Homebrew安装...")
        if try_brew_install():
            return 0
        print()
    
    # 方法2: 下载Postgres.app
    print("方法2: 下载Postgres.app...")
    if download_postgres_app():
        print("\n请按照上述说明手动安装Postgres.app")
        return 1
    
    print("\n" + "=" * 60)
    print("自动安装失败")
    print("=" * 60)
    print("\n请手动安装PostgreSQL，方法:")
    print("1. 访问 https://postgresapp.com/ 下载Postgres.app")
    print("2. 或运行: brew install postgresql@14")
    print("3. 或使用Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:13")
    print("\n详细说明请查看: INSTALL_POSTGRES.md")
    return 1

if __name__ == "__main__":
    sys.exit(main())

