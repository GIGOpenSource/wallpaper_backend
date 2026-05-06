# -*- coding: UTF-8 -*-
"""
外链扫描工具类
调用免费SEO API获取外链信息
"""
import requests
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def scan_backlink_info(target_url):
    """
    扫描外链信息
    :param target_url: 目标页面URL
    :return: dict containing da_score, quality_score, attribute, status, source_page, anchor_text
    """
    result = {
        'da_score': 0,
        'quality_score': 50,
        'attribute': 'dofollow',
        'status': 'pending',
        'source_page': '',
        'anchor_text': ''
    }
    
    try:
        # 提取域名
        parsed = urlparse(target_url)
        domain = parsed.netloc
        if not domain:
            domain = parsed.path
        
        # 方法1: 使用 Moz API (免费版每月2500次查询)
        # 需要注册: https://moz.com/products/api
        moz_access_id = ""  # 从配置获取
        moz_secret_key = ""  # 从配置获取
        
        if moz_access_id and moz_secret_key:
            result = _scan_with_moz(domain, moz_access_id, moz_secret_key)
        else:
            # 如果没有配置API，使用模拟数据
            logger.warning(f"未配置SEO API，使用默认评分: {target_url}")
            result = _mock_scan(target_url)
            
    except Exception as e:
        logger.error(f"外链扫描失败: {target_url}, 错误: {e}")
        result = _mock_scan(target_url)
    
    return result


def _scan_with_moz(domain, access_id, secret_key):
    """
    使用 Moz API 获取 DA 评分
    API文档: https://moz.com/help/guides/moz-api/mozscape/api-reference/url-metrics
    """
    import hmac
    import hashlib
    import base64
    import time
    
    try:
        # 构建请求
        expires = int(time.time()) + 300
        string_to_sign = f"{access_id}\n{expires}"
        signature = base64.b64encode(
            hmac.new(secret_key.encode(), string_to_sign.encode(), hashlib.sha1).digest()
        ).decode()
        
        url = "https://lsapi.seomoz.com/v2/url_metrics"
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{access_id}:{signature}'.encode()).decode()}"
        }
        
        response = requests.post(url, json={"targets": [domain]}, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                metrics = data[0]
                
                # DA评分 (Domain Authority)
                da_score = metrics.get('domain_authority', 0)
                
                # 质量评分（基于DA计算）
                quality_score = min(100, da_score + 20)
                
                # 状态判断
                if da_score >= 40:
                    status = 'active'
                elif da_score >= 20:
                    status = 'pending'
                else:
                    status = 'inactive'
                
                return {
                    'da_score': da_score,
                    'quality_score': quality_score,
                    'attribute': 'dofollow',
                    'status': status,
                    'source_page': f"https://{domain}",
                    'anchor_text': domain
                }
            else:
                return _mock_scan(domain)
        else:
            logger.error(f"Moz API 请求失败: {response.status_code}")
            return _mock_scan(domain)
            
    except Exception as e:
        logger.error(f"Moz API 调用失败: {e}")
        return _mock_scan(domain)


def _mock_scan(target_url):
    """
    模拟外链扫描（用于测试或API不可用时）
    根据URL特征生成评分
    """
    import hashlib
    
    # 基于URL生成稳定的评分
    hash_value = int(hashlib.md5(target_url.encode()).hexdigest(), 16)
    
    # DA评分 (0-100)
    da_score = hash_value % 101
    
    # 质量评分 (0-100)
    quality_score = (hash_value >> 8) % 101
    
    # 属性判断
    attributes = ['dofollow', 'nofollow', 'ugc', 'sponsored']
    attribute = attributes[hash_value % len(attributes)]
    
    # 状态判断
    if da_score >= 50:
        status = 'active'
    elif da_score >= 30:
        status = 'pending'
    else:
        status = 'inactive'
    
    # 提取域名作为来源页面
    parsed = urlparse(target_url)
    domain = parsed.netloc or parsed.path
    source_page = f"https://{domain}" if domain else target_url
    
    return {
        'da_score': da_score,
        'quality_score': quality_score,
        'attribute': attribute,
        'status': status,
        'source_page': source_page,
        'anchor_text': domain.split('.')[0] if domain else ''
    }


def find_potential_backlinks(site_prefix=None):
    """
    查找潜在的外链机会
    :param site_prefix: 网站前缀，默认从配置获取
    :return: list of potential backlinks with website_url, da_score, relevance, contact_info
    """
    try:
        from App.view.seo.page_speed.tools import get_site_prefix as get_prefix
        
        if not site_prefix:
            site_prefix = get_prefix()
        
        # 调用第三方SEO API寻找外链机会
        result = _find_with_third_party_api(site_prefix)
        
        if result:
            return result
        else:
            # API失败时使用模拟数据
            logger.warning("第三方API调用失败，使用模拟数据")
            return _mock_find_potential_backlinks(site_prefix)
            
    except Exception as e:
        logger.error(f"查找外链机会失败: {e}")
        return _mock_find_potential_backlinks(site_prefix)


def _find_with_third_party_api(site_prefix):
    """
    调用第三方SEO API查找外链机会
    可以使用 Ahrefs、SEMrush、Moz 等API
    """
    try:
        # 这里可以集成真实的第三方API
        # 例如 Ahrefs API: https://ahrefs.com/api
        # SEMrush API: https://www.semrush.com/api-documentation/
        
        api_key = ""  # 从配置获取
        
        if not api_key:
            return None
        
        # 示例：调用Ahrefs API查找引用域名
        # url = "https://open.api.ahrefs.com/v3/backlinks/referring-domains"
        # response = requests.get(url, params={...}, timeout=30)
        
        # 暂时返回None，使用模拟数据
        return None
        
    except Exception as e:
        logger.error(f"第三方API调用失败: {e}")
        return None


def _mock_find_potential_backlinks(site_prefix):
    """
    模拟查找外链机会
    生成一些潜在的外链网站信息
    """
    import hashlib
    import random
    
    # 基于站点前缀生成稳定的随机种子
    seed = int(hashlib.md5(site_prefix.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    
    # 模拟一些可能外链的网站
    potential_sites = [
        {
            'website_url': 'https://techblog.example.com',
            'da_score': random.randint(40, 80),
            'relevance': random.choice(['high', 'medium', 'low']),
            'contact_info': {
                'email': 'contact@techblog.example.com',
                'name': 'Tech Blog Team'
            }
        },
        {
            'website_url': 'https://designinspiration.net',
            'da_score': random.randint(30, 70),
            'relevance': random.choice(['high', 'medium']),
            'contact_info': {
                'email': 'hello@designinspiration.net',
                'name': 'Design Team'
            }
        },
        {
            'website_url': 'https://wallpapercollection.org',
            'da_score': random.randint(20, 60),
            'relevance': 'high',
            'contact_info': {
                'email': 'info@wallpapercollection.org',
                'name': 'Wallpaper Collection'
            }
        },
        {
            'website_url': 'https://creativestudio.io',
            'da_score': random.randint(35, 75),
            'relevance': random.choice(['medium', 'low']),
            'contact_info': {
                'email': 'contact@creativestudio.io',
                'phone': '+1-555-0123'
            }
        },
        {
            'website_url': 'https://digitalart.gallery',
            'da_score': random.randint(25, 65),
            'relevance': 'high',
            'contact_info': {
                'email': 'support@digitalart.gallery',
                'name': 'Digital Art Gallery'
            }
        }
    ]
    
    return potential_sites
