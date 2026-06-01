FROM python:3.12-slim-bookworm
LABEL maintainer="Yuri"
LABEL version="1.0.0"

# 引入官方 uv 极速包管理工具
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 设置标准 Python 容器环境变量，强力保障日志实时输出与环境隔离
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENV_FILE=.env \
    PYTHONPATH=/app \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# 首先复制依赖声明文件以最大化利用 Docker 构建缓存层
COPY pyproject.toml uv.lock ./

# 使用 uv 同步安装项目所有依赖（冻结锁定版本，并且进行字节码预编译以加速启动）
RUN uv sync --frozen --no-install-project

# 复制其余的项目代码
COPY . /app

EXPOSE 8000

# 通过 uv run 启动服务，自动加载虚拟环境中的依赖，并执行入口程序
CMD ["uv", "run", "src/main.py"]
