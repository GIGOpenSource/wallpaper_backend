# check_migrations.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WallPaper.settings.pro')
django.setup()

from django.db import connection

# 检查 django_migrations 表
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, app, name, applied 
        FROM django_migrations 
        WHERE app = 'models' 
        ORDER BY id;
    """)
    rows = cursor.fetchall()
    print("=== 已应用的迁移记录 ===")
    for row in rows:
        print(f"ID: {row[0]}, 名称: {row[1]}.{row[2]}, 应用时间: {row[3]}")

    # 检查表是否存在
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name LIKE 't_%'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    print("\n=== 数据库中实际存在的表 ===")
    for table in tables:
        print(f"表名: {table[0]}")
