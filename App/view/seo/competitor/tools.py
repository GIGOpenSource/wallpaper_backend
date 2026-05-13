# -*- coding: UTF-8 -*-
"""
竞争对手工具类
调用第三方API获取竞争对手的SEO数据
"""
import requests
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# 5118 API配置
API_KEY = "8D6D84B3096A45F98C6220774C6AB752"
API_URL = "http://apis.5118.com/keyword/pc/v2"


def extract_domain(url):
    """
    从URL中提取域名（保留www前缀）
    :param url: 完整URL
    :return: 域名（包含www）
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # 保留 www. 前缀，不做去除处理
        return domain.lower()
    except Exception as e:
        logger.error(f"提取域名失败: {url}, 错误: {e}")
        return None


def fetch_competitor_data(domain):
    """
    获取竞争对手的SEO数据
    对接5118 API获取关键词数据（自动分页获取所有数据）
    
    :param domain: 域名
    :return: dict containing domain_authority, monthly_traffic, keyword_count, backlink_count, growth_trend, keywords
    """
    result = {
        'domain_authority': 0,
        'monthly_traffic': 0,
        'keyword_count': 0,
        'backlink_count': 0,
        'growth_trend': 'stable',
        'keywords': []  # 新增：关键词列表
    }
    
    try:
        # 调用5118 API获取所有关键词数据（自动分页）
        keywords_data = fetch_all_keywords_from_5118(domain)
        
        if keywords_data:
            result['keywords'] = keywords_data.get('keywords', [])
            result['keyword_count'] = keywords_data.get('total', 0)
            
            # 根据关键词数量估算其他指标
            keyword_count = result['keyword_count']
            if keyword_count > 10000:
                result['domain_authority'] = min(100, keyword_count // 1000)
                result['monthly_traffic'] = keyword_count * 10
                result['backlink_count'] = keyword_count * 5
                result['growth_trend'] = 'up'
            elif keyword_count > 1000:
                result['domain_authority'] = min(80, keyword_count // 500)
                result['monthly_traffic'] = keyword_count * 5
                result['backlink_count'] = keyword_count * 3
                result['growth_trend'] = 'stable'
            else:
                result['domain_authority'] = min(50, keyword_count // 100)
                result['monthly_traffic'] = keyword_count * 2
                result['backlink_count'] = keyword_count * 2
                result['growth_trend'] = 'down'
        else:
            # API调用失败，使用模拟数据
            logger.warning(f"5118 API调用失败，使用模拟数据: {domain}")
            mock_data = _mock_competitor_data(domain)
            result.update(mock_data)
            
    except Exception as e:
        logger.error(f"获取竞争对手数据失败: {domain}, 错误: {e}")
        # 出错时使用模拟数据
        mock_data = _mock_competitor_data(domain)
        result.update(mock_data)
    
    return result


def fetch_keywords_from_5118(domain, page_index=1):
    """
    从5118 API获取单页关键词数据
    
    :param domain: 域名
    :param page_index: 页码
    :return: dict with total, page_count, page_size, page_index and keywords list
    """
    try:
        headers = {
            'Authorization': API_KEY,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'url': domain,
            'page_index': page_index
        }
        
        response = requests.post(API_URL, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('errcode') == '0':
            api_data = result.get('data', {})
            keywords_list = api_data.get('pc', [])
            total = api_data.get('total', 0)
            page_count = api_data.get('page_count', 1)
            page_size = api_data.get('page_size', 500)
            
            # 转换关键词数据格式
            formatted_keywords = []
            for kw in keywords_list:
                formatted_keywords.append({
                    'keyword': kw.get('keyword', ''),
                    'rank': kw.get('rank', 0),
                    'page_title': kw.get('page_title', ''),
                    'bidword_companycount': kw.get('bidword_companycount', 0),
                    'long_keyword_count': kw.get('long_keyword_count', 0),
                    'index': kw.get('index', 0)
                })
            
            return {
                'total': total,
                'page_count': page_count,
                'page_size': page_size,
                'page_index': page_index,
                'keywords': formatted_keywords
            }
        else:
            logger.error(f"5118 API返回错误: {result.get('errmsg', '未知错误')}")
            return None
            
    except Exception as e:
        logger.error(f"调用5118 API失败: {e}")
        return None


def fetch_all_keywords_from_5118(domain):
    """
    从5118 API获取所有页的关键词数据
    
    :param domain: 域名
    :return: dict with total and all keywords list
    """
    try:
        # 先获取第一页，得到总页数
        first_page = fetch_keywords_from_5118(domain, page_index=1)
        
        if not first_page:
            return None
        
        all_keywords = first_page.get('keywords', [])
        total = first_page.get('total', 0)
        page_count = first_page.get('page_count', 1)
        
        # 如果有多页，继续获取剩余页
        if page_count > 1:
            for page_index in range(2, page_count + 1):
                try:
                    logger.info(f"正在获取第 {page_index}/{page_count} 页关键词数据")
                    page_data = fetch_keywords_from_5118(domain, page_index=page_index)
                    if page_data:
                        all_keywords.extend(page_data.get('keywords', []))
                except Exception as e:
                    logger.error(f"获取第 {page_index} 页失败: {e}")
                    continue
        
        logger.info(f"成功获取 {len(all_keywords)} 个关键词，共 {page_count} 页")
        
        return {
            'total': total,
            'keywords': all_keywords
        }
        
    except Exception as e:
        logger.error(f"获取所有关键词数据失败: {e}")
        return None


def _mock_competitor_data(domain):
    """
    模拟竞争对手数据（用于测试或API不可用时）
    根据域名生成一些合理的模拟数据
    """
    import hashlib
    
    # 基于域名生成稳定的模拟数据
    hash_value = int(hashlib.md5(domain.encode()).hexdigest(), 16)
    
    # 模拟域名权重 (0-100)
    domain_authority = hash_value % 101
    
    # 模拟月流量 (1000-1000000)
    monthly_traffic = 1000 + (hash_value % 999000)
    
    # 模拟关键词数 (10-10000)
    keyword_count = 10 + (hash_value % 9990)
    
    # 模拟外链数 (100-50000)
    backlink_count = 100 + (hash_value % 49900)
    
    # 模拟增长趋势
    trend_value = hash_value % 3
    if trend_value == 0:
        growth_trend = 'up'
    elif trend_value == 1:
        growth_trend = 'stable'
    else:
        growth_trend = 'down'
    
    return {
        'domain_authority': domain_authority,
        'monthly_traffic': monthly_traffic,
        'keyword_count': keyword_count,
        'backlink_count': backlink_count,
        'growth_trend': growth_trend
    }
