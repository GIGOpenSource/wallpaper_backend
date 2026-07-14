# 使用 Python 3.11 基础镜像
FROM python:3.11-slim AS builder

# 基础环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 构建阶段：创建虚拟环境安装依赖
WORKDIR /app
RUN mkdir -p /app/venv
COPY req.txt .

RUN python -m venv /app/venv && \
    /app/venv/bin/pip install -r req.txt

# 运行阶段
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=WallPaper.settings.pro
ENV PATH="/app/venv/bin:$PATH"

# 仅必要系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/venv /app/venv
COPY . .

RUN mkdir -p /app/media && \
    chmod -R 755 /app/media

EXPOSE 8000
# ✅ 删除 collectstatic，只运行 gunicorn；migrate 按需单独执行（不要放常驻启动命令）
CMD ["gunicorn", "WallPaper.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]