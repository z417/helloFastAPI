# Starry Cinema 星空影城 - 极速上手与生产部署指南 (Quick Start)

> [!IMPORTANT]
> 本指南收录本地开发联调、生产级部署指令、高并发调优及全栈容器化配置。

---

## 一、 本地开发与联调指令

### 1.1 后端服务开发
在 `backend` 目录下通过 `uv` 极速进行依赖及服务管理：
```bash
# 安装并同步依赖
uv sync

# 额外添加依赖包
uv add <package_name>

# 启动本地开发服务 (自动读取 .env)
uv run uvicorn src.main:helloFastApi

# 运行本地回归单元测试
uv run pytest -v
```

### 1.2 前端服务开发
在 `frontend` 目录下通过 `bun` 运行极速宿主服务：
```bash
# 安装依赖
bun install

# 启动本地静态服务器
bun run server.js
```

---

## 二、 🚀 生产环境金牌部署指南

### 2.1 生产级裸机/源码部署
为防止 Dev 调试包（如 pytest）流入生产，请使用 `--no-dev` 参数：
```bash
# 纯净生产依赖同步
uv sync --no-dev

# 初始化生产 SQLite 数据库并导入种子数据
uv run python -c "from src.Cinema.seeder import run_reset_and_seed; import asyncio; from src.common.dependencies import get_async_engine; e=get_async_engine(); engine=asyncio.run(e.__anext__()); from src.common.dependencies import get_async_session; s=get_async_session(engine); session=asyncio.run(s.__anext__()); asyncio.run(run_reset_and_seed(session))"

# 多进程无热载启动后端
uv run uvicorn src.main:helloFastApi --workers 4
```

### 2.2 💡 前端 API 自适应与构建时环境注入
前端内置智能地址自适应逻辑，且在 `bun build` 编译时支持常量注入与死码消除：
```javascript
const API_BASE_URL = (typeof process !== "undefined" && process.env && process.env.API_URL)
    ? process.env.API_URL
    : ((window.location.port && window.location.port !== "8000")
        ? `${window.location.protocol}//${window.location.hostname}:8000/api`
        : "/api");
```
- **方案 A (.env 注入)**：在 `frontend` 目录下建立 `.env` 声明 `API_URL=https://prod.cinema-api.com/api`，再执行 `bun build ./app.js --minify --outfile=./dist/app.js`。
- **方案 B (CLI 注入)**：直接指定映射覆盖：
  ```bash
  bun build ./app.js --minify --outfile=./dist/app.js --define "process.env.API_URL='https://prod.cinema-api.com/api'"
  ```

### 2.3 生产级 `.env` 环境变量配置
在 `backend/.env` 写入以下高并发优化配置：
```ini
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_RELOAD=False
ENABLE_API_DOCS=False

# DB_URL 可配置为 sqlite+aiosqlite:////app/db.sqlite 或 postgresql+asyncpg://user:pass@host:port/dbname
DB_URL=sqlite+aiosqlite:////app/db.sqlite
DB_POOL_MODE=queue

# 并发锁模式：pessimistic (悲观锁) | optimistic (乐观锁)；秒杀推荐使用 optimistic
BOOKING_LOCK_MODE=optimistic

# 生产级安全防护
BOOKING_SIGNATURE_CHECK=True
APP_SECRET_KEY=prod_super_secret_cryptographic_key_998811
```

### 2.4 云原生容器化部署 (Docker Compose)
项目根目录下 `docker-compose.yml` 编排配置：
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: cinema-backend
    restart: always
    environment:
      - ENV_FILE=.env
    volumes:
      - cinema-db-volume:/app
    expose:
      - "8000"
    networks:
      - cinema-network

  nginx:
    image: nginx:alpine
    container_name: cinema-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - backend
    networks:
      - cinema-network

volumes:
  cinema-db-volume:

networks:
  cinema-network:
    driver: bridge
```

### 2.5 高并发 Nginx 反向代理配置
项目根目录下高性能 `nginx.conf` 动静分离反代配置：
```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 10240;
    multi_accept on;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    gzip on;
    gzip_disable "msie6";
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    upstream backend_servers {
        server backend:8000;
        keepalive 100;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
            gzip_static on;
            expires 7d;
            add_header Cache-Control "public, no-transform";
        }

        location /api/ {
            proxy_pass http://backend_servers;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 5s;
            proxy_read_timeout 30s;
            proxy_send_timeout 30s;
        }
    }
}
```

### 2.6 ⚡ 前端代码极限压缩与静态预压缩
为将首屏加载与传输响应提升至极致，结合 Bun 的混淆混淆与 Nginx `gzip_static` 预压缩：
```bash
# 1. 建立打包发布目录并进行极限 Tree-Shaking 压缩混淆
mkdir -p dist
bun build ./app.js --minify --outfile=./dist/app.js
cp ./index.html ./dist/

# 2. 预先物理生成最高级别 (9) 静态 Gzip 预压缩包 (消除动态 Gzip 对 CPU 的损耗)
cd dist
gzip -9 -k -f index.html app.js
```
**生产目录 `frontend/dist/` 结构**：
- `index.html` 与 `index.html.gz` (体积缩减 75%+)
- `app.js` 与 `app.js.gz` (体积缩减 80%+)

### 2.7 🐳 容器发布与维护命令
```bash
# 全栈静默构建启动
docker compose up -d --build

# 后端平滑无中断重载
docker compose build backend
docker compose up -d --no-deps backend

# 容器内手动还原初始化数据库并导入种子数据
docker compose exec backend uv run python -c "from src.Cinema.seeder import run_reset_and_seed; import asyncio; from src.common.dependencies import get_async_engine; e=get_async_engine(); engine=asyncio.run(e.__anext__()); from src.common.dependencies import get_async_session; s=get_async_session(engine); session=asyncio.run(s.__anext__()); asyncio.run(run_reset_and_seed(session))"
```

### 2.8 🚀 操作系统级高并发优化 (OS Tweaks)
当抢票并发峰值极大时，宿主服务器必须调高文件句柄及回收 TIME_WAIT 连接。
- 在 `/etc/security/limits.conf` 追加：
  ```text
  * soft nofile 65535
  * hard nofile 65535
  ```
- 在 `/etc/sysctl.conf` 追加：
  ```ini
  net.ipv4.tcp_tw_reuse = 1
  net.ipv4.tcp_fin_timeout = 15
  net.ipv4.ip_local_port_range = 1024 65535
  net.core.somaxconn = 4096
  ```
  生效指令：`sudo sysctl -p`
