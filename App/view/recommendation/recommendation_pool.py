"""
推荐算法池化管理
基于Redis存储用户个性化推荐池和冷启动池
支持多算法融合和快速分页
"""
import json
from tool.token_tools import _redis
from App.view.recommendation.user_interest_algorithm import (
    get_user_top_tags,
    filter_by_ctr,
    get_layer_score_wallpapers,
    get_cold_start_wallpaper_ids,
    get_ctr_based_wallpapers
)


# Redis键前缀
PERSONAL_POOL_PREFIX = "recommend:personal_pool:"
COLD_POOL_PREFIX = "recommend:cold_pool:"
CTR_POOL_PREFIX = "recommend:ctr_pool:"
MIXED_POOL_PREFIX = "recommend:mixed_pool:"

# 过期时间（秒）
POOL_EXPIRE_TIME = 600  # 10分钟


def build_personal_pool(unique_id, platform, order):
    """构建个性化推荐池
    
    流程：
    1. 获取用户TOP标签
    2. 使用CTR过滤出高质量标签
    3. 根据分层评分获取壁纸ID
    4. 存入Redis
    
    Args:
        unique_id: 用户唯一标识（不能为空）
        platform: 平台类型 'PC' 或 'PHONE'
        order: 排序类型 'hot' 或 'home'
        
    Returns:
        list: 壁纸ID列表
    """
    try:
        # 防御性检查：确保 unique_id 不为空
        if not unique_id:
            print(f"[Error] unique_id is empty, cannot build personal pool")
            return []
        
        # 1. 获取用户标签
        user_tags = get_user_top_tags(unique_id, top_n=10, sync_from_track=True)
        
        if not user_tags:
            return []
        
        # 2. CTR过滤
        best_tags = filter_by_ctr(user_tags, min_ctr=0.01)
        
        if not best_tags:
            # 如果没有高CTR标签，使用原始标签
            best_tags = user_tags
        
        # 3. 分层评分获取壁纸
        personal_ids = get_layer_score_wallpapers(best_tags, platform, limit=800)
        
        # 4. 存入Redis
        redis_key = f"{PERSONAL_POOL_PREFIX}{unique_id}:{platform}:{order}"
        _redis.setKey(redis_key, json.dumps(personal_ids), ex=POOL_EXPIRE_TIME)
        
        print(f"[Personal Pool] unique_id: {unique_id}, platform: {platform}, order: {order}, count: {len(personal_ids)}")
        return personal_ids
        
    except Exception as e:
        print(f"[Build Personal Pool Failed] error: {e}")
        return []


def build_cold_pool(platform, order):
    """构建冷启动推荐池
    
    Args:
        platform: 平台类型 'PC' 或 'PHONE'
        order: 排序类型 'hot' 或 'home'
        
    Returns:
        list: 壁纸ID列表
    """
    try:
        # 获取冷启动壁纸（策略壁纸或热门壁纸）
        cold_ids = get_cold_start_wallpaper_ids(platform, limit=600)
        
        # 存入Redis
        redis_key = f"{COLD_POOL_PREFIX}{platform}:{order}"
        _redis.setKey(redis_key, json.dumps(cold_ids), ex=POOL_EXPIRE_TIME)
        
        print(f"[Cold Pool] platform: {platform}, order: {order}, count: {len(cold_ids)}")
        return cold_ids
        
    except Exception as e:
        print(f"[Build Cold Pool Failed] error: {e}")
        return []


def build_ctr_pool(unique_id, platform, order):
    """构建CTR标签推荐池
    
    基于全局高CTR标签获取壁纸，增加数据丰富度
    
    Args:
        unique_id: 用户唯一标识
        platform: 平台类型 'PC' 或 'PHONE'
        order: 排序类型 'hot' 或 'home'
        
    Returns:
        list: 壁纸ID列表
    """
    try:
        # 防御性检查
        if not unique_id:
            print(f"[Error] unique_id is empty, cannot build ctr pool")
            return []
        
        # 获取用户标签（用于参考，但不限制）
        user_tags = get_user_top_tags(unique_id, top_n=10, sync_from_track=True)
        
        # 基于CTR获取壁纸池
        ctr_ids = get_ctr_based_wallpapers(user_tags, platform, min_ctr=0.01, limit=600)
        
        # 存入Redis
        redis_key = f"{CTR_POOL_PREFIX}{unique_id}:{platform}:{order}"
        _redis.setKey(redis_key, json.dumps(ctr_ids), ex=POOL_EXPIRE_TIME)
        
        print(f"[CTR Pool] unique_id: {unique_id}, platform: {platform}, order: {order}, count: {len(ctr_ids)}")
        return ctr_ids
        
    except Exception as e:
        print(f"[Build CTR Pool Failed] error: {e}")
        return []


def merge_three_pools(personal_ids, cold_ids, ctr_ids, ratio=(0.5, 0.2, 0.3)):
    """混合三个推荐池（个性化:冷启动:CTR = 5:2:3）
    
    Args:
        personal_ids: 个性化壁纸ID列表
        cold_ids: 冷启动壁纸ID列表
        ctr_ids: CTR标签壁纸ID列表
        ratio: 各池占比（personal, cold, ctr），默认(0.5, 0.2, 0.3)
        
    Returns:
        list: 混合后的壁纸ID列表
    """
    try:
        if not personal_ids and not cold_ids and not ctr_ids:
            return []
        
        # 如果只有一个池有数据，直接返回
        if not personal_ids and not cold_ids:
            return ctr_ids
        if not personal_ids and not ctr_ids:
            return cold_ids
        if not cold_ids and not ctr_ids:
            return personal_ids
        
        # 计算各自的数量
        total_count = min(len(personal_ids) + len(cold_ids) + len(ctr_ids), 2000)  # 最多2000张
        personal_count = int(total_count * ratio[0])
        cold_count = int(total_count * ratio[1])
        ctr_count = total_count - personal_count - cold_count
        
        # 截取对应数量
        personal_part = personal_ids[:personal_count]
        cold_part = cold_ids[:cold_count]
        ctr_part = ctr_ids[:ctr_count]
        
        # 交替合并（避免同一来源连续出现）
        merged = []
        p_idx, c_idx, t_idx = 0, 0, 0
        
        while p_idx < len(personal_part) or c_idx < len(cold_part) or t_idx < len(ctr_part):
            # 按顺序从三个池中取
            if p_idx < len(personal_part):
                merged.append(personal_part[p_idx])
                p_idx += 1
            
            if t_idx < len(ctr_part):
                merged.append(ctr_part[t_idx])
                t_idx += 1
            
            if c_idx < len(cold_part):
                merged.append(cold_part[c_idx])
                c_idx += 1
        
        print(f"[Merge Three Pools] personal: {len(personal_part)}, cold: {len(cold_part)}, ctr: {len(ctr_part)}, merged: {len(merged)}")
        return merged
        
    except Exception as e:
        print(f"[Merge Three Pools Failed] error: {e}")
        # 降级：简单拼接
        result = []
        result.extend(personal_ids or [])
        result.extend(cold_ids or [])
        result.extend(ctr_ids or [])
        return result


def get_or_build_mixed_pool(unique_id, platform, order):
    """获取或构建混合推荐池
    
    优先从Redis读取，不存在则构建
    
    Args:
        unique_id: 用户唯一标识（不能为空）
        platform: 平台类型 'PC' 或 'PHONE'
        order: 排序类型 'hot' 或 'home'
        
    Returns:
        list: 混合后的壁纸ID列表
    """
    try:
        # 防御性检查：确保 unique_id 不为空
        if not unique_id:
            print(f"[Error] unique_id is empty, cannot build mixed pool")
            return []
        
        redis_key = f"{MIXED_POOL_PREFIX}{unique_id}:{platform}:{order}"
        
        # 尝试从Redis读取
        cached_data = _redis.getKey(redis_key)
        if cached_data:
            pool_ids = json.loads(cached_data)
            print(f"[Mixed Pool Cache Hit] unique_id: {unique_id}, platform: {platform}, order: {order}, count: {len(pool_ids)}")
            return pool_ids
        
        # Redis中没有，需要构建
        print(f"[Mixed Pool Cache Miss] building for unique_id: {unique_id}, platform: {platform}, order: {order}")
        
        # 1. 构建个性化池
        personal_ids = build_personal_pool(unique_id, platform, order)
        
        # 2. 构建冷启动池
        cold_ids = build_cold_pool(platform, order)
        
        # 3. 构建CTR池
        ctr_ids = build_ctr_pool(unique_id, platform, order)
        
        # 4. 三路混合（5:2:3）
        mixed_ids = merge_three_pools(personal_ids, cold_ids, ctr_ids, ratio=(0.5, 0.2, 0.3))
        
        # 5. 存入Redis
        if mixed_ids:
            _redis.setKey(redis_key, json.dumps(mixed_ids), ex=POOL_EXPIRE_TIME)
        
        return mixed_ids
        
    except Exception as e:
        print(f"[Get Or Build Mixed Pool Failed] error: {e}")
        return []


def get_pool_page(unique_id, platform, order, page_num, page_size):
    """从推荐池中获取指定页的数据
    
    Args:
        unique_id: 用户唯一标识
        platform: 平台类型 'PC' 或 'PHONE'
        order: 排序类型 'hot' 或 'home'
        page_num: 页码（从1开始）
        page_size: 每页数量
        
    Returns:
        tuple: (当前页壁纸ID列表, 总数量)
    """
    try:
        # 获取或构建混合池
        pool_ids = get_or_build_mixed_pool(unique_id, platform, order)
        
        if not pool_ids:
            return [], 0
        
        total_count = len(pool_ids)
        
        # 计算分页
        start_idx = (page_num - 1) * page_size
        end_idx = start_idx + page_size
        
        # 切片获取当前页
        page_ids = pool_ids[start_idx:end_idx]
        
        return page_ids, total_count
        
    except Exception as e:
        print(f"[Get Pool Page Failed] error: {e}")
        return [], 0


def invalidate_pool(unique_id, platform, order=None):
    """清除用户的推荐池缓存
    
    Args:
        unique_id: 用户唯一标识
        platform: 平台类型 'PC' 或 'PHONE'
        order: 排序类型 'hot' 或 'home'（可选，不传则清除所有）
    """
    try:
        orders = [order] if order else ['hot', 'home']
        
        for ord in orders:
            personal_key = f"{PERSONAL_POOL_PREFIX}{unique_id}:{platform}:{ord}"
            ctr_key = f"{CTR_POOL_PREFIX}{unique_id}:{platform}:{ord}"
            mixed_key = f"{MIXED_POOL_PREFIX}{unique_id}:{platform}:{ord}"
            
            _redis.delKey(personal_key)
            _redis.delKey(ctr_key)
            _redis.delKey(mixed_key)
        
        print(f"[Invalidate Pool] unique_id: {unique_id}, platform: {platform}, order: {order or 'all'}")
        
    except Exception as e:
        print(f"[Invalidate Pool Failed] error: {e}")
