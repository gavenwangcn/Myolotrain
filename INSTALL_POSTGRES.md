# PostgreSQL 安装指南

## macOS 安装 PostgreSQL 的方法

### 方法1：使用 Postgres.app（推荐，最简单）

1. 下载 Postgres.app：https://postgresapp.com/
2. 解压并拖拽到 Applications 文件夹
3. 双击启动 Postgres.app
4. 点击 "Initialize" 初始化数据库
5. 默认配置：
   - 用户名：你的macOS用户名
   - 密码：无（或你设置的密码）
   - 端口：5432

**注意**：如果使用 Postgres.app，需要创建 postgres 用户：
```bash
# 在 Postgres.app 的终端中运行
createuser -s postgres
```

### 方法2：使用 Homebrew（需要修复权限）

1. 修复 Homebrew 权限：
```bash
sudo chown -R $(whoami) /usr/local/Homebrew
```

2. 安装 PostgreSQL：
```bash
brew install postgresql@14
```

3. 启动 PostgreSQL 服务：
```bash
brew services start postgresql@14
```

4. 创建 postgres 用户和数据库：
```bash
createuser -s postgres
createdb -U postgres yolov8_platform
```

### 方法3：使用 Docker（如果已安装 Docker）

```bash
docker run --name postgres-yolo -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=yolov8_platform -p 5432:5432 -d postgres:13
```

### 方法4：手动下载安装

从 PostgreSQL 官网下载 macOS 安装包：
https://www.postgresql.org/download/macosx/

## 验证安装

安装完成后，运行以下命令验证：

```bash
psql --version
pg_isready -h localhost -p 5432
```

## 配置项目

项目默认配置：
- 主机：localhost
- 端口：5432
- 用户名：postgres
- 密码：postgres
- 数据库：yolov8_platform

如果需要修改，请编辑 `app/core/config.py` 文件。

