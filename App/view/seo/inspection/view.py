#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：view.py
@Author  ：Liang
@Date    ：2026/5/7
@description : SEO日常巡查视图
"""
from datetime import datetime, timedelta

import requests
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.decorators import action

from models.models import SEOInspection, SiteConfig, InspectionLog
from seo.seo_tools import GoogleSearchConsoleTool
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination

class SEOInspectionSerializer(serializers.ModelSerializer):
    """SEO日常巡查序列化器"""
    inspection_item_display = serializers.CharField(source='get_inspection_item_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SEOInspection
        fields = [
            'id', 'site_url', 'inspection_item', 'inspection_item_display',
            'category', 'category_display', 'status', 'status_display',
            'current_value', 'threshold', 'suggestion', 'problem_urls',
            'start_date', 'end_date',
            'inspected_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'inspected_at', 'created_at', 'updated_at']


class InspectionLogSerializer(serializers.ModelSerializer):
    """SEO巡查日志序列化器"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InspectionLog
        fields = [
            'id', 'site_url', 'category', 'category_display',
            'start_date', 'end_date',
            'inspected_at', 'duration',
            'status', 'status_display',
            'inspection_count', 'error_count', 'warning_count', 'normal_count',
            'result_summary', 'error_message', 'operator'
        ]
        read_only_fields = ['id', 'inspected_at']


@extend_schema(tags=["SEO日常巡查"])
@extend_schema_view(
    list=extend_schema(
        summary="获取巡查列表",
        description="获取SEO日常巡查列表，支持按网站URL、分类、状态、时间范围筛选",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=False, description="网站URL"),
            OpenApiParameter(name="category", type=str, required=False, description="分类：search_crawl/page_quality/security/performance"),
            OpenApiParameter(name="status", type=str, required=False, description="状态：normal/warning/error"),
            OpenApiParameter(name="start_date", type=str, required=False, description="开始日期（YYYY-MM-DD）"),
            OpenApiParameter(name="end_date", type=str, required=False, description="结束日期（YYYY-MM-DD）"),
        ],
    ),
    retrieve=extend_schema(
        summary="获取巡查详情",
        description="根据ID获取巡查详细信息",
    ),
    destroy=extend_schema(
        summary="删除巡查记录",
        description="删除指定的巡查记录",
    ),
    inspection_logs=extend_schema(
        summary="获取巡查日志列表",
        description="获取SEO巡查执行日志列表，支持按网站URL、分类、状态、时间范围筛选，支持分页",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=False, description="网站URL"),
            OpenApiParameter(name="category", type=str, required=False, description="分类：search_crawl/page_quality/security/performance"),
            OpenApiParameter(name="status", type=str, required=False, description="状态：success/failed/partial"),
            OpenApiParameter(name="start_date", type=str, required=False, description="开始日期（YYYY-MM-DD）"),
            OpenApiParameter(name="end_date", type=str, required=False, description="结束日期（YYYY-MM-DD）"),
            OpenApiParameter(name="page", type=int, required=False, description="页码，默认1"),
            OpenApiParameter(name="page_size", type=int, required=False, description="每页数量，默认20"),
        ],
    ),
)
class SEOInspectionViewSet(BaseViewSet):
    """
    SEO日常巡查 ViewSet
    提供巡查记录的查询、删除和执行巡查功能
    """
    queryset = SEOInspection.objects.all()
    serializer_class = SEOInspectionSerializer
    pagination_class = CustomPagination
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        """获取巡查列表，支持筛选"""
        queryset = SEOInspection.objects.all()
        
        # 按网站URL筛选
        site_url = request.query_params.get('site_url')
        if site_url:
            queryset = queryset.filter(site_url=site_url)
        
        # 按分类筛选
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # 按状态筛选
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # 按时间范围筛选
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        
        queryset = queryset.order_by('-inspected_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="巡查列表获取成功")
    
    @action(detail=False, methods=['post'], name='执行巡查')
    def run_inspection(self, request):
        """
        执行SEO巡查
        请求体: {
            "site_url": "https://example.com",
            "category": "search_crawl",  // 可选，分类：search_crawl/page_quality/security/performance
            "start_timestamp": 1712361600,  // 可选，开始时间戳（秒）
            "end_timestamp": 1714953600     // 可选，结束时间戳（秒）
        }
        """
        from django.utils import timezone
        import time
        
        site_url = request.data.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供网站URL")
        
        # 验证URL格式
        if site_url == 'string' or not site_url.startswith(('http://', 'https://')):
            return ApiResponse(code=400, message="请提供有效的网站URL（以http://或https://开头）")
        
        # 确保URL格式正确（末尾加/）
        if not site_url.endswith('/'):
            site_url += '/'
        
        # 获取分类参数
        category = request.data.get('category', 'search_crawl')
        
        # 处理时间戳参数
        start_timestamp = request.data.get('start_timestamp')
        end_timestamp = request.data.get('end_timestamp')
        
        if start_timestamp and end_timestamp:
            try:
                start_timestamp = int(start_timestamp)
                end_timestamp = int(end_timestamp)
                start_date = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d')
                end_date = datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d')
            except (ValueError, TypeError, OSError) as e:
                return ApiResponse(code=400, message=f"时间戳格式错误: {str(e)}")
        else:
            # 默认使用最近30天
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 创建巡查日志记录
        log = InspectionLog.objects.create(
            site_url=site_url,
            category=category,
            start_date=start_date,
            end_date=end_date,
            status='success',
            operator=request.user.username if hasattr(request, 'user') and request.user.role else 'system'
        )
        
        start_time = time.time()
        
        try:
            gsc_tool = GoogleSearchConsoleTool()
            
            # 根据分类执行不同的检查
            if category == 'page_quality':
                results = self._run_page_quality_inspection(site_url, start_date, end_date)
            elif category == 'security':
                results = self._run_security_inspection(site_url, start_date, end_date)
            elif category == 'performance':
                results = self._run_performance_inspection(site_url, start_date, end_date)
            elif category == 'search_crawl':
                results = self._run_search_crawl_inspection(site_url, gsc_tool, start_date, end_date)
            else:
                log.status = 'failed'
                log.error_message = f"暂不支持的分类: {category}"
                log.save()
                return ApiResponse(code=400, message=f"暂不支持的分类: {category}")
            
            # 计算统计信息
            end_time_val = time.time()
            duration = int(end_time_val - start_time)
            
            error_count = sum(1 for r in results if r.get('status') == 'error')
            warning_count = sum(1 for r in results if r.get('status') == 'warning')
            normal_count = sum(1 for r in results if r.get('status') == 'normal')
            
            # 更新日志
            log.duration = duration
            log.inspection_count = len(results)
            log.error_count = error_count
            log.warning_count = warning_count
            log.normal_count = normal_count
            
            if error_count > 0:
                log.status = 'partial' if normal_count > 0 else 'failed'
            
            # 生成结果摘要
            summary_parts = []
            if error_count > 0:
                summary_parts.append(f"{error_count}个错误")
            if warning_count > 0:
                summary_parts.append(f"{warning_count}个警告")
            if normal_count > 0:
                summary_parts.append(f"{normal_count}个正常")
            
            log.result_summary = f"共检查{len(results)}项，" + "，".join(summary_parts) if summary_parts else "全部正常"
            log.save()
            
            return ApiResponse(
                data={
                    'site_url': site_url,
                    'category': category,
                    'start_date': start_date,
                    'end_date': end_date,
                    'inspection_count': len(results),
                    'results': results
                },
                message="巡查执行完成"
            )
        except Exception as e:
            # 记录错误
            end_time_val = time.time()
            duration = int(end_time_val - start_time)
            
            log.duration = duration
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            
            return ApiResponse(code=500, message=f"巡查执行失败: {str(e)}")
    
    def _run_search_crawl_inspection(self, site_url, gsc_tool, start_date=None, end_date=None):
        """执行搜索与抓取类检查"""
        # 如果未提供日期，使用默认值
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        results = []
        
        # 1. Indexed Pages - 通过Sitemap URL间接判断
        indexed_result = self._check_indexed_pages(site_url, gsc_tool, start_date, end_date)
        results.append(indexed_result)
        
        # 2. Discovered Pages - 通过GSC索引覆盖率估算
        discovered_result = self._check_discovered_pages(site_url, gsc_tool, start_date, end_date)
        results.append(discovered_result)
        
        # 3. Googlebot Crawls/Day - 通过GSC API获取
        crawls_result = self._check_googlebot_crawls(site_url, gsc_tool, start_date, end_date)
        results.append(crawls_result)
        
        # 4. Avg Response Time - Mock数据（需要其他工具）
        response_time_result = self._check_avg_response_time(site_url)
        results.append(response_time_result)
        
        # 5. Sitemap Status - 通过GSC API获取
        sitemap_result = self._check_sitemap_status(site_url, gsc_tool)
        results.append(sitemap_result)
        
        # 6. Google Penalties - Mock数据（无法直接API获取）
        penalties_result = self._check_google_penalties(site_url, start_date, end_date)
        results.append(penalties_result)
        
        return results
    
    def _run_page_quality_inspection(self, site_url, start_date=None, end_date=None):
        """执行页面质量类检查 - 优化版：一次性获取页面内容"""
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urlparse
            import os
                
            # 配置代理
            use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
            proxies = None
            if use_proxy:
                proxies = {
                    'http': os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890'),
                    'https': os.getenv('HTTPS_PROXY', 'http://127.0.0.1:7890')
                }
                print(f"🌐 页面质量检测使用代理: {proxies['http']}")
            else:
                print(f"🌐 页面质量检测不使用代理")
                
            # 从 SiteConfig 获取 sitemap URL 列表
            sitemap_configs = SiteConfig.objects.filter(
                config_type='sitemap_url',
                is_active=True
            ).values_list('content', flat=True)
                
            if not sitemap_configs:
                # 所有检查项都返回未配置
                return [
                    self._save_or_update_inspection(site_url=site_url, inspection_item=item, category='page_quality',
                        status='warning', current_value='0', threshold='N/A', suggestion='未配置Sitemap URL', problem_urls=[],
                        start_date=start_date, end_date=end_date)
                    for item in ['http_status_code', 'tdk_check', 'nofollow_external_links', 'h_tag_structure']
                ]
            
            # 一次性遍历所有URL，获取页面内容并在内存中分析
            site_domain = urlparse(site_url).netloc
            
            # 存储所有检测结果
            error_urls = []  # HTTP错误
            tdk_issues = []  # TDK问题
            external_link_issues = []  # 外链问题
            h_tag_issues = []  # H标签问题
            
            total_checked = 0
            error_404_count = 0
            error_500_count = 0
            missing_title = 0
            missing_desc = 0
            total_external = 0
            missing_nofollow = 0
            multiple_h1 = 0
            skipped_levels = 0
            
            for page_url in sitemap_configs:
                try:
                    # 每个URL只请求一次
                    resp = requests.get(page_url, timeout=10, allow_redirects=True, proxies=proxies)
                    total_checked += 1
                    
                    # 1. HTTP状态码检测
                    if resp.status_code == 404:
                        error_404_count += 1
                        error_urls.append({'url': page_url, 'status': 404, 'type': '404 Not Found'})
                    elif resp.status_code >= 500:
                        error_500_count += 1
                        error_urls.append({'url': page_url, 'status': resp.status_code, 'type': f'{resp.status_code} Server Error'})
                    
                    # 如果状态码正常，继续分析页面内容
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        
                        # 2. TDK检测
                        title = soup.find('title')
                        if not title or not title.string or len(title.string.strip()) == 0:
                            missing_title += 1
                            tdk_issues.append({'url': page_url, 'issue': 'Missing Title'})
                        
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if not meta_desc or not meta_desc.get('content') or len(meta_desc.get('content', '').strip()) == 0:
                            missing_desc += 1
                            tdk_issues.append({'url': page_url, 'issue': 'Missing Description'})
                        
                        # 3. Nofollow外链检测
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            if href.startswith(('http://', 'https://')):
                                link_domain = urlparse(href).netloc
                                if link_domain and link_domain != site_domain:
                                    total_external += 1
                                    rel_attr = link.get('rel', [])
                                    if isinstance(rel_attr, list):
                                        rel_str = ' '.join(rel_attr)
                                    else:
                                        rel_str = str(rel_attr)
                                    
                                    if 'nofollow' not in rel_str.lower():
                                        missing_nofollow += 1
                                        external_link_issues.append({
                                            'url': page_url,
                                            'external_link': href,
                                            'issue': 'External link without nofollow'
                                        })
                        
                        # 4. H标签结构检测
                        h_tags = []
                        for i in range(1, 7):
                            tags = soup.find_all(f'h{i}')
                            for tag in tags:
                                h_tags.append((i, tag.get_text().strip()))
                        
                        h1_count = sum(1 for level, _ in h_tags if level == 1)
                        if h1_count > 1:
                            multiple_h1 += 1
                            h_tag_issues.append({
                                'url': page_url,
                                'issue': f'Multiple H1 tags ({h1_count} found)'
                            })
                        
                        if h_tags:
                            prev_level = 0
                            for level, text in h_tags:
                                if level > prev_level + 1 and prev_level > 0:
                                    skipped_levels += 1
                                    h_tag_issues.append({
                                        'url': page_url,
                                        'issue': f'Skipped heading level: H{prev_level} to H{level}'
                                    })
                                    break
                                prev_level = level
                                
                except Exception as e:
                    error_urls.append({'url': page_url, 'status': 0, 'type': f'Connection Error: {str(e)}'})
            
            # 保存4个检查结果
            results = []
            
            # 1. HTTP状态码结果
            total_errors = error_404_count + error_500_count
            if total_errors > 0:
                http_status = 'error'
                http_suggestion = f'发现{total_errors}个错误页面（404: {error_404_count}, 500+: {error_500_count}）。建议修复或删除这些页面'
            else:
                http_status = 'normal'
                http_suggestion = f'检查了{total_checked}个页面，未发现404或500错误'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='http_status_code',
                category='page_quality',
                status=http_status,
                current_value=f'{total_errors} errors / {total_checked} pages',
                threshold='No errors',
                suggestion=http_suggestion,
                problem_urls=error_urls[:50],
                start_date=start_date,
                end_date=end_date
            ))
            
            # 2. TDK结果
            total_tdk_issues = missing_title + missing_desc
            if total_tdk_issues > 0:
                tdk_status = 'error'
                tdk_suggestion = f'发现{total_tdk_issues}个TDK问题（缺失Title: {missing_title}, 缺失Description: {missing_desc}）。建议补充完整的TDK信息'
            else:
                tdk_status = 'normal'
                tdk_suggestion = f'检查了{total_checked}个页面，TDK完整'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='tdk_check',
                category='page_quality',
                status=tdk_status,
                current_value=f'{total_tdk_issues} issues / {total_checked} pages',
                threshold='Complete TDK',
                suggestion=tdk_suggestion,
                problem_urls=tdk_issues[:50]
            ))
            
            # 3. Nofollow外链结果
            if missing_nofollow > 0:
                nofollow_status = 'warning'
                nofollow_suggestion = f'发现{missing_nofollow}个外链未添加nofollow属性（共{total_external}个外链）。建议为所有外链添加rel="nofollow"'
            else:
                nofollow_status = 'normal'
                nofollow_suggestion = f'检查了{total_checked}个页面的{total_external}个外链，均已添加nofollow属性'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='nofollow_external_links',
                category='page_quality',
                status=nofollow_status,
                current_value=f'{missing_nofollow} issues / {total_external} external links',
                threshold='All external links have nofollow',
                suggestion=nofollow_suggestion,
                problem_urls=external_link_issues[:50]
            ))
            
            # 4. H标签结构结果
            total_h_issues = multiple_h1 + skipped_levels
            if total_h_issues > 0:
                h_status = 'warning'
                h_suggestion = f'发现{total_h_issues}个H标签结构问题（多个H1: {multiple_h1}, 层级跳跃: {skipped_levels}）。建议保持H标签层级结构合理'
            else:
                h_status = 'normal'
                h_suggestion = f'检查了{total_checked}个页面，H标签结构合理'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='h_tag_structure',
                category='page_quality',
                status=h_status,
                current_value=f'{total_h_issues} issues / {total_checked} pages',
                threshold='Proper H tag hierarchy',
                suggestion=h_suggestion,
                problem_urls=h_tag_issues[:50]
            ))
            
            return results
            
        except ImportError:
            return [
                self._save_or_update_inspection(site_url=site_url, inspection_item=item, category='page_quality',
                    status='error', current_value=None, threshold='N/A', 
                    suggestion='缺少beautifulsoup4库，请安装: pip install beautifulsoup4', problem_urls=[])
                for item in ['http_status_code', 'tdk_check', 'nofollow_external_links', 'h_tag_structure']
            ]
        except Exception as e:
            return [
                self._save_or_update_inspection(site_url=site_url, inspection_item=item, category='page_quality',
                    status='error', current_value=None, threshold='N/A', 
                    suggestion=f'检查失败: {str(e)}', problem_urls=[])
                for item in ['http_status_code', 'tdk_check', 'nofollow_external_links', 'h_tag_structure']
            ]
    
    def _run_security_inspection(self, site_url, start_date=None, end_date=None):
        """执行安全巡查类检查 - 优化版：一次性获取页面内容"""
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urlparse
            import hashlib
            import re
            import os
            
            # 配置代理
            use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
            proxies = None
            if use_proxy:
                proxies = {
                    'http': os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890'),
                    'https': os.getenv('HTTPS_PROXY', 'http://127.0.0.1:7890')
                }
                print(f"🌐 安全巡查使用代理: {proxies['http']}")
            else:
                print(f"🌐 安全巡查不使用代理")
            
            # 从SiteConfig获取sitemap URL列表
            sitemap_configs = SiteConfig.objects.filter(
                config_type='sitemap_url',
                is_active=True
            ).values_list('content', flat=True)
            
            if not sitemap_configs:
                return [
                    self._save_or_update_inspection(site_url=site_url, inspection_item=item, category='security',
                        status='warning', current_value='0', threshold='N/A', suggestion='未配置Sitemap URL', problem_urls=[])
                    for item in ['dangerous_domain_refs', 'low_quality_internal_links', 'page_tampering', 'malicious_code']
                ]
            
            # 危险域名黑名单（示例）
            dangerous_domains = [
                'malware-site.com', 'phishing-example.net', 'suspicious-domain.org',
                'bad-redirect.com', 'spam-links.net'
            ]
            
            # 恶意代码特征（简化版）
            malicious_patterns = [
                r'<script[^>]*src=["\'][^"\']*\.js["\'][^>]*>',  # 外部JS
                r'eval\s*\(',  # eval函数
                r'document\.write',  # document.write
                r'iframe[^>]*src=["\'][^"\']*://[^"\']*["\']',  # 外部iframe
                r'base64_decode',  # base64解码
            ]
            
            site_domain = urlparse(site_url).netloc
            
            # 存储所有检测结果
            dangerous_refs = []  # 危险域名引用
            low_quality_links = []  # 低质内链
            tampering_issues = []  # 页面篡改
            malicious_codes = []  # 恶意代码
            
            total_checked = 0
            dangerous_count = 0
            low_quality_count = 0
            tampering_count = 0
            malicious_count = 0
            
            # 用于页面篡改检测：存储页面哈希
            page_hashes = {}
            
            for page_url in sitemap_configs:
                try:
                    # 每个URL只请求一次
                    resp = requests.get(page_url, timeout=10, allow_redirects=True, proxies=proxies)
                    total_checked += 1
                    
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        page_content = resp.text
                        
                        # 计算页面哈希（用于篡改检测）
                        page_hash = hashlib.md5(page_content.encode('utf-8')).hexdigest()
                        page_hashes[page_url] = page_hash
                        
                        # 1. 危险域名引用检测
                        links = soup.find_all('a', href=True)
                        for link in links:
                            href = link['href']
                            if href.startswith(('http://', 'https://')):
                                link_domain = urlparse(href).netloc
                                # 检查是否在危险域名列表中
                                for dangerous in dangerous_domains:
                                    if dangerous in link_domain:
                                        dangerous_count += 1
                                        dangerous_refs.append({
                                            'url': page_url,
                                            'dangerous_link': href,
                                            'domain': link_domain,
                                            'issue': f'Dangerous domain reference: {dangerous}'
                                        })
                                        break
                        
                        # 检查iframe和script标签
                        iframes = soup.find_all('iframe', src=True)
                        for iframe in iframes:
                            src = iframe['src']
                            if src.startswith(('http://', 'https://')):
                                iframe_domain = urlparse(src).netloc
                                for dangerous in dangerous_domains:
                                    if dangerous in iframe_domain:
                                        dangerous_count += 1
                                        dangerous_refs.append({
                                            'url': page_url,
                                            'dangerous_link': src,
                                            'domain': iframe_domain,
                                            'issue': f'Dangerous iframe source: {dangerous}'
                                        })
                                        break
                        
                        # 2. 低质内链检测
                        internal_links = []
                        for link in links:
                            href = link['href']
                            # 判断是否为内链
                            if href.startswith('/') or (href.startswith(site_url) and site_domain in href):
                                # 检查链接文本
                                link_text = link.get_text().strip()
                                
                                # 低质内链特征：空文本、通用文本、过长文本
                                is_low_quality = False
                                reason = ''
                                
                                if not link_text:
                                    is_low_quality = True
                                    reason = 'Empty link text'
                                elif link_text.lower() in ['click here', 'read more', 'learn more', '点击这里', '查看更多']:
                                    is_low_quality = True
                                    reason = f'Generic link text: {link_text}'
                                elif len(link_text) > 100:
                                    is_low_quality = True
                                    reason = f'Too long link text ({len(link_text)} chars)'
                                
                                if is_low_quality:
                                    low_quality_count += 1
                                    low_quality_links.append({
                                        'url': page_url,
                                        'link_href': href,
                                        'link_text': link_text[:50],
                                        'issue': reason
                                    })
                        
                        # 3. 恶意代码检测
                        for pattern in malicious_patterns:
                            matches = re.findall(pattern, page_content, re.IGNORECASE)
                            if matches:
                                malicious_count += 1
                                malicious_codes.append({
                                    'url': page_url,
                                    'pattern': pattern,
                                    'matches_count': len(matches),
                                    'issue': f'Suspicious code pattern detected'
                                })
                                break  # 每个页面只报告一次
                        
                        # 检查是否有可疑的JavaScript
                        scripts = soup.find_all('script')
                        for script in scripts:
                            if script.string:
                                script_content = script.string
                                # 检查是否有混淆代码
                                if len(script_content) > 1000 and script_content.count(';') > 50:
                                    malicious_count += 1
                                    malicious_codes.append({
                                        'url': page_url,
                                        'pattern': 'obfuscated_js',
                                        'matches_count': 1,
                                        'issue': 'Potentially obfuscated JavaScript detected'
                                    })
                                    break
                
                except Exception as e:
                    pass
            
            # 4. 页面篡改检测（与历史哈希对比）
            # 这里简化处理：检查是否有常见的篡改迹象
            for page_url, current_hash in page_hashes.items():
                # 在实际应用中，应该从数据库读取历史哈希进行对比
                # 这里只做基础检查：页面是否包含可疑内容
                try:
                    resp = requests.get(page_url, timeout=10, proxies=proxies)
                    if resp.status_code == 200:
                        content = resp.text.lower()
                        # 检查是否有明显的篡改迹象
                        tampering_indicators = [
                            'hacked by', 'defaced by', 'this site has been hacked',
                            ' compromised', 'malware detected'
                        ]
                        for indicator in tampering_indicators:
                            if indicator in content:
                                tampering_count += 1
                                tampering_issues.append({
                                    'url': page_url,
                                    'indicator': indicator,
                                    'issue': 'Potential page tampering detected'
                                })
                                break
                except:
                    pass
            
            # 保存4个检查结果
            results = []
            
            # 1. 危险域名引用结果
            if dangerous_count > 0:
                dangerous_status = 'error'
                dangerous_suggestion = f'发现{dangerous_count}个危险域名引用。建议立即移除或替换这些链接'
            else:
                dangerous_status = 'normal'
                dangerous_suggestion = f'检查了{total_checked}个页面，未发现危险域名引用'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='dangerous_domain_refs',
                category='security',
                status=dangerous_status,
                current_value=f'{dangerous_count} dangerous refs / {total_checked} pages',
                threshold='No dangerous domains',
                suggestion=dangerous_suggestion,
                problem_urls=dangerous_refs[:50]
            ))
            
            # 2. 低质内链结果
            if low_quality_count > 0:
                low_quality_status = 'warning'
                low_quality_suggestion = f'发现{low_quality_count}个低质内链。建议优化链接文本，使其更具描述性'
            else:
                low_quality_status = 'normal'
                low_quality_suggestion = f'检查了{total_checked}个页面，内链质量良好'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='low_quality_internal_links',
                category='security',
                status=low_quality_status,
                current_value=f'{low_quality_count} low quality links / {total_checked} pages',
                threshold='No low quality links',
                suggestion=low_quality_suggestion,
                problem_urls=low_quality_links[:50]
            ))
            
            # 3. 页面篡改检测结果
            if tampering_count > 0:
                tampering_status = 'error'
                tampering_suggestion = f'⚠️ 发现{tampering_count}个页面可能被篡改！请立即检查并恢复备份'
            else:
                tampering_status = 'normal'
                tampering_suggestion = f'检查了{total_checked}个页面，未发现篡改迹象'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='page_tampering',
                category='security',
                status=tampering_status,
                current_value=f'{tampering_count} tampered pages / {total_checked} pages',
                threshold='No tampering',
                suggestion=tampering_suggestion,
                problem_urls=tampering_issues[:50]
            ))
            
            # 4. 恶意代码检测结果
            if malicious_count > 0:
                malicious_status = 'error'
                malicious_suggestion = f'⚠️ 发现{malicious_count}个页面存在可疑代码！请立即清理并检查服务器安全'
            else:
                malicious_status = 'normal'
                malicious_suggestion = f'检查了{total_checked}个页面，未发现恶意代码'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='malicious_code',
                category='security',
                status=malicious_status,
                current_value=f'{malicious_count} malicious codes / {total_checked} pages',
                threshold='No malicious code',
                suggestion=malicious_suggestion,
                problem_urls=malicious_codes[:50]
            ))
            
            return results
            
        except ImportError:
            return [
                self._save_or_update_inspection(site_url=site_url, inspection_item=item, category='security',
                    status='error', current_value=None, threshold='N/A', 
                    suggestion='缺少beautifulsoup4库，请安装: pip install beautifulsoup4', problem_urls=[])
                for item in ['dangerous_domain_refs', 'low_quality_internal_links', 'page_tampering', 'malicious_code']
            ]
        except Exception as e:
            return [
                self._save_or_update_inspection(site_url=site_url, inspection_item=item, category='security',
                    status='error', current_value=None, threshold='N/A', 
                    suggestion=f'检查失败: {str(e)}', problem_urls=[])
                for item in ['dangerous_domain_refs', 'low_quality_internal_links', 'page_tampering', 'malicious_code']
            ]
    
    def _run_performance_inspection(self, site_url, start_date=None, end_date=None):
        """执行性能巡查类检查 - 使用PageSpeed Insights API"""
        try:
            from App.view.seo.page_speed.tools import _scan_with_pagespeed_api
            
            # 首页URL（用户指定）
            home_url = 'https://www.markwallpapers.com/'
            
            results = []
            
            # 调用 PageSpeed Insights API 获取性能数据
            print(f"🔍 调用 PageSpeed Insights API: {home_url}")
            ps_data = _scan_with_pagespeed_api(home_url, platform='page')
            
            if not ps_data:
                return [
                    self._save_or_update_inspection(
                        site_url=site_url, inspection_item=item, category='performance',
                        status='error', current_value=None, threshold='N/A',
                        suggestion='PageSpeed API 调用失败，请检查API Key配置', problem_urls=[]
                    )
                    for item in ['first_screen_render_blocking', 'first_screen_image_loading', 
                                'avg_response_time', 'fid_first_input_delay']
                ]
            
            # 1. 首屏渲染阻塞检测 (基于FCP和LCP)
            fcp = ps_data.get('fcp', 0)  # First Contentful Paint (秒)
            lcp = ps_data.get('lcp', 0)  # Largest Contentful Paint (秒)
            
            # 判断是否有渲染阻塞
            render_blocking_issues = []
            if fcp > 2.5:
                render_blocking_issues.append({
                    'url': home_url,
                    'metric': 'FCP',
                    'value': f'{fcp}s',
                    'threshold': '< 2.5s',
                    'issue': 'First Contentful Paint too slow'
                })
            
            if lcp > 4.0:
                render_blocking_issues.append({
                    'url': home_url,
                    'metric': 'LCP',
                    'value': f'{lcp}s',
                    'threshold': '< 4.0s',
                    'issue': 'Largest Contentful Paint too slow'
                })
            
            if render_blocking_issues:
                render_status = 'error'
                render_suggestion = f'发现{len(render_blocking_issues)}个渲染阻塞问题。建议：1)优化CSS/JS加载 2)使用懒加载 3)压缩资源 4)启用CDN'
            else:
                render_status = 'normal'
                render_suggestion = f'首屏渲染良好，FCP={fcp}s, LCP={lcp}s'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='first_screen_render_blocking',
                category='performance',
                status=render_status,
                current_value=f'FCP={fcp}s, LCP={lcp}s',
                threshold='FCP < 2.5s, LCP < 4.0s',
                suggestion=render_suggestion,
                problem_urls=render_blocking_issues[:50]
            ))
            
            # 2. 首屏图片加载检测 (基于LCP和资源分析)
            ttfb = ps_data.get('ttfb', 0)  # Time to First Byte
            load_time = ps_data.get('load_time', 0)  # Speed Index
            page_size = ps_data.get('page_size', 0)  # 页面大小(KB)
            
            image_loading_issues = []
            
            # 如果LCP时间过长，可能是图片加载慢
            if lcp > 2.5:
                image_loading_issues.append({
                    'url': home_url,
                    'metric': 'LCP',
                    'value': f'{lcp}s',
                    'issue': 'LCP可能由大图导致，建议优化首屏图片'
                })
            
            # 如果页面过大，可能包含未优化的图片
            if page_size > 2000:  # 超过2MB
                image_loading_issues.append({
                    'url': home_url,
                    'metric': 'Page Size',
                    'value': f'{page_size:.0f}KB',
                    'issue': '页面过大，可能存在未优化的图片'
                })
            
            if image_loading_issues:
                image_status = 'warning'
                image_suggestion = f'发现{len(image_loading_issues)}个图片加载问题。建议：1)使用WebP格式 2)压缩图片 3)懒加载非首屏图片 4)使用响应式图片'
            else:
                image_status = 'normal'
                image_suggestion = f'首屏图片加载良好，页面大小={page_size:.0f}KB'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='first_screen_image_loading',
                category='performance',
                status=image_status,
                current_value=f'LCP={lcp}s, Size={page_size:.0f}KB',
                threshold='LCP < 2.5s, Size < 2000KB',
                suggestion=image_suggestion,
                problem_urls=image_loading_issues[:50]
            ))
            
            # 3. 平均响应时间 (TTFB)
            if ttfb > 0.8:  # 超过800ms
                response_status = 'error'
                response_suggestion = f'服务器响应时间{ttfb:.2f}s过慢！建议：1)优化数据库查询 2)启用缓存 3)使用CDN 4)升级服务器'
            elif ttfb > 0.4:  # 超过400ms
                response_status = 'warning'
                response_suggestion = f'服务器响应时间{ttfb:.2f}s较慢。建议：1)启用服务器端缓存 2)优化后端代码'
            else:
                response_status = 'normal'
                response_suggestion = f'服务器响应时间{ttfb:.2f}s，良好'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='avg_response_time',
                category='performance',
                status=response_status,
                current_value=f'{ttfb:.2f}s',
                threshold='< 0.4s',
                suggestion=response_suggestion,
                problem_urls=[{'url': home_url, 'metric': 'TTFB', 'value': f'{ttfb:.2f}s'}] if ttfb > 0.4 else []
            ))
            
            # 4. FID首次输入延迟
            fid = ps_data.get('fid', 0)  # 毫秒
            inp = ps_data.get('inp', 0)  # Interaction to Next Paint (毫秒)
            
            # FID > 100ms 为需要改进，> 300ms 为差
            if fid > 300:
                fid_status = 'error'
                fid_suggestion = f'FID={fid:.0f}ms过慢！建议：1)减少JavaScript执行时间 2)拆分长任务 3)使用Web Workers'
            elif fid > 100:
                fid_status = 'warning'
                fid_suggestion = f'FID={fid:.0f}ms较慢。建议：1)优化JavaScript代码 2)延迟加载非关键脚本'
            else:
                fid_status = 'normal'
                fid_suggestion = f'FID={fid:.0f}ms，交互响应良好'
            
            results.append(self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='fid_first_input_delay',
                category='performance',
                status=fid_status,
                current_value=f'{fid:.0f}ms',
                threshold='< 100ms',
                suggestion=fid_suggestion,
                problem_urls=[{'url': home_url, 'metric': 'FID', 'value': f'{fid:.0f}ms'}] if fid > 100 else []
            ))
            
            return results
            
        except Exception as e:
            print(f"❌ 性能巡查失败: {e}")
            import traceback
            traceback.print_exc()
            return [
                self._save_or_update_inspection(
                    site_url=site_url, inspection_item=item, category='performance',
                    status='error', current_value=None, threshold='N/A',
                    suggestion=f'检查失败: {str(e)}', problem_urls=[]
                )
                for item in ['first_screen_render_blocking', 'first_screen_image_loading', 
                            'avg_response_time', 'fid_first_input_delay']
            ]
    
    def _check_indexed_pages(self, site_url, gsc_tool, start_date=None, end_date=None):
        """检查已收录页面数量"""
        try:
            # 如果未提供日期，使用默认值
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # 从SiteConfig表获取sitemap URL
            sitemap_configs = SiteConfig.objects.filter(
                config_type='sitemap_url',
                is_active=True
            ).values_list('content', flat=True)
            
            if not sitemap_configs:
                return self._save_or_update_inspection(
                    site_url=site_url,
                    inspection_item='indexed_pages',
                    category='search_crawl',
                    status='warning',
                    current_value='0',
                    threshold=None,
                    suggestion='未配置Sitemap URL，请在网站配置中添加Sitemap地址'
                )
            
            # 尝试通过GSC API获取搜索分析数据来估算收录情况
            rows = gsc_tool.get_search_analytics(site_url, start_date, end_date, dimensions=['page'])
            
            if rows:
                # 有曝光的页面数作为已收录页面的估算
                indexed_count = len(rows)
                status = 'normal' if indexed_count > 0 else 'warning'
                suggestion = f'发现 {indexed_count} 个有搜索数据的页面' if indexed_count > 0 else '未发现任何有搜索数据的页面，请检查网站是否被Google收录'
                
                return self._save_or_update_inspection(
                    site_url=site_url,
                    inspection_item='indexed_pages',
                    category='search_crawl',
                    status=status,
                    current_value=str(indexed_count),
                    threshold='> 0',
                    suggestion=suggestion
                )
            else:
                # 使用Mock数据
                mock_count = 150
                return self._save_or_update_inspection(
                    site_url=site_url,
                    inspection_item='indexed_pages',
                    category='search_crawl',
                    status='warning',
                    current_value=str(mock_count),
                    threshold='> 0',
                    suggestion='使用模拟数据：检测到约150个页面。建议配置GSC API以获取真实数据'
                )
        except Exception as e:
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='indexed_pages',
                category='search_crawl',
                status='error',
                current_value=None,
                threshold=None,
                suggestion=f'检查失败: {str(e)}'
            )
    
    def _check_discovered_pages(self, site_url, gsc_tool, start_date=None, end_date=None):
        """检查已发现但未收录的页面"""
        try:
            # 如果未提供日期，使用默认值
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # GSC API不直接提供此数据，需要从索引覆盖率报告中获取
            # 这里使用估算方法
            
            # 获取总页面数（从sitemap配置，不实际请求sitemap文件）
            sitemap_configs = SiteConfig.objects.filter(
                config_type='sitemap_url',
                is_active=True
            ).values_list('content', flat=True)
            
            # 估算总页面数（基于配置的sitemap数量）
            total_pages = len(sitemap_configs) * 100 if sitemap_configs else 0  # 每个sitemap估算100页
            
            # 获取已收录页面数
            rows = gsc_tool.get_search_analytics(site_url, start_date, end_date, dimensions=['page'])
            indexed_count = len(rows) if rows else 0
            
            discovered_count = max(0, total_pages - indexed_count)
            
            if total_pages == 0:
                status = 'warning'
                suggestion = '未找到Sitemap或无法解析，无法计算发现页面数'
            elif discovered_count > indexed_count * 0.5:
                status = 'warning'
                suggestion = f'发现 {discovered_count} 个未被收录的页面，占总数的{discovered_count/max(total_pages,1)*100:.1f}%。建议优化页面质量并重新提交Sitemap'
            else:
                status = 'normal'
                suggestion = f'发现 {discovered_count} 个未收录页面，比例正常'
            
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='discovered_pages',
                category='search_crawl',
                status=status,
                current_value=str(discovered_count),
                threshold='< 50% of total',
                suggestion=suggestion
            )
        except Exception as e:
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='discovered_pages',
                category='search_crawl',
                status='error',
                current_value=None,
                threshold=None,
                suggestion=f'检查失败: {str(e)}'
            )
    
    def _check_googlebot_crawls(self, site_url, gsc_tool, start_date=None, end_date=None):
        """检查Googlebot每日爬取次数"""
        try:
            # 如果未提供日期，使用默认值
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # GSC API不直接提供爬取次数，需要通过其他方式估算
            # 这里使用过去7天的点击和曝光数据来估算活跃度
            
            rows = gsc_tool.get_search_analytics(site_url, start_date, end_date)
            
            if rows:
                total_impressions = sum(row['impressions'] for row in rows)
                # 粗略估算：曝光量越高，爬取频率可能越高
                avg_daily_crawls = int(total_impressions / 7 / 100)  # 简化估算
                avg_daily_crawls = max(avg_daily_crawls, 10)  # 至少10次
                
                if avg_daily_crawls < 50:
                    status = 'warning'
                    suggestion = f'Googlebot日均爬取约{avg_daily_crawls}次，较低。建议增加高质量内容和外部链接'
                else:
                    status = 'normal'
                    suggestion = f'Googlebot日均爬取约{avg_daily_crawls}次，正常'
                
                return self._save_or_update_inspection(
                    site_url=site_url,
                    inspection_item='googlebot_crawls_per_day',
                    category='search_crawl',
                    status=status,
                    current_value=str(avg_daily_crawls),
                    threshold='> 50',
                    suggestion=suggestion
                )
            else:
                # Mock数据
                mock_crawls = 120
                return self._save_or_update_inspection(
                    site_url=site_url,
                    inspection_item='googlebot_crawls_per_day',
                    category='search_crawl',
                    status='warning',
                    current_value=str(mock_crawls),
                    threshold='> 50',
                    suggestion=f'使用模拟数据：Googlebot日均爬取约{mock_crawls}次。建议配置GSC API获取真实数据'
                )
        except Exception as e:
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='googlebot_crawls_per_day',
                category='search_crawl',
                status='error',
                current_value=None,
                threshold=None,
                suggestion=f'检查失败: {str(e)}'
            )
    
    def _check_avg_response_time(self, site_url):
        """检查平均响应时间"""
        try:
            import requests
            import time
            import os
            
            # 配置代理
            use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
            proxies = None
            if use_proxy:
                proxies = {
                    'http': os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890'),
                    'https': os.getenv('HTTPS_PROXY', 'http://127.0.0.1:7890')
                }
            
            # 测量2次响应时间取平均（减少等待时间）
            times = []
            for _ in range(2):
                start = time.time()
                resp = requests.get(site_url, timeout=5, proxies=proxies)  # 超时改为5秒
                end = time.time()
                times.append((end - start) * 1000)  # 转换为毫秒
            
            avg_time = sum(times) / len(times)
            
            if avg_time > 3000:
                status = 'error'
                suggestion = f'平均响应时间{avg_time:.0f}ms，过慢！建议优化服务器性能、启用CDN、压缩资源'
            elif avg_time > 1500:
                status = 'warning'
                suggestion = f'平均响应时间{avg_time:.0f}ms，较慢。建议优化数据库查询、启用缓存'
            else:
                status = 'normal'
                suggestion = f'平均响应时间{avg_time:.0f}ms，良好'
            
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='avg_response_time',
                category='search_crawl',
                status=status,
                current_value=f'{avg_time:.0f}ms',
                threshold='< 1500ms',
                suggestion=suggestion
            )
        except Exception as e:
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='avg_response_time',
                category='search_crawl',
                status='error',
                current_value=None,
                threshold='< 1500ms',
                suggestion=f'检查失败: {str(e)}'
            )
    
    def _check_sitemap_status(self, site_url, gsc_tool):
        """检查Sitemap状态"""
        try:
            sitemaps = gsc_tool.get_sitemap_status(site_url)
            
            if not sitemaps:
                # 尝试从配置中获取并提交
                sitemap_configs = SiteConfig.objects.filter(
                    config_type='sitemap_url',
                    is_active=True
                ).values_list('content', flat=True)
                
                if sitemap_configs:
                    suggestion = f'GSC中未找到提交的Sitemap。已配置的Sitemap: {", ".join(sitemap_configs[:3])}'
                    return self._save_or_update_inspection(
                        site_url=site_url,
                        inspection_item='sitemap_status',
                        category='search_crawl',
                        status='warning',
                        current_value='Not Submitted',
                        threshold='Submitted',
                        suggestion=suggestion
                    )
                else:
                    return self._save_or_update_inspection(
                        site_url=site_url,
                        inspection_item='sitemap_status',
                        category='search_crawl',
                        status='error',
                        current_value='Not Configured',
                        threshold='Submitted',
                        suggestion='未配置Sitemap URL，请在网站设置中添加'
                    )
            
            # 检查是否有错误
            has_errors = any(sm.get('errors', 0) > 0 for sm in sitemaps)
            has_warnings = any(sm.get('warnings', 0) > 0 for sm in sitemaps)
            
            if has_errors:
                status = 'error'
                total_errors = sum(sm.get('errors', 0) for sm in sitemaps)
                suggestion = f'Sitemap存在{total_errors}个错误，请立即修复'
            elif has_warnings:
                status = 'warning'
                total_warnings = sum(sm.get('warnings', 0) for sm in sitemaps)
                suggestion = f'Sitemap存在{total_warnings}个警告，建议检查'
            else:
                status = 'normal'
                suggestion = f'Sitemap状态正常，共{len(sitemaps)}个Sitemap文件'
            
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='sitemap_status',
                category='search_crawl',
                status=status,
                current_value=f'{len(sitemaps)} sitemaps',
                threshold='No errors',
                suggestion=suggestion
            )
        except Exception as e:
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='sitemap_status',
                category='search_crawl',
                status='error',
                current_value=None,
                threshold='No errors',
                suggestion=f'检查失败: {str(e)}'
            )
    
    def _check_google_penalties(self, site_url, start_date=None, end_date=None):
        """检查Google惩罚"""
        try:
            # 如果未提供日期，使用默认值
            if not start_date:
                start_date_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            else:
                start_date_30 = start_date
                
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Google不提供直接的惩罚检测API
            # 这里通过一些指标间接判断
            
            start_date_60 = (datetime.strptime(start_date_30, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # 比较最近30天和前30天的流量变化
            recent_rows = GoogleSearchConsoleTool().get_search_analytics(
                site_url, start_date_30, end_date
            )
            previous_rows = GoogleSearchConsoleTool().get_search_analytics(
                site_url, start_date_60, start_date_30
            )
            
            recent_clicks = sum(row['clicks'] for row in recent_rows) if recent_rows else 0
            previous_clicks = sum(row['clicks'] for row in previous_rows) if previous_rows else 0
            
            if previous_clicks > 0:
                change_rate = (recent_clicks - previous_clicks) / previous_clicks * 100
                
                if change_rate < -50:
                    status = 'error'
                    suggestion = f'⚠️ 流量大幅下降{abs(change_rate):.1f}%！可能存在Google惩罚。检查：1)手动操作通知 2)算法更新 3)技术问题'
                elif change_rate < -20:
                    status = 'warning'
                    suggestion = f'流量下降{abs(change_rate):.1f}%，建议关注。可能原因：季节性波动、竞争加剧、轻微算法影响'
                else:
                    status = 'normal'
                    suggestion = f'流量变化{change_rate:+.1f}%，在正常范围内'
            else:
                # Mock数据
                status = 'normal'
                suggestion = '使用模拟数据：未检测到Google惩罚迹象。建议在GSC中定期检查"安全和手动操作"报告'
            
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='google_penalties',
                category='search_crawl',
                status=status,
                current_value=f'{change_rate:+.1f}%' if previous_clicks > 0 else 'N/A',
                threshold='No significant drop',
                suggestion=suggestion
            )
        except Exception as e:
            return self._save_or_update_inspection(
                site_url=site_url,
                inspection_item='google_penalties',
                category='search_crawl',
                status='error',
                current_value=None,
                threshold='No significant drop',
                suggestion=f'检查失败: {str(e)}'
            )
    
    def _save_or_update_inspection(self, site_url, inspection_item, category, 
                                   status, current_value, threshold, suggestion, problem_urls=None,
                                   start_date=None, end_date=None):
        """保存或更新巡查结果"""
        try:
            from django.utils import timezone
            inspection, created = SEOInspection.objects.update_or_create(
                site_url=site_url,
                inspection_item=inspection_item,
                category=category,
                defaults={
                    'status': status,
                    'current_value': current_value,
                    'threshold': threshold,
                    'suggestion': suggestion,
                    'problem_urls': problem_urls,
                    'start_date': start_date,
                    'end_date': end_date,
                    'inspected_at': timezone.now()
                }
            )
            
            return {
                'inspection_item': inspection_item,
                'inspection_item_display': inspection.get_inspection_item_display(),
                'status': status,
                'status_display': inspection.get_status_display(),
                'current_value': current_value,
                'threshold': threshold,
                'suggestion': suggestion,
                'start_date': start_date,
                'end_date': end_date,
                'created': created
            }
        except Exception as e:
            return {
                'inspection_item': inspection_item,
                'status': 'error',
                'suggestion': f'保存失败: {str(e)}'
            }
    
    @action(detail=False, methods=['get'], name='获取巡查统计')
    def inspection_stats(self, request):
        """获取巡查统计信息"""
        site_url = request.query_params.get('site_url')
        
        queryset = SEOInspection.objects.all()
        if site_url:
            queryset = queryset.filter(site_url=site_url)
        
        total = queryset.count()
        normal_count = queryset.filter(status='normal').count()
        warning_count = queryset.filter(status='warning').count()
        error_count = queryset.filter(status='error').count()
        
        # 按分类统计
        category_stats = {}
        for category, _ in SEOInspection.CATEGORY_CHOICES:
            cat_queryset = queryset.filter(category=category)
            category_stats[category] = {
                'name': dict(SEOInspection.CATEGORY_CHOICES)[category],
                'total': cat_queryset.count(),
                'normal': cat_queryset.filter(status='normal').count(),
                'warning': cat_queryset.filter(status='warning').count(),
                'error': cat_queryset.filter(status='error').count(),
            }
        
        return ApiResponse(data={
            'total': total,
            'normal': normal_count,
            'warning': warning_count,
            'error': error_count,
            'categories': category_stats
        }, message="统计信息获取成功")

    @extend_schema(
        summary="获取日常巡查看板",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True,
                             description="网站URL，如: https://www.markwallpapers.com/"),
            OpenApiParameter(name="start_timestamp", type=int, required=True,
                             description="开始时间戳（秒），如: 1712361600"),
            OpenApiParameter(name="end_timestamp", type=int, required=True,
                             description="结束时间戳（秒），如: 1714953600"),
        ],
    )
    @action(detail=False, methods=['get'], name='获取日常巡查看板')
    def inspection_dashboard(self, request):
        """
        获取日常巡查看板数据
        返回四个分类（搜索与抓取、页面质量、安全巡查、性能巡查）的统计信息：
        - 正常项数量
        - 警告项数量
        - 异常项数量
        - 最新检查时间
        """
        site_url = request.query_params.get('site_url')
        if not site_url:
            return ApiResponse(code=400, message="请提供网站URL参数")
        
        # 确保URL格式正确
        if not site_url.endswith('/'):
            site_url += '/'
        
        dashboard_data = {
            'site_url': site_url,
            'categories': {}
        }
        
        # 遍历四个分类，获取统计数据
        for category_code, category_name in SEOInspection.CATEGORY_CHOICES:
            queryset = SEOInspection.objects.filter(
                site_url=site_url,
                category=category_code
            )
            
            # 获取该分类的最新检查时间
            latest_inspection = queryset.order_by('-inspected_at').first()
            latest_check_time = latest_inspection.inspected_at.strftime('%Y-%m-%d %H:%M:%S') if latest_inspection else None
            
            # 统计各状态数量
            normal_count = queryset.filter(status='normal').count()
            warning_count = queryset.filter(status='warning').count()
            error_count = queryset.filter(status='error').count()
            
            dashboard_data['categories'][category_code] = {
                'name': category_name,
                'normal': normal_count,
                'warning': warning_count,
                'error': error_count,
                'latest_check_time': latest_check_time
            }
        
        # 计算总计
        all_queryset = SEOInspection.objects.filter(site_url=site_url)
        dashboard_data['summary'] = {
            'total_normal': all_queryset.filter(status='normal').count(),
            'total_warning': all_queryset.filter(status='warning').count(),
            'total_error': all_queryset.filter(status='error').count(),
            'total_items': all_queryset.count()
        }
        
        return ApiResponse(data=dashboard_data, message="巡查看板数据获取成功")
    
    @action(detail=False, methods=['get'], name='获取巡查日志列表')
    def inspection_logs(self, request):
        """获取巡查日志列表，支持筛选"""
        from tool.utils import CustomPagination
        queryset = InspectionLog.objects.all()
        # 按网站URL筛选
        site_url = request.query_params.get('site_url')
        if site_url:
            queryset = queryset.filter(site_url=site_url)
        # 按分类筛选
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        # 按状态筛选
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        # 按时间范围筛选
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        queryset = queryset.order_by('-inspected_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = InspectionLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = InspectionLogSerializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="巡查日志获取成功")
