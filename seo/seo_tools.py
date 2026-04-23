# -*- coding: UTF-8 -*-
"""
SEO 工具类 - Google Search Console API 集成
"""
import os
from datetime import datetime, timedelta

import httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleSearchConsoleTool:
    """Google Search Console API 工具类"""

    # Search Console API 作用域
    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize()

    def _initialize(self):
        try:
            key_file = os.getenv('GOOGLE_SEARCH_CONSOLE_KEY_FILE')
            if not key_file:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                key_file = os.path.join(base_dir, 'resource', 'key', 'search-console-key.json')

            if not os.path.exists(key_file):
                print(f"❌ 密钥不存在: {key_file}")
                self.service = None
                return

            self.credentials = service_account.Credentials.from_service_account_file(
                key_file, scopes=self.SCOPES
            )
            # 直接 build，不用代理
            self.service = build('searchconsole', 'v1', credentials=self.credentials)
            print("✅ GSC 初始化成功")
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.service = None



    def get_search_analytics(self, site_url, start_date, end_date, dimensions=None):
        """获取搜索分析数据"""
        if not self.service:
            print(f"⚠️ Search Console 服务未初始化，返回空数据")
            return []

        try:
            request_body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions or [],
                'rowLimit': 25000,
                'startRow': 0,
                'aggregationType': 'auto'
            }

            print(f"🔍 调用 Search Console API: site={site_url}, dates={start_date} to {end_date}")

            response = self.service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()

            rows = response.get('rows', [])
            print(f"📊 返回数据行数: {len(rows)}")

            return rows
        except Exception as e:
            print(f"❌ 获取搜索分析数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_site_performance(self, site_url, days=30):
        """
        获取网站整体性能数据

        Args:
            site_url: 网站 URL
            days: 天数，默认 30 天

        Returns:
            性能数据字典
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        rows = self.get_search_analytics(site_url, start_date, end_date)

        if not rows:
            return {
                'total_clicks': 0,
                'total_impressions': 0,
                'avg_ctr': 0,
                'avg_position': 0,
                'period_days': days
            }

        total_clicks = sum(row['clicks'] for row in rows)
        total_impressions = sum(row['impressions'] for row in rows)
        avg_ctr = total_clicks / total_impressions * 100 if total_impressions > 0 else 0
        avg_position = sum(
            row['position'] * row['impressions'] for row in rows) / total_impressions if total_impressions > 0 else 0

        return {
            'total_clicks': round(total_clicks, 2),
            'total_impressions': round(total_impressions, 2),
            'avg_ctr': round(avg_ctr, 2),
            'avg_position': round(avg_position, 2),
            'period_days': days
        }

    def get_top_queries(self, site_url, days=30, limit=10):
        """
        获取热门搜索查询

        Args:
            site_url: 网站 URL
            days: 天数
            limit: 返回数量限制

        Returns:
            热门搜索查询列表
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        rows = self.get_search_analytics(
            site_url,
            start_date,
            end_date,
            dimensions=['query']
        )

        if not rows:
            return []

        sorted_rows = sorted(rows, key=lambda x: x['clicks'], reverse=True)[:limit]

        return [
            {
                'query': row['keys'][0],
                'clicks': round(row['clicks'], 2),
                'impressions': round(row['impressions'], 2),
                'ctr': round(row['ctr'] * 100, 2),
                'position': round(row['position'], 2)
            }
            for row in sorted_rows
        ]

    def get_top_pages(self, site_url, days=30, limit=10):
        """
        获取热门页面

        Args:
            site_url: 网站 URL
            days: 天数
            limit: 返回数量限制

        Returns:
            热门页面列表
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        rows = self.get_search_analytics(
            site_url,
            start_date,
            end_date,
            dimensions=['page']
        )

        if not rows:
            return []

        sorted_rows = sorted(rows, key=lambda x: x['clicks'], reverse=True)[:limit]

        return [
            {
                'page': row['keys'][0],
                'clicks': round(row['clicks'], 2),
                'impressions': round(row['impressions'], 2),
                'ctr': round(row['ctr'] * 100, 2),
                'position': round(row['position'], 2)
            }
            for row in sorted_rows
        ]

    def get_country_data(self, site_url, days=30, limit=10):
        """
        获取国家/地区数据

        Args:
            site_url: 网站 URL
            days: 天数
            limit: 返回数量限制

        Returns:
            国家/地区数据列表
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        rows = self.get_search_analytics(
            site_url,
            start_date,
            end_date,
            dimensions=['country']
        )

        if not rows:
            return []

        sorted_rows = sorted(rows, key=lambda x: x['clicks'], reverse=True)[:limit]

        return [
            {
                'country': row['keys'][0],
                'clicks': round(row['clicks'], 2),
                'impressions': round(row['impressions'], 2),
                'ctr': round(row['ctr'] * 100, 2),
                'position': round(row['position'], 2)
            }
            for row in sorted_rows
        ]

    def get_device_data(self, site_url, days=30):
        """
        获取设备类型数据

        Args:
            site_url: 网站 URL
            days: 天数

        Returns:
            设备类型数据列表
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        rows = self.get_search_analytics(
            site_url,
            start_date,
            end_date,
            dimensions=['device']
        )

        if not rows:
            return []

        return [
            {
                'device': row['keys'][0],
                'clicks': round(row['clicks'], 2),
                'impressions': round(row['impressions'], 2),
                'ctr': round(row['ctr'] * 100, 2),
                'position': round(row['position'], 2)
            }
            for row in rows
        ]

    def calculate_seo_health_score(self, site_url, days=30):
        """
        计算 SEO 健康度评分 (0-100)

        评分维度：
        - 点击率 (CTR): 25%
        - 平均排名: 25%
        - 索引覆盖率: 25%
        - 移动端友好度: 25%

        Args:
            site_url: 网站 URL
            days: 天数

        Returns:
            SEO 健康度评分和详细数据
        """
        performance = self.get_site_performance(site_url, days)

        # 1. 点击率评分 (0-25)
        ctr = performance['avg_ctr']
        ctr_score = min(25, (ctr / 5) * 25) if ctr > 0 else 0

        # 2. 平均排名评分 (0-25)
        position = performance['avg_position']
        position_score = max(0, 25 - (position - 1) * 2.5) if position > 0 else 0

        # 3. 索引覆盖率评分 (0-25)
        impressions = performance['total_impressions']
        coverage_score = min(25, (impressions / 10000) * 25) if impressions > 0 else 0

        # 4. 移动端友好度评分 (0-25)
        device_data = self.get_device_data(site_url, days)
        mobile_data = next((d for d in device_data if d['device'] == 'MOBILE'), None)
        mobile_score = 20 if mobile_data else 10

        # 总分
        total_score = round(ctr_score + position_score + coverage_score + mobile_score, 2)

        return {
            'health_score': min(100, total_score),
            'details': {
                'ctr_score': round(ctr_score, 2),
                'position_score': round(position_score, 2),
                'coverage_score': round(coverage_score, 2),
                'mobile_score': round(mobile_score, 2)
            },
            'performance': performance
        }


# 全局实例
gsc_tool = GoogleSearchConsoleTool()
