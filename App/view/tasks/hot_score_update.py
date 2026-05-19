import logging
from django.db import connection
from models.models import Wallpapers

logger = logging.getLogger(__name__)

def update_hot_score_daily():
    logger.info("[HotScore] 开始极速更新热门评分...")
    print("\n[1/2] 正在计算全局统计值...")

    # 1. 先一次性算出全局最大最小（超快）
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                MIN(exposure_count), MAX(exposure_count),
                MIN(CAST(view_count AS FLOAT) / (exposure_count + 0.000001)),
                MAX(CAST(view_count AS FLOAT) / (exposure_count + 0.000001)),
                MIN(0.3 * like_count + 0.35 * collect_count + 0.35 * comment_count),
                MAX(0.3 * like_count + 0.35 * collect_count + 0.35 * comment_count),
                MIN(0.4 * download_count + 0.4 * CAST(download_count AS FLOAT) / NULLIF(view_count, 1)),
                MAX(0.4 * download_count + 0.4 * CAST(download_count AS FLOAT) / NULLIF(view_count, 1)),
                AVG(CAST(download_count AS FLOAT) / NULLIF(view_count, 1))
            FROM t_wallpapers
            WHERE audit_status != 'rejected'
        """)
        row = cursor.fetchone()

    min_e, max_e, min_c, max_c, min_cv, max_cv, min_b, max_b, avg_dr = row

    logger.info(f"统计完成，开始批量更新...")
    print(f"[2/2] 正在批量更新热门分数（极速模式）...")

    # 2. 单条 SQL 直接更新全部 70万 条！
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE t_wallpapers
            SET
                hot_score = GREATEST(
                    (
                        0.3 * ((exposure_count - %s) / (%s - %s + 0.000001)) +
                        0.3 * (( (CAST(view_count AS FLOAT) / (exposure_count + 0.000001)) - %s) / (%s - %s + 0.000001)) / 2 +
                        0.3 * (( (0.3 * like_count + 0.35 * collect_count + 0.35 * comment_count) - %s) / (%s - %s + 0.000001)) +
                        0.4 * ((
                            (0.4 * download_count + 0.4 * (CAST(download_count AS FLOAT) / NULLIF(view_count, 1))) *
                            CASE WHEN (CAST(download_count AS FLOAT) / NULLIF(view_count, 1)) > %s * 2 THEN 1.1 ELSE 1 END
                            - %s
                        ) / (%s - %s + 0.000001))
                    ) * 1000,
                    0
                ),
                updated_at = NOW()
            WHERE audit_status != 'rejected'
        """, [
            min_e, max_e, min_e,
            min_c, max_c, min_c,
            min_cv, max_cv, min_cv,
            avg_dr,
            min_b, max_b, min_b
        ])

    print("\n✅ 热门评分全部更新完成！[极速SQL模式]")
    logger.info("[HotScore] 更新完成！")