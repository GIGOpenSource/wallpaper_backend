#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import psycopg2
import psycopg2.extras
import logging
import sys
import time
from typing import List, Tuple
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import warnings

warnings.filterwarnings("ignore")

# ==================== 稳定代理配置（带重试机制） ====================
tunnel = "v353.kdlfps.com:18866"
username = "f2855151637"
password = "z1ag28gi"

# 代理配置
PROXY_URL = f"http://{username}:{password}@{tunnel}"
proxies = {
    "http": PROXY_URL,
    "https": PROXY_URL
}

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
TIMEOUT = 20
MAX_RETRIES = 3
REQUEST_DELAY = 0.5  # 每个请求之间的延迟


# 创建带重试机制的Session
def create_session():
    """创建带重试和连接池管理的Session"""
    session = requests.Session()
    session.proxies.update(proxies)
    session.verify = False

    # 重试策略
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,  # 重试间隔：1, 2, 4秒
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=5,

        pool_maxsize=5
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def check_proxy_alive() -> str:
    """校验代理是否可用，返回出口IP"""
    print("=== 校验隧道代理可用性 ===")
    session = create_session()

    try:
        # 使用ipinfo获取IP信息
        resp_ip = session.get(
            "https://ipinfo.io/",
            headers={"Connection": "close"},
            timeout=TIMEOUT
        )
        if resp_ip.status_code != 200:
            raise ConnectionError(f"代理校验失败，状态码:{resp_ip.status_code}")

        ip_info = resp_ip.json()
        export_ip = ip_info["ip"]
        print(f"✅ 代理正常，当前隧道出口IP: {export_ip} 地区:{ip_info.get('country', 'Unknown')}")

        # 测试壁纸链接
        test_img = "https://w.wallhaven.cc/full/p2/wallhaven-p2m7ve.jpg"
        resp_img = session.head(
            test_img,
            headers={"User-Agent": UA, "Connection": "close"},
            timeout=TIMEOUT,
            allow_redirects=True
        )
        if resp_img.status_code != 200:
            raise ConnectionError(f"壁纸测试链接访问失败，状态码:{resp_img.status_code}")
        print("✅ 壁纸测试链接访问正常，准备开始批量检测\n")

        return export_ip

    except Exception as e:
        raise ConnectionError(f"代理校验失败: {e}")


def head_check_url(target_url: str, retry_count: int = MAX_RETRIES) -> int:
    """
    HEAD检测壁纸链接状态码，带重试机制
    """
    session = create_session()

    headers = {
        "User-Agent": UA,
        "Connection": "close"
    }

    for attempt in range(retry_count):
        try:
            resp = session.head(
                target_url,
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            return resp.status_code

        except requests.exceptions.ProxyError as e:
            if "503" in str(e) or "Service Unavailable" in str(e):
                logging.warning(f"  -> 代理503错误 (尝试 {attempt + 1}/{retry_count})，等待后重试...")
                time.sleep(2 ** attempt)  # 指数退避
                continue
            raise
        except Exception as e:
            if attempt < retry_count - 1:
                logging.warning(f"  -> 请求异常 (尝试 {attempt + 1}/{retry_count}): {e}")
                time.sleep(1)
                continue
            raise

    raise RuntimeError(f"重试{retry_count}次后仍然失败")


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
    # 1. 启动先校验代理，失效直接退出

    try:
        export_ip = check_proxy_alive()
        logger.info(f"隧道代理已就绪，出口IP: {export_ip}")
    except Exception as e:
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
            # 请求延迟，避免触发限流
            if idx > 0.5:
                time.sleep(REQUEST_DELAY)

            # 通过隧道代理HEAD检测状态码（带重试）
            status_code = head_check_url(url)

            if status_code == 404:
                bad_ids.append(wid)
                logger.info(f"  -> 返回 404，标记失效")
            elif status_code == 200:
                logger.debug(f"  -> 状态正常 code={status_code}")
            else:
                logger.warning(f"  -> 返回状态码 {status_code}，跳过")

        except RuntimeError as e:
            logger.warning(f"  -> 链接访问异常，标记失效: {e}")
            bad_ids.append(wid)
        except requests.exceptions.ProxyError as e:
            # 代理彻底挂了，停止任务
            logger.error(f"❌ 隧道代理中断，终止检测任务: {e}")
            break
        except Exception as e:
            logger.error(f"❌ 未知错误: {e}")
            bad_ids.append(wid)

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