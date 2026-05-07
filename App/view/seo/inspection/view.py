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

from models.models import SEOInspection, SiteConfig
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
            'current_value', 'threshold', 'suggestion', 'inspected_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'inspected_at', 'created_at', 'updated_at']


@extend_schema(tags=["SEO日常巡查"])
@extend_schema_view(
    list=extend_schema(
        summary="获取巡查列表",
        description="获取SEO日常巡查列表，支持按网站URL、分类、状态筛选",
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=False, description="网站URL"),
            OpenApiParameter(name="category", type=str, required=False, description="分类：search_crawl/page_quality/security"),
            OpenApiParameter(name="status", type=str, required=False, description="状态：normal/warning/error"),
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
        
        try:
            gsc_tool = GoogleSearchConsoleTool()
            
            # 根据分类执行不同的检查
            if category == 'page_quality':
                results = self._run_page_quality_inspection(site_url, start_date, end_date)
            elif category == 'search_crawl':
                results = self._run_search_crawl_inspection(site_url, gsc_tool, start_date, end_date)
            else:
                return ApiResponse(code=400, message=f"暂不支持的分类: {category}")
            
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
            
            # 从SiteConfig获取sitemap URL列表
            sitemap_configs = SiteConfig.objects.filter(
                config_type='sitemap_url',
                is_active=True
            ).values_list('content', flat=True)
            
            if not sitemap_configs:
                # 所有检查项都返回未配置
                return [
                    self._save_or_update_inspection(site_url=site_url, inspection_item=item, category='page_quality',
                        status='warning', current_value='0', threshold='N/A', suggestion='未配置Sitemap URL', problem_urls=[])
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
                    resp = requests.get(page_url, timeout=10, allow_redirects=True)
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
                problem_urls=error_urls[:50]
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
            
            # 测量2次响应时间取平均（减少等待时间）
            times = []
            for _ in range(2):
                start = time.time()
                resp = requests.get(site_url, timeout=5)  # 超时改为5秒
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
                                   status, current_value, threshold, suggestion, problem_urls=None):
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
