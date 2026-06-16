# check_404_wallpapers_proxy.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import psycopg2
import psycopg2.extras
import logging
import sys
from typing import List, Tuple

from check_wallpapers.KdlProxy import KdlTunnelProxy

# 导入独立代理类


# ========== PostgreSQL 数据库配置 ==========
DB_CONFIG = {
    'host': '101.32.179.223',
    'port': 5436,
    'user': 'wallpaper123',
    'password': 'wallpaper123',
    'database': 'wallpaper_db'
}

TABLE_NAME = 't_wallpapers'
ID_FIELD = 'id'
URL_FIELD = 'url'

REQUEST_TIMEOUT = 10
# ==========================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_wallpapers_in_range(conn, start_id: int, end_id: int) -> List[Tuple]:
    cursor = conn.cursor()
    sql = f"SELECT {ID_FIELD}, {URL_FIELD} FROM {TABLE_NAME} WHERE {ID_FIELD} BETWEEN %s AND %s"
    cursor.execute(sql, (start_id, end_id))
    result = cursor.fetchall()
    cursor.close()
    logger.info(f"查询到 {len(result)} 条壁纸记录 (id {start_id} ~ {end_id})")
    return result


def save_404_ids(ids: List[int], filename: str = "404_ids.txt"):
    with open(filename, 'w', encoding='utf-8') as f:
        for iid in ids:
            f.write(str(iid) + '\n')
    logger.info(f"404 壁纸 ID 已保存至 {filename}")


def main():
    # 1. 初始化隧道代理并检测可用性
    try:
        proxy = KdlTunnelProxy()
        proxy.check_proxy_alive()
    except ConnectionError as e:
        logger.error(f"❌ 隧道代理无法使用，程序终止: {e}")
        return

    # 2. 输入ID区间
    try:
        start = int(input("请输入起始 ID: "))
        end = int(input("请输入结束 ID: "))
        if start > end:
            logger.error("起始ID不能大于结束ID")
            return
    except ValueError:
        logger.error("ID 必须为整数")
        return

    # 3. 连接数据库
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("PostgreSQL 数据库连接成功")
    except psycopg2.Error as e:
        logger.error(f"数据库连接失败: {e}")
        return

    wallpapers = get_wallpapers_in_range(conn, start, end)
    if not wallpapers:
        logger.info("该范围内没有壁纸数据")
        conn.close()
        return

    bad_ids = []
    total = len(wallpapers)
    for idx, (wid, url) in enumerate(wallpapers, 1):
        logger.info(f"[{idx}/{total}] 检查 id={wid} : {url}")
        try:
            # 通过隧道代理HEAD检测状态码
            status_code = proxy.head_check_url(url)
            if status_code == 404:
                bad_ids.append(wid)
                logger.info(f"  -> 返回 404，标记失效")
            else:
                logger.debug(f"  -> 状态正常 code={status_code}")
        except RuntimeError as e:
            # 链接本身访问失败（超时/不存在）统一当作失效链接
            logger.warning(f"  -> 链接访问异常，标记失效: {e}")
            bad_ids.append(wid)
        except ConnectionError as e:
            # 代理彻底挂了，直接停止全部任务
            logger.error(f"❌ 隧道代理中断，终止检测任务: {e}")
            break

    conn.close()

    if bad_ids:
        logger.info(f"\n找到 {len(bad_ids)} 个失效壁纸 ID：")
        print("\n===== 失效壁纸 ID 列表 =====")
        print(bad_ids)
        print("============================\n")
        save_404_ids(bad_ids)
    else:
        logger.info("未发现任何失效壁纸")


if __name__ == "__main__":
    main()