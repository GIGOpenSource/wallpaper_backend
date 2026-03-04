# 使用 Python 3.11 基础镜像适配 Django 5.2
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=FlashCicle.settings

# 配置国内pip源（解决依赖安装慢/失败问题）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --upgrade pip

# 设置工作目录
WORKDIR /app

# 安装系统依赖（PostgreSQL驱动+编译工具）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装Python依赖
COPY req.txt req.txt
RUN pip install --no-cache-dir -r req.txt

# 复制项目文件
COPY . .

# 创建静态文件/媒体文件目录并授权
RUN mkdir -p /app/staticfiles /app/media && \
    chmod -R 755 /app/staticfiles /app/media

# 暴露Django服务端口
EXPOSE 8000

# 启动命令（与compose中保持一致）
CMD sh -c "find . -path '*/migrations/*.py' -not -name '__init__.py' -delete && \
    find . -path '*/migrations/*.pyc' -delete && \
    python manage.py makemigrations && \
    python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    python manage.py runserver 0.0.0.0:8000"