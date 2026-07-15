FROM base-django-venv:v1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=WallPaper.settings.pro

# 必要系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN mkdir -p /app/media /app/logs && \
    chmod -R 755 /app/media /app/logs

EXPOSE 8000
# 生产用gunicorn（低配可改为workers=1）
CMD ["/venv/bin/gunicorn", "WallPaper.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
#CMD ["/venv/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]