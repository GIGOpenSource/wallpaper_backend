# -*- coding: UTF-8 -*-
"""
SEO 工具类 - Google Search Console API 集成
支持关键词挖掘、外链管理等第三方 SEO 工具 API
"""
import os
from datetime import datetime, timedelta

import httplib2
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp


class GoogleSearchConsoleTool:
    """Google Search Console API 工具类"""

    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

    def __init__(self):
        self.credentials = None
        self.service = None
        self._initialize()

    def _initialize(self):
        """初始化 Google Search Console 服务"""
        try:
            key_file = os.getenv('GOOGLE_SEARCH_CONSOLE_KEY_FILE')

            if not key_file:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                key_file = os.path.join(base_dir, 'resource', 'key', 'search-console-key.json')

            key_file = os.path.abspath(key_file)

            if not os.path.exists(key_file):
                print(f"❌ Google Search Console 密钥文件不存在: {key_file}")
                self.service = None
                return

            with open(key_file, 'r', encoding='utf-8') as f:
                import json
                key_data = json.load(f)
                print(f"✅ 成功读取密钥文件: {key_file}")
                print(f"📋 项目ID: {key_data.get('project_id', 'N/A')}")
                print(f"📧 客户端邮箱: {key_data.get('client_email', 'N/A')}")

            self.credentials = service_account.Credentials.from_service_account_file(
                key_file,
                scopes=self.SCOPES
            )

            use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
            if use_proxy:
                proxy_host = os.getenv('PROXY_HOST', '127.0.0.1')
                proxy_port = int(os.getenv('PROXY_PORT', '7897'))
                print(f"🌐 代理配置: {proxy_host}:{proxy_port}")
                http = httplib2.Http(
                    proxy_info=httplib2.ProxyInfo(
                        httplib2.socks.PROXY_TYPE_HTTP,
                        proxy_host,
                        proxy_port
                    )
                )
            else:
                print(f"🌐 不使用代理，直接连接")
                http = httplib2.Http()
            authed_http = AuthorizedHttp(self.credentials, http=http)
            self.service = build('searchconsole', 'v1', http=authed_http)
            print(f"✅ Google Search Console 初始化成功")
        except json.JSONDecodeError as e:
            print(f"❌ 密钥文件格式错误: {e}")
            self.service = None
        except Exception as e:
            print(f"❌ Google Search Console 初始化失败: {e}")
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

    def get_backlinks_report(self, site_url, days=90):
        """
        从 Google Search Console 获取外链报告（基础数据）

        Args:
            site_url: 网站 URL
            days: 天数，默认 90 天

        Returns:
            外链数据列表
        """
        if not self.service:
            print(f"⚠️ Search Console 服务未初始化，返回空数据")
            return []

        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            response = self.service.sites().list().execute()
            sites = response.get('siteEntry', [])

            for site in sites:
                if site.get('siteUrl') == site_url:
                    backlinks_response = self.service.sites().get(siteUrl=site_url).execute()
                    return backlinks_response

            return []
        except Exception as e:
            print(f"❌ 获取外链报告失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_search_type_data(self, site_url, days=30):
        """
        获取不同搜索类型的数据（Web、图片、视频、新闻）
        
        Args:
            site_url: 网站 URL
            days: 天数
            
        Returns:
            各搜索类型的数据列表
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        search_types = ['web', 'image', 'video', 'news']
        results = []
        
        for search_type in search_types:
            rows = self.get_search_analytics(
                site_url,
                start_date,
                end_date,
                dimensions=['query', 'page']
            )
            
            if rows:
                total_clicks = sum(row['clicks'] for row in rows)
                total_impressions = sum(row['impressions'] for row in rows)
                avg_ctr = total_clicks / total_impressions * 100 if total_impressions > 0 else 0
                avg_position = sum(
                    row['position'] * row['impressions'] for row in rows
                ) / total_impressions if total_impressions > 0 else 0
                
                results.append({
                    'search_type': search_type,
                    'total_clicks': round(total_clicks, 2),
                    'total_impressions': round(total_impressions, 2),
                    'avg_ctr': round(avg_ctr, 2),
                    'avg_position': round(avg_position, 2)
                })
        
        return results

    def get_performance_trend(self, site_url, days=30, granularity='day'):
        """
        获取性能趋势数据（按天/周/月）
        
        Args:
            site_url: 网站 URL
            days: 天数
            granularity: 粒度 'day', 'week', 'month'
            
        Returns:
            时间序列数据列表
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        trend_data = []
        current_date = start_date
        
        while current_date <= end_date:
            if granularity == 'day':
                period_end = current_date
                period_start = current_date
                current_date += timedelta(days=1)
            elif granularity == 'week':
                period_start = current_date
                period_end = current_date + timedelta(days=6)
                if period_end > end_date:
                    period_end = end_date
                current_date = period_end + timedelta(days=1)
            else:  # month
                period_start = current_date
                next_month = current_date.replace(day=28) + timedelta(days=4)
                period_end = min(next_month - timedelta(days=next_month.day), end_date)
                current_date = period_end + timedelta(days=1)
            
            rows = self.get_search_analytics(
                site_url,
                period_start.strftime('%Y-%m-%d'),
                period_end.strftime('%Y-%m-%d')
            )
            
            if rows:
                total_clicks = sum(row['clicks'] for row in rows)
                total_impressions = sum(row['impressions'] for row in rows)
                avg_ctr = total_clicks / total_impressions * 100 if total_impressions > 0 else 0
                avg_position = sum(
                    row['position'] * row['impressions'] for row in rows
                ) / total_impressions if total_impressions > 0 else 0
                
                trend_data.append({
                    'date': period_start.strftime('%Y-%m-%d'),
                    'end_date': period_end.strftime('%Y-%m-%d'),
                    'clicks': round(total_clicks, 2),
                    'impressions': round(total_impressions, 2),
                    'ctr': round(avg_ctr, 2),
                    'position': round(avg_position, 2)
                })
        
        return trend_data

    def get_top_queries_by_position(self, site_url, days=30, position_range='1-10'):
        """
        根据排名范围获取热门查询
        
        Args:
            site_url: 网站 URL
            days: 天数
            position_range: 排名范围 '1-3', '4-10', '11-20', '21-50', '51-100'
            
        Returns:
            查询列表
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
        
        # 解析排名范围
        pos_min, pos_max = map(int, position_range.split('-'))
        filtered_rows = [row for row in rows if pos_min <= row['position'] <= pos_max]
        
        if not filtered_rows:
            return []
        
        sorted_rows = sorted(filtered_rows, key=lambda x: x['clicks'], reverse=True)[:20]
        
        return [
            {
                'query': row['keys'][0],
                'clicks': round(row['clicks'], 2),
                'impressions': round(row['impressions'], 2),
                'ctr': round(row['ctr'] * 100, 2),
                'position': round(row['position'], 2),
                'opportunity': 'high' if row['impressions'] > 1000 and row['position'] > 5 else 'medium'
            }
            for row in sorted_rows
        ]

    def get_mobile_usability_issues(self, site_url):
        """
        获取移动可用性问题（需要 PageSpeed Insights API）
        
        Args:
            site_url: 网站 URL
            
        Returns:
            移动可用性问题列表
        """
        api_key = os.getenv('GOOGLE_PAGESPEED_API_KEY')
        if not api_key:
            print("⚠️ Google PageSpeed API Key 未配置")
            return []
        
        try:
            url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            params = {
                'url': site_url,
                'key': api_key,
                'category': 'MOBILE_USABILITY'
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            issues = []
            audits = data.get('lighthouseResult', {}).get('audits', {})
            
            for audit_id, audit_data in audits.items():
                if audit_data.get('score') is not None and audit_data['score'] < 1:
                    issues.append({
                        'id': audit_id,
                        'title': audit_data.get('title', ''),
                        'description': audit_data.get('description', ''),
                        'score': audit_data.get('score', 0),
                        'severity': audit_data.get('details', {}).get('items', [{}])[0].get('severity', 'medium')
                    })
            
            return issues
        except Exception as e:
            print(f"❌ 获取移动可用性问题失败: {e}")
            return []

    def get_core_web_vitals(self, site_url):
        """
        获取核心网页指标 (Core Web Vitals)
        
        Args:
            site_url: 网站 URL
            
        Returns:
            Core Web Vitals 数据
        """
        api_key = os.getenv('GOOGLE_PAGESPEED_API_KEY')
        if not api_key:
            print("⚠️ Google PageSpeed API Key 未配置")
            return {}
        
        try:
            url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            params = {
                'url': site_url,
                'key': api_key,
                'category': 'PERFORMANCE'
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            metrics = data.get('lighthouseResult', {}).get('audits', {})
            
            return {
                'lcp': metrics.get('largest-contentful-paint', {}).get('numericValue', 0),
                'fid': metrics.get('max-potential-fid', {}).get('numericValue', 0),
                'cls': metrics.get('cumulative-layout-shift', {}).get('numericValue', 0),
                'fcp': metrics.get('first-contentful-paint', {}).get('numericValue', 0),
                'speed_index': metrics.get('speed-index', {}).get('numericValue', 0),
                'performance_score': data.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', 0) * 100
            }
        except Exception as e:
            print(f"❌ 获取 Core Web Vitals 失败: {e}")
            return {}

    def get_sitemap_status(self, site_url):
        """
        获取 Sitemap 提交状态
        
        Args:
            site_url: 网站 URL
            
        Returns:
            Sitemap 状态信息
        """
        if not self.service:
            return []
        
        try:
            response = self.service.sitemaps().list(siteUrl=site_url).execute()
            sitemaps = response.get('sitemap', [])
            
            return [
                {
                    'path': sitemap.get('path', ''),
                    'type': sitemap.get('type', ''),
                    'is_pending': sitemap.get('isPending', False),
                    'is_sitemap_index': sitemap.get('isSitemapIndex', False),
                    'last_submitted': sitemap.get('lastSubmitted', ''),
                    'errors': sitemap.get('errors', 0),
                    'warnings': sitemap.get('warnings', 0)
                }
                for sitemap in sitemaps
            ]
        except Exception as e:
            print(f"❌ 获取 Sitemap 状态失败: {e}")
            return []

    def get_index_coverage_summary(self, site_url):
        """
        获取索引覆盖率摘要
        
        Args:
            site_url: 网站 URL
            
        Returns:
            索引覆盖数据
        """
        if not self.service:
            return {}
        
        try:
            # 注意：Index Coverage API 在 GSC API v1 中不可用
            # 这里返回模拟数据结构，实际需要使用 Search Console UI 或其他工具
            return {
                'note': 'Index Coverage API 需要通过 Search Console UI 查看',
                'recommendation': '建议定期在 GSC 中检查“索引”报告'
            }
        except Exception as e:
            print(f"❌ 获取索引覆盖率失败: {e}")
            return {}


class KeywordResearchTool:
    """关键词研究工具类 - 支持多个第三方 API"""

    def __init__(self):
        self.semrush_api_key = os.getenv('SEMRUSH_API_KEY')
        self.ahrefs_api_key = os.getenv('AHREFS_API_KEY')
        self.keyword_planner_client_id = os.getenv('GOOGLE_KEYWORD_PLANNER_CLIENT_ID')
        self.keyword_planner_client_secret = os.getenv('GOOGLE_KEYWORD_PLANNER_CLIENT_SECRET')
        self.keyword_planner_developer_token = os.getenv('GOOGLE_KEYWORD_PLANNER_DEVELOPER_TOKEN')
        use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
        if use_proxy:
            self.proxy_config = {
                'http': os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890'),
                'https': os.getenv('HTTPS_PROXY', 'http://127.0.0.1:7890')
            }
        else:
            self.proxy_config = None

    def _make_request(self, url, params=None, headers=None, method='GET'):
        """统一的请求方法，支持代理"""
        try:
            proxies = self.proxy_config if self.proxy_config.get('http') else None

            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers,
                                        proxies=proxies, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=params, headers=headers,
                                         proxies=proxies, timeout=30)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API 请求失败: {url}, 错误: {e}")
            return None

    def semrush_keyword_research(self, keyword, country='us', limit=100):
        """
        使用 SEMrush API 进行关键词研究

        Args:
            keyword: 种子关键词
            country: 国家代码，默认 'us'
            limit: 返回结果数量限制

        Returns:
            关键词数据列表
        """
        if not self.semrush_api_key:
            print("⚠️ SEMrush API Key 未配置")
            return []

        base_url = "https://api.semrush.com/"
        params = {
            'type': 'phrase_related',
            'key': self.semrush_api_key,
            'database': country,
            'phrase': keyword,
            'display_limit': limit,
            'export_columns': 'Ph,Nq,Cp,Co,Nr,Td',
            'display_unit': 'id'
        }

        data = self._make_request(base_url, params=params)

        if not data:
            return []

        keywords = []
        for row in data.get('data', []):
            if len(row) >= 6:
                keywords.append({
                    'keyword': row[0],
                    'search_volume': int(row[1]) if row[1] else 0,
                    'cpc': float(row[2]) if row[2] else 0,
                    'competition': float(row[3]) if row[3] else 0,
                    'trend': row[5] if len(row) > 5 else '',
                    'source': 'SEMrush'
                })

        return keywords

    def ahrefs_keyword_research(self, keyword, country='us', limit=100):
        """
        使用 Ahrefs API 进行关键词研究

        Args:
            keyword: 种子关键词
            country: 国家代码，默认 'us'
            limit: 返回结果数量限制

        Returns:
            关键词数据列表
        """
        if not self.ahrefs_api_key:
            print("⚠️ Ahrefs API Key 未配置")
            return []

        base_url = "https://open.api.ahrefs.com/v3/keywords/metrics"
        headers = {
            'Authorization': f'Bearer {self.ahrefs_api_key}',
            'Content-Type': 'application/json'
        }

        params = {
            'keywords': [keyword],
            'location_code': self._get_location_code(country),
            'language_code': 'en'
        }

        data = self._make_request(base_url, params=params, headers=headers, method='POST')

        if not data:
            return []

        keywords = []
        for item in data.get('items', []):
            keywords.append({
                'keyword': item.get('keyword', ''),
                'search_volume': item.get('search_volume', 0),
                'cpc': item.get('cpc', 0),
                'competition': item.get('competition_level', 'UNKNOWN'),
                'difficulty': item.get('keyword_difficulty', 0),
                'source': 'Ahrefs'
            })

        return keywords

    def generate_long_tail_keywords(self, seed_keyword, modifiers=None):
        """
        生成长尾关键词（基于规则生成，无需 API）

        Args:
            seed_keyword: 种子关键词
            modifiers: 修饰词列表

        Returns:
            长尾关键词列表
        """
        if modifiers is None:
            modifiers = {
                'questions': ['how to', 'what is', 'why', 'when', 'where', 'best way to'],
                'modifiers': ['best', 'top', 'free', 'cheap', 'review', 'guide', 'tutorial'],
                'locations': ['near me', 'in usa', 'online', '2024', '2025'],
                'actions': ['download', 'buy', 'find', 'create', 'make']
            }

        long_tail_keywords = []

        for category, words in modifiers.items():
            for word in words:
                long_tail_keywords.append({
                    'keyword': f"{word} {seed_keyword}",
                    'type': category,
                    'estimated_volume': 'low',
                    'competition': 'low',
                    'source': 'Generated'
                })
                long_tail_keywords.append({
                    'keyword': f"{seed_keyword} {word}",
                    'type': category,
                    'estimated_volume': 'low',
                    'competition': 'low',
                    'source': 'Generated'
                })

        return long_tail_keywords

    def analyze_keyword_difficulty(self, keyword, search_volume=None, cpc=None):
        """
        分析关键词难度（综合评估）

        Args:
            keyword: 关键词
            search_volume: 搜索量
            cpc: 每次点击费用

        Returns:
            难度分析结果
        """
        difficulty_score = 0
        factors = []

        if search_volume:
            if search_volume > 100000:
                difficulty_score += 30
                factors.append('高搜索量竞争激烈')
            elif search_volume > 10000:
                difficulty_score += 20
                factors.append('中等搜索量')
            else:
                difficulty_score += 10
                factors.append('低搜索量，竞争较小')

        if cpc:
            if cpc > 5:
                difficulty_score += 25
                factors.append('高 CPC，商业价值高')
            elif cpc > 2:
                difficulty_score += 15
                factors.append('中等 CPC')
            else:
                difficulty_score += 5
                factors.append('低 CPC')

        word_count = len(keyword.split())
        if word_count <= 2:
            difficulty_score += 25
            factors.append('短尾词，竞争激烈')
        elif word_count <= 4:
            difficulty_score += 15
            factors.append('中尾词')
        else:
            difficulty_score += 5
            factors.append('长尾词，容易优化')

        difficulty_score = min(100, difficulty_score)

        if difficulty_score >= 70:
            level = '困难'
        elif difficulty_score >= 40:
            level = '中等'
        else:
            level = '简单'

        return {
            'keyword': keyword,
            'difficulty_score': difficulty_score,
            'difficulty_level': level,
            'factors': factors,
            'recommendation': self._get_recommendation(difficulty_score)
        }

    def _get_recommendation(self, score):
        """根据难度分数给出建议"""
        if score >= 70:
            return "建议寻找相关长尾词，或提升域名权威度后再尝试"
        elif score >= 40:
            return "可以优化，需要高质量内容和适当的外链支持"
        else:
            return "容易优化的关键词，建议优先布局"

    def _get_location_code(self, country):
        """将国家代码转换为 Ahrefs 位置代码"""
        location_map = {
            'us': 2840,
            'cn': 2156,
            'gb': 2826,
            'de': 2276,
            'fr': 2250,
            'jp': 2392,
            'kr': 2410,
        }
        return location_map.get(country.lower(), 2840)


class BacklinkMonitorTool:
    """外链监控工具类 - 支持多个第三方 API"""

    def __init__(self):
        self.ahrefs_api_key = os.getenv('AHREFS_API_KEY')
        self.majestic_api_key = os.getenv('MAJESTIC_API_KEY')
        self.semrush_api_key = os.getenv('SEMRUSH_API_KEY')
        use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
        if use_proxy:
            self.proxy_config = {
                'http': os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890'),
                'https': os.getenv('HTTPS_PROXY', 'http://127.0.0.1:7890')
            }
        else:
            self.proxy_config = None

    def _make_request(self, url, params=None, headers=None, method='GET'):
        """统一的请求方法，支持代理"""
        try:
            proxies = self.proxy_config if self.proxy_config.get('http') else None

            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers,
                                        proxies=proxies, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=params, headers=headers,
                                         proxies=proxies, timeout=30)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API 请求失败: {url}, 错误: {e}")
            return None

    def ahrefs_backlinks(self, domain, limit=100):
        """
        使用 Ahrefs API 获取外链数据

        Args:
            domain: 域名
            limit: 返回结果数量限制

        Returns:
            外链数据列表
        """
        if not self.ahrefs_api_key:
            print("⚠️ Ahrefs API Key 未配置")
            return []

        base_url = "https://open.api.ahrefs.com/v3/backlinks"
        headers = {
            'Authorization': f'Bearer {self.ahrefs_api_key}',
            'Content-Type': 'application/json'
        }

        params = {
            'target': domain,
            'mode': 'exact',
            'limit': limit
        }

        data = self._make_request(base_url, params=params, headers=headers, method='POST')

        if not data:
            return []

        backlinks = []
        for item in data.get('items', []):
            backlinks.append({
                'source_url': item.get('referrer_page', ''),
                'target_url': item.get('target', ''),
                'anchor_text': item.get('anchor_text', ''),
                'domain_rating': item.get('referring_page_domain_rating', 0),
                'url_rating': item.get('referring_page_url_rating', 0),
                'first_seen': item.get('first_seen', ''),
                'last_seen': item.get('last_seen', ''),
                'link_type': item.get('link_type', 'unknown'),
                'is_follow': item.get('is_follow', True),
                'source': 'Ahrefs'
            })

        return backlinks

    def majestic_backlinks(self, domain, limit=100):
        """
        使用 Majestic API 获取外链数据

        Args:
            domain: 域名
            limit: 返回结果数量限制

        Returns:
            外链数据列表
        """
        if not self.majestic_api_key:
            print("⚠️ Majestic API Key 未配置")
            return []

        base_url = "https://api.majestic.com/api_json"
        params = {
            'app_api_key': self.majestic_api_key,
            'cmd': 'GetIndexItemInfo',
            'items': domain,
            'datasource': 'fresh'
        }

        data = self._make_request(base_url, params=params)

        if not data:
            return []

        backlinks = []
        for item in data.get('FullResult', {}).get('DataTables', {}).get('Results', {}).get('Data', []):
            backlinks.append({
                'domain': item.get('Item', ''),
                'trust_flow': item.get('TrustFlow', 0),
                'citation_flow': item.get('CitationFlow', 0),
                'ref_domains': item.get('RefDomains', 0),
                'ref_subnets': item.get('RefSubNets', 0),
                'ref_ips': item.get('RefIPs', 0),
                'source': 'Majestic'
            })

        return backlinks

    def semrush_backlinks(self, domain, limit=100):
        """
        使用 SEMrush API 获取外链数据

        Args:
            domain: 域名
            limit: 返回结果数量限制

        Returns:
            外链数据列表
        """
        if not self.semrush_api_key:
            print("⚠️ SEMrush API Key 未配置")
            return []

        base_url = "https://api.semrush.com/"
        params = {
            'type': 'domain_backlinks',
            'key': self.semrush_api_key,
            'domain': domain,
            'display_limit': limit,
            'export_columns': 'Dt,Dn,Rt,Ru,At,Au,Fs,Lt'
        }

        data = self._make_request(base_url, params=params)

        if not data:
            return []

        backlinks = []
        for row in data.get('data', []):
            if len(row) >= 8:
                backlinks.append({
                    'source_domain': row[0],
                    'source_url': row[1],
                    'target_url': row[2],
                    'anchor_text': row[3],
                    'authority_score': int(row[4]) if row[4] else 0,
                    'first_seen': row[6],
                    'last_seen': row[7],
                    'source': 'SEMrush'
                })

        return backlinks

    def analyze_backlink_quality(self, backlinks):
        """
        分析外链质量

        Args:
            backlinks: 外链数据列表

        Returns:
            质量分析报告
        """
        if not backlinks:
            return {
                'total_backlinks': 0,
                'quality_score': 0,
                'risk_level': '未知',
                'issues': []
            }

        total = len(backlinks)
        high_quality = 0
        medium_quality = 0
        low_quality = 0
        issues = []

        for link in backlinks:
            dr = link.get('domain_rating', link.get('authority_score', 0))

            if dr >= 50:
                high_quality += 1
            elif dr >= 20:
                medium_quality += 1
            else:
                low_quality += 1

            if not link.get('is_follow', True):
                issues.append(f"NoFollow 链接: {link.get('source_url', '')}")

        quality_score = (high_quality * 100 + medium_quality * 60 + low_quality * 20) / total if total > 0 else 0

        if quality_score >= 70:
            risk_level = '低风险'
        elif quality_score >= 40:
            risk_level = '中等风险'
        else:
            risk_level = '高风险'

        return {
            'total_backlinks': total,
            'high_quality': high_quality,
            'medium_quality': medium_quality,
            'low_quality': low_quality,
            'quality_score': round(quality_score, 2),
            'risk_level': risk_level,
            'issues': issues[:10],
            'recommendations': self._get_backlink_recommendations(quality_score, total)
        }

    def _get_backlink_recommendations(self, quality_score, total):
        """根据外链质量给出建议"""
        recommendations = []

        if quality_score < 40:
            recommendations.append("外链质量较低，建议获取更多高质量域名的外链")

        if total < 50:
            recommendations.append("外链数量不足，建议增加外链建设力度")

        if quality_score >= 70 and total >= 100:
            recommendations.append("外链状况良好，继续保持当前策略")

        return recommendations

    def detect_toxic_backlinks(self, backlinks):
        """
        检测有毒外链（垃圾外链）

        Args:
            backlinks: 外链数据列表

        Returns:
            有毒外链列表
        """
        toxic_indicators = [
            'spam', 'casino', 'porn', 'pharma', 'viagra', 'cialis',
            'betting', 'gambling', 'adult', 'xxx'
        ]

        toxic_links = []

        for link in backlinks:
            source_url = link.get('source_url', '').lower()
            anchor_text = link.get('anchor_text', '').lower()

            is_toxic = False
            reason = []

            for indicator in toxic_indicators:
                if indicator in source_url or indicator in anchor_text:
                    is_toxic = True
                    reason.append(f"包含敏感词: {indicator}")

            dr = link.get('domain_rating', link.get('authority_score', 0))
            if dr < 5:
                is_toxic = True
                reason.append("域名权威度过低")

            if is_toxic:
                toxic_links.append({
                    'url': link.get('source_url', ''),
                    'anchor': link.get('anchor_text', ''),
                    'reason': ', '.join(reason),
                    'action': '建议提交到 Google Disavow Tool'
                })

        return toxic_links


gsc_tool = GoogleSearchConsoleTool()
keyword_tool = KeywordResearchTool()
backlink_tool = BacklinkMonitorTool()

