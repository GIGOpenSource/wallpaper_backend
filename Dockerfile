# 使用 Python 3.11 基础镜像适配 Django 5.2
FROM python:3.11-slim AS builder

# 配置国内源 + 网络优化
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_MAX_RETRIES=10
ENV PIP_NO_CACHE_DIR=0

# 配置国内pip源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --upgrade pip

# 创建依赖缓存目录
WORKDIR /app
RUN mkdir -p /app/.pip_cache /app/venv

# 复制依赖文件（仅req.txt，代码不变时这层不重建）
COPY req.txt .

# 安装依赖到独立虚拟环境（缓存核心）
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --cache-dir /app/.pip_cache -r req.txt

# 阶段2：运行层（仅复制依赖和代码，无下载）
FROM python:3.11-slim

# 继承环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=WallPaper.settings.pro
ENV PATH="/app/venv/bin:$PATH"

# 安装系统依赖（仅运行时需要，精简）
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从构建层复制虚拟环境（核心：复用已安装的依赖）
COPY --from=builder /app/venv /app/venv

# 复制项目文件（代码变化仅重建这层，无依赖下载）
COPY . .

# 创建静态文件目录
RUN mkdir -p /app/staticfiles /app/media && \
    chmod -R 755 /app/staticfiles /app/media

EXPOSE 8000
CMD sh -c "python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    python manage.py runserver 0.0.0.0:8000"