# 使用 Python 3.11 基础镜像
FROM python:3.11-slim AS builder

# 基础环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 构建阶段：创建虚拟环境安装依赖（放到 /venv，不是 /app/venv）
WORKDIR /app
COPY req.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install -r req.txt

# 运行阶段
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=WallPaper.settings.pro

# 仅必要系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
# 复制虚拟环境到容器根目录 /venv
COPY --from=builder /venv /venv
COPY . .

RUN mkdir -p /app/media /app/logs && \
    chmod -R 755 /app/media /app/logs

EXPOSE 8000
# 默认CMD
CMD ["/venv/bin/gunicorn", "WallPaper.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]