# -*- coding: UTF-8 -*-
"""
内容优化工具类
调用三方接口分析页面内容，提供优化建议
"""
import requests
import logging
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)


def analyze_page_content(page_path, platform='page'):
    """
    分析页面内容
    :param page_path: 页面路径，如 /markwallpapers/search
    :param platform: 平台类型，page(桌面端)/phone(手机)/pad(平板)
    :return: dict containing page_title, content_score, word_count, issues, suggestions
    """
    result = {
        'page_title': '',
        'content_score': 0,
        'word_count': 0,
        'issues': [],  # 问题检测
        'suggestions': []  # 优化建议
    }
    
    try:
        # 拼接完整URL
        from App.view.seo.page_speed.tools import get_site_prefix
        site_prefix = get_site_prefix()
        if not page_path.startswith('/'):
            page_path_with_slash = '/' + page_path
        else:
            page_path_with_slash = page_path
        full_url = f"{site_prefix}{page_path_with_slash}"
        
        # 调用三方接口分析页面内容
        result = _call_content_analysis_api(full_url, platform)
        
    except Exception as e:
        logger.error(f"页面内容分析失败: {page_path}, 错误: {e}")
        # 如果API调用失败，使用模拟数据
        result = _mock_content_analysis(page_path, platform)
    
    return result


def _call_content_analysis_api(url, platform='page'):
    """
    调用三方内容分析API
    这里可以使用各种SEO分析API，例如：
    - Google Search Console API
    - SEMrush API
    - Ahrefs API
    - 或自定义的内容分析服务
    
    :param url: 完整URL
    :param platform: 平台类型
    :return: 分析结果字典
    """
    try:
        # 获取API配置（需要在settings中配置）
        api_key = getattr(settings, 'CONTENT_ANALYSIS_API_KEY', '')
        api_url = getattr(settings, 'CONTENT_ANALYSIS_API_URL', '')
        
        if not api_key or not api_url:
            logger.warning("未配置内容分析API，使用模拟数据")
            return _mock_content_analysis(url, platform)
        
        # 构造请求参数
        params = {
            'url': url,
            'platform': platform,
            'api_key': api_key
        }
        
        # 发送请求
        response = requests.post(api_url, json=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # 解析返回结果（根据实际API返回格式调整）
            optimization_suggestions = data.get('optimization_suggestions', [])
            
            # 如果是字符串，尝试转换为JSON数组
            if isinstance(optimization_suggestions, str):
                import json
                try:
                    optimization_suggestions = json.loads(optimization_suggestions)
                except:
                    optimization_suggestions = []
            
            # 将建议分为问题和优化建议两类
            issues = []
            suggestions = []
            
            for item in optimization_suggestions:
                # 如果有severity字段，归类为问题；否则归类为建议
                if 'severity' in item:
                    issues.append(item)
                else:
                    suggestions.append(item)
            
            return {
                'page_title': data.get('page_title', ''),
                'content_score': data.get('content_score', 0),
                'word_count': data.get('word_count', 0),
                'issues': issues,
                'suggestions': suggestions
            }
        else:
            logger.error(f"内容分析API请求失败: {response.status_code}")
            return _mock_content_analysis(url, platform)
            
    except Exception as e:
        logger.error(f"内容分析API调用失败: {e}")
        return _mock_content_analysis(url, platform)


def _mock_content_analysis(page_path, platform='page'):
    """
    模拟页面内容分析（用于测试或API不可用时）
    根据页面路径和平台生成稳定的分析结果
    :param page_path: 页面路径
    :param platform: 平台类型
    """
    import hashlib
    
    # 基于页面路径和平台生成稳定的分析结果
    hash_input = f"{page_path}_{platform}_content"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    
    # 页面标题
    page_titles = [
        "优质壁纸下载 - MarkWallpapers",
        "高清壁纸大全 - 免费壁纸下载",
        "4K壁纸精选 - 专业壁纸网站",
        "手机壁纸推荐 - 每日更新",
        "桌面壁纸合集 - 高清无水印"
    ]
    title_index = hash_value % len(page_titles)
    page_title = page_titles[title_index]
    
    # 内容评分 (0-100)
    content_score = 60 + (hash_value % 41)  # 60-100之间
    
    # 字数 (200-2000字)
    word_count = 200 + (hash_value % 1800)
    
    # 问题检测（issues）- 带有severity字段
    issues = []
    
    if content_score < 70:
        issues.append({
            "type": "content_length",
            "title": "内容长度不足",
            "severity": "high",
            "description": "页面内容少于500字，建议增加内容长度以提升SEO排名"
        })
        issues.append({
            "type": "title_optimization",
            "title": "标题需要优化",
            "severity": "medium",
            "description": "页面标题不够吸引人或缺少关键词"
        })
        issues.append({
            "type": "internal_links",
            "title": "内部链接缺失",
            "severity": "medium",
            "description": "缺少相关内部链接，影响页面关联性"
        })
    
    if content_score < 80:
        issues.append({
            "type": "image_alt",
            "title": "图片ALT标签缺失",
            "severity": "low",
            "description": "部分图片缺少ALT标签，影响可访问性"
        })
        issues.append({
            "type": "content_structure",
            "title": "段落结构不佳",
            "severity": "low",
            "description": "内容缺少小标题，可读性较差"
        })
    
    # 优化建议（suggestions）- 带有priority字段
    suggestions = []
    
    if content_score < 90:
        suggestions.append({
            "type": "multimedia",
            "title": "添加多媒体内容",
            "priority": "medium",
            "description": "增加视频、图表等多媒体内容，提升用户体验和页面停留时间"
        })
        suggestions.append({
            "type": "keyword_density",
            "title": "优化关键词密度",
            "priority": "medium",
            "description": "调整关键词密度至2%-5%之间，避免过度优化"
        })
    
    if content_score >= 90:
        suggestions.append({
            "type": "content_quality",
            "title": "保持内容质量",
            "priority": "low",
            "description": "当前内容质量优秀，建议持续产出高质量内容"
        })
        suggestions.append({
            "type": "deep_content",
            "title": "扩展深度内容",
            "priority": "low",
            "description": "可以增加更多深度内容，建立行业权威地位"
        })
    
    # 添加平台特定建议
    if platform in ['phone', 'pad']:
        suggestions.append({
            "type": "mobile_readability",
            "title": "优化移动端阅读体验",
            "priority": "high",
            "description": "确保内容在移动设备上易于阅读，调整字体大小和行间距"
        })
        suggestions.append({
            "type": "touch_interaction",
            "title": "优化触摸交互",
            "priority": "medium",
            "description": "调整触摸交互元素的大小和间距，提升移动端用户体验"
        })
    
    return {
        'page_title': page_title,
        'content_score': content_score,
        'word_count': word_count,
        'issues': issues,  # 问题检测
        'suggestions': suggestions  # 优化建议
    }
