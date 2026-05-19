import logging
from django.db import connection

logger = logging.getLogger(__name__)

def sync_wallpaper_all_counts():
    logger.info("[同步计数] 开始批量同步 评论/点赞/收藏 数量...")
    print("\n[1/3] 同步评论数...")

    # ----------------------
    # 评论数（PostgreSQL 语法）
    # ----------------------
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE t_wallpapers w
            SET comment_count = COALESCE(c.comment_count, 0)
            FROM (
                SELECT wallpaper_id, COUNT(*) AS comment_count
                FROM t_wallpaper_comment
                WHERE is_hidden = false
                GROUP BY wallpaper_id
            ) c
            WHERE w.id = c.wallpaper_id;
        """)

    print("[2/3] 同步点赞数...")
    # ----------------------
    # 点赞数
    # ----------------------
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE t_wallpapers w
            SET like_count = COALESCE(l.like_count, 0)
            FROM (
                SELECT wallpaper_id, COUNT(*) AS like_count
                FROM t_wallpaper_like
                GROUP BY wallpaper_id
            ) l
            WHERE w.id = l.wallpaper_id;
        """)

    print("[3/3] 同步收藏数...")
    # ----------------------
    # 收藏数
    # ----------------------
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE t_wallpapers w
            SET collect_count = COALESCE(col.collect_count, 0)
            FROM (
                SELECT wallpaper_id, COUNT(*) AS collect_count
                FROM t_wallpaper_collection
                GROUP BY wallpaper_id
            ) col
            WHERE w.id = col.wallpaper_id;
        """)

    print("\n✅ 同步完成！[PostgreSQL 批量极速模式]")
    logger.info("[同步计数] 同步完成！")