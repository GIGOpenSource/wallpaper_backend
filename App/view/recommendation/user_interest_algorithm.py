"""
用户兴趣标签推荐算法
基于用户行为数据计算兴趣分数，提供个性化壁纸推荐
"""
import math
from urllib.parse import unquote
from datetime import timedelta
from django.utils import timezone
from models.models import UserInterestTag, Wallpapers, TrackEvent


# ==================== 常量配置 ====================
MAX_STAY_SECONDS = 60  # 最大停留时长（秒）
DECAY_RATE = 0.1  # 时间衰减率（每天）
TOP_N_TAGS = 10  # 保留的TOP标签数量
CLEANUP_INTERVAL = 10  # 每N次更新清理一次TOP10

CORE_INTEREST_THRESHOLD = 0.7  # 核心兴趣阈值
MAIN_INTEREST_THRESHOLD = 0.4  # 主要兴趣阈值

RECOMMENDATION_ALLOCATION = {
    'top_3': 3,      # 第1-3标签：各取3张
    'mid_4': 2,      # 第4-7标签：各取2张
    'bottom_3': 1,   # 第8-10标签：各取1张
}


def parse_tags_from_path(page_path):
    """从页面路径解析一级标签和二级标签
    
    示例：
    - "/tag/wallpapers%204k" -> ("wallpapers 4k", None)
    - "/tag/Samurai%20Girl" -> ("samurai girl", None)
    - "/tag/abstract" -> ("abstract", None)
    
    Args:
        page_path: 页面路径，如 "/tag/wallpapers%204k"
        
    Returns:
        tuple: (一级标签, 二级标签) 或 (None, None)
    """
    if not page_path or '/tag/' not in page_path:
        return None, None
    
    try:
        tag_part = page_path.split('/tag/')[-1].strip()
        if not tag_part:
            return None, None
        
        # URL解码：将 %20 等编码转换为空格
        tag_part = unquote(tag_part)
        
        tag_part = tag_part.split('?')[0].split('#')[0]
        tags = tag_part.split()
        
        if len(tags) == 0:
            return None, None
        elif len(tags) == 1:
            return tags[0].lower(), None
        else:
            tag_level1 = tags[0].lower()
            tag_level2 = ' '.join(tags[1:]).lower()
            return tag_level1, tag_level2
            
    except Exception as e:
        print(f"[Tag Parse Error] page_path: {page_path}, error: {e}")
        return None, None


def calculate_stay_score(page_stay):
    """根据停留时长计算基础分数（0~1分）
    
    使用对数函数归一化，60秒封顶
    公式：score = log(1 + stay) / log(1 + 60)
    
    Args:
        page_stay: 停留秒数
        
    Returns:
        float: 归一化分数（0~1）
    """
    if page_stay <= 0:
        return 0.0
    
    effective_stay = min(page_stay, MAX_STAY_SECONDS)
    score = math.log1p(effective_stay) / math.log1p(MAX_STAY_SECONDS)
    
    return round(score, 4)


def apply_time_decay(old_score, last_interaction_time):
    """应用时间指数衰减
    
    兴趣分数随时间自然降低，每天衰减10%
    公式：new_score = old_score * e^(-0.1 * days)
    
    Args:
        old_score: 原始分数
        last_interaction_time: 上次交互时间（datetime对象）
        
    Returns:
        float: 衰减后的分数
    """
    if not last_interaction_time:
        return old_score
    
    now = timezone.now()
    days_since_interaction = (now - last_interaction_time).total_seconds() / 86400.0
    decayed_score = old_score * math.exp(-DECAY_RATE * days_since_interaction)
    
    return round(decayed_score, 4)


def update_user_tags(unique_id, page_path, page_stay, user_id=None, behavior_type='tag_detail'):
    """更新用户兴趣标签
    
    核心流程：
    1. 解析页面路径得到标签
    2. 计算停留时长分数（根据行为类型加权）
    3. 创建或更新标签记录
    4. 如果已存在，应用时间衰减后累加新分数
    5. 注意：TOP10清理在 get_user_top_tags 中每10次更新时执行
    
    Args:
        unique_id: 用户唯一标识
        page_path: 页面路径
        page_stay: 停留秒数
        user_id: 用户ID（可选，登录用户才有）
        behavior_type: 行为类型 ('tag_detail' 或 'retrieve')
        
    Returns:
        bool: 是否成功更新
    """
    try:
        tag_level1, tag_level2 = parse_tags_from_path(page_path)
        if not tag_level1:
            return False
        
        stay_score = calculate_stay_score(page_stay)
        if stay_score <= 0:
            return False
        
        # 根据行为类型调整权重
        if behavior_type == 'retrieve':
            # 壁纸详情页行为权重更高
            stay_score *= 1.2  # 增加20%权重
        elif behavior_type == 'tag_detail':
            # 标签分类页行为权重较低
            stay_score *= 1.0  # 基础权重
        else:
            # 其他行为类型权重
            stay_score *= 1.0
        
        # 限制分数上限
        stay_score = min(stay_score, 1.0)
        
        now = timezone.now()
        
        tag_obj, created = UserInterestTag.objects.get_or_create(
            unique_id=unique_id,
            tag_level1=tag_level1,
            tag_level2=tag_level2,
            defaults={
                'user_id': user_id,
                'score': stay_score,
                'last_interaction_time': now,
                'interaction_count': 1
            }
        )
        
        if not created:
            # 应用时间衰减
            decayed_score = apply_time_decay(tag_obj.score, tag_obj.last_interaction_time)
            
            # 计算新权重：考虑行为类型和交互次数
            weight = 1.0 / math.sqrt(tag_obj.interaction_count + 1)
            
            # 组合新旧分数
            new_score = decayed_score + stay_score * weight
            
            tag_obj.score = min(new_score, 10.0)
            tag_obj.last_interaction_time = now
            tag_obj.interaction_count += 1
            if user_id and not tag_obj.user_id:
                tag_obj.user_id = user_id
            tag_obj.save()
        
        return True
        
    except Exception as e:
        print(f"[Update User Tags Failed] unique_id: {unique_id}, error: {e}")
        return False


def _cleanup_low_score_tags(unique_id):
    """清理低分标签，只保留TOP10
    
    当用户标签超过10个时，删除分数最低的标签
    
    Args:
        unique_id: 用户唯一标识
    """
    try:
        all_tags = UserInterestTag.objects.filter(
            unique_id=unique_id
        ).order_by('-score')
        
        if all_tags.count() > TOP_N_TAGS:
            tags_to_delete = all_tags[TOP_N_TAGS:]
            tags_to_delete.delete()
            
    except Exception as e:
        print(f"[Cleanup Low Score Tags Failed] unique_id: {unique_id}, error: {e}")


def get_user_top_tags(unique_id, top_n=TOP_N_TAGS, sync_from_track=True):
    """获取用户TOP N兴趣标签
    
    核心流程：
    1. （可选）从 TrackEvent 表同步最新行为数据
    2. 查询用户所有标签，按分数降序排列
    3. 返回前N个标签及其详细信息
    4. 每10次更新清理一次TOP10（删除低分标签）
    
    Args:
        unique_id: 用户唯一标识
        top_n: 返回的标签数量
        sync_from_track: 是否从 TrackEvent 同步数据（默认True）
        
    Returns:
        list: 标签列表，按分数从高到低排序
              每个元素包含：tag_level1, tag_level2, score, interaction_count, interest_level
    """
    try:
        # 从 TrackEvent 同步数据
        if sync_from_track:
            sync_user_tags_from_track_event(unique_id)
        
        tags = UserInterestTag.objects.filter(
            unique_id=unique_id
        ).order_by('-score')[:top_n]
        
        result = []
        for tag in tags:
            result.append({
                'tag_level1': tag.tag_level1,
                'tag_level2': tag.tag_level2,
                'score': tag.score,
                'interaction_count': tag.interaction_count,
                'interest_level': _classify_interest_level(tag.score)
            })
        
        # Cleanup TOP10 every 10 updates
        if tags and tags[0].interaction_count % CLEANUP_INTERVAL == 0:
            _cleanup_low_score_tags(unique_id)
        
        return result
        
    except Exception as e:
        print(f"[Get User Tags Failed] unique_id: {unique_id}, error: {e}")
        return []


def _classify_interest_level(score):
    """根据分数分类兴趣等级
    
    分数代表该标签在所有标签中的占比（0-1之间）
    - core（核心兴趣）: score >= 0.7 （前3个标签）
    - main（主要兴趣）: 0.4 <= score < 0.7 （中间标签）
    - potential（潜在兴趣）: score < 0.4 （后几个标签）
    
    Args:
        score: 兴趣分数（占比）
        
    Returns:
        str: 'core', 'main', 或 'potential'
    """
    if score >= CORE_INTEREST_THRESHOLD:
        return 'core'
    elif score >= MAIN_INTEREST_THRESHOLD:
        return 'main'
    else:
        return 'potential'


def get_cold_start_wallpaper_ids(platform, limit=50):
    """冷启动推荐：使用策略壁纸
    
    当新用户没有标签数据时，使用此方法返回推荐壁纸
    
    核心流程：
    1. 查找匹配平台的活跃策略（优先当前语言，其次global）
    2. 如果找到策略，返回策略关联的壁纸ID
    3. 如果没有策略，返回热门壁纸
    
    Args:
        platform: 平台类型 'PC' 或 'PHONE'
        limit: 返回数量（默认50，提供足够的壁纸池）
        
    Returns:
        list: 壁纸ID列表
    """
    from models.models import RecommendStrategy, StrategyWallpaperRelation
    from django.utils.translation import get_language
    
    try:
        now = timezone.now()
        current_language = get_language()
        
        platforms_to_try = [platform.lower()] if platform in ['pc', 'phone'] else ['all']
        if 'all' not in platforms_to_try:
            platforms_to_try.append('all')
        
        matched_strategy = None
        for p in platforms_to_try:
            strategies_with_area = RecommendStrategy.objects.filter(
                platform=p, 
                status='active',
                apply_area=current_language
            ).order_by('-priority', '-created_at')
            
            for strategy in strategies_with_area:
                if strategy.start_time and now < strategy.start_time:
                    continue
                if strategy.end_time and now > strategy.end_time:
                    continue
                matched_strategy = strategy
                break
            
            if matched_strategy:
                break
                
            strategies_global = RecommendStrategy.objects.filter(
                platform=p, 
                status='active',
                apply_area='global'
            ).order_by('-priority', '-created_at')
            
            for strategy in strategies_global:
                if strategy.start_time and now < strategy.start_time:
                    continue
                if strategy.end_time and now > strategy.end_time:
                    continue
                matched_strategy = strategy
                break
                
            if matched_strategy:
                break
        
        if not matched_strategy:
            queryset = Wallpapers.objects.exclude(audit_status='rejected')
            if platform == 'PC':
                queryset = queryset.filter(category__id=1)
            elif platform == 'PHONE':
                queryset = queryset.filter(category__id=2)
            
            wallpaper_ids = list(queryset.order_by('-hot_score', '-created_at')
                               .values_list('id', flat=True)[:limit])
            return wallpaper_ids
        
        relation_qs = StrategyWallpaperRelation.objects.filter(
            strategy=matched_strategy
        ).order_by('sort_order', '-created_at')
        
        if matched_strategy.content_limit and matched_strategy.content_limit > 0:
            relation_qs = relation_qs[:matched_strategy.content_limit]
        
        wallpaper_ids = list(relation_qs.values_list('wallpaper_id', flat=True))
        
        if limit and len(wallpaper_ids) > limit:
            wallpaper_ids = wallpaper_ids[:limit]
        
        return wallpaper_ids
        
    except Exception as e:
        print(f"[Cold Start Recommendation Failed] platform: {platform}, error: {e}")
        return []


def get_tag_based_wallpaper_ids(unique_id, platform, limit=20):
    """
    Personalized recommendations based on user interest tags
    Returns wallpaper ID list with diversity (different results each call)
    """
    top_tags = get_user_top_tags(unique_id)
    
    if not top_tags:
        return []
    
    try:
        recommended_ids = []
        seen_ids = set()
        
        allocation_rules = [
            (0, 3, RECOMMENDATION_ALLOCATION['top_3']),
            (3, 7, RECOMMENDATION_ALLOCATION['mid_4']),
            (7, 10, RECOMMENDATION_ALLOCATION['bottom_3']),
        ]
        
        for start_idx, end_idx, per_tag_count in allocation_rules:
            tags_slice = top_tags[start_idx:end_idx]
            
            for tag_info in tags_slice:
                if len(recommended_ids) >= limit:
                    break
                
                tag_wallpaper_ids = _get_wallpapers_by_tag(
                    tag_info['tag_level1'],
                    tag_info['tag_level2'],
                    platform,
                    per_tag_count,
                    exclude_ids=seen_ids
                )
                
                for wid in tag_wallpaper_ids:
                    if wid not in seen_ids:
                        recommended_ids.append(wid)
                        seen_ids.add(wid)
        
        if len(recommended_ids) < limit:
            remaining = limit - len(recommended_ids)
            supplementary_ids = _get_supplementary_wallpapers(
                platform, remaining, exclude_ids=seen_ids
            )
            recommended_ids.extend(supplementary_ids)
        
        return recommended_ids[:limit]
        
    except Exception as e:
        print(f"[Tag-based Recommendation Failed] error: {e}")
        return []


def _get_wallpapers_by_tag(tag_level1, tag_level2, platform, count, exclude_ids=None):
    """Get wallpaper IDs by tag with random ordering for diversity"""
    try:
        from models.models import WallpaperTag
        
        tag_query = WallpaperTag.objects.filter(name__icontains=tag_level1)
        if tag_level2:
            tag_query = tag_query.filter(name__icontains=tag_level2)
        
        matched_tags = list(tag_query.values_list('id', flat=True))
        
        if not matched_tags:
            return []
        
        queryset = Wallpapers.objects.filter(
            tags__id__in=matched_tags
        ).exclude(audit_status='rejected')
        
        if platform == 'PC':
            queryset = queryset.filter(category__id=1)
        elif platform == 'PHONE':
            queryset = queryset.filter(category__id=2)
        
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)
        
        # Random ordering for diversity (different results each call)
        wallpaper_ids = list(queryset.order_by('?').values_list('id', flat=True)[:count])
        
        return wallpaper_ids
        
    except Exception as e:
        print(f"[Get Wallpapers By Tag Failed] tag: {tag_level1}/{tag_level2}, error: {e}")
        return []


def _get_supplementary_wallpapers(platform, count, exclude_ids=None):
    """Get supplementary wallpapers when tag recommendations are insufficient"""
    try:
        queryset = Wallpapers.objects.exclude(audit_status='rejected')
        
        if platform == 'PC':
            queryset = queryset.filter(category__id=1)
        elif platform == 'PHONE':
            queryset = queryset.filter(category__id=2)
        
        if exclude_ids:
            queryset = queryset.exclude(id__in=exclude_ids)
        
        wallpaper_ids = list(queryset.order_by('-hot_score', '-created_at')
                           .values_list('id', flat=True)[:count])
        
        return wallpaper_ids
        
    except Exception as e:
        print(f"[Get Supplementary Wallpapers Failed] error: {e}")
        return []


def sync_user_tags_from_track_event(unique_id, user_id=None, max_events=500):
    """从 TrackEvent 表同步用户行为数据，重新计算兴趣标签
    
    核心逻辑：
    1. 查询用户所有 page_stay 事件
    2. 按标签分组统计总时长（考虑行为权重）
    3. 计算每个标签的占比 = 标签总时长 / 所有标签总时长
    4. 覆盖更新到 UserInterestTag 表
    
    Args:
        unique_id: 用户唯一标识
        user_id: 用户ID（可选）
        max_events: 最大处理事件数量（默认500）
        
    Returns:
        int: 更新的标签数量
    """
    try:
        # 查询用户的 page_stay 事件
        events = TrackEvent.objects.filter(
            unique_id=unique_id,
            event_type='page_stay',
            page_stay__gt=0,
            page_type__in=['tag_detail', 'retrieve']
        ).order_by('-created_at')[:max_events]
        
        if not events:
            return 0
        
        # 按标签分组统计加权时长
        tag_duration_map = {}  # {(tag_level1, tag_level2): weighted_duration}
        
        for event in events:
            if not event.page_path or not event.page_stay:
                continue
            
            page_type = event.page_type
            page_path = event.page_path
            stay_time = event.page_stay
            
            # 获取该事件涉及的标签列表
            tags_list = []
            
            if page_type == 'tag_detail':
                # 方式一：直接从路径提取标签
                tag_level1, tag_level2 = parse_tags_from_path(page_path)
                if tag_level1:
                    tags_list.append((tag_level1, tag_level2))
                    
            elif page_type == 'retrieve':
                # 方式二：从壁纸ID反向获取标签
                tags_list = _get_tags_from_wallpaper_path(page_path)
            
            # 为每个标签累加加权时长
            weight = 1.2 if page_type == 'retrieve' else 1.0
            weighted_duration = stay_time * weight
            
            for tag_key in tags_list:
                if tag_key not in tag_duration_map:
                    tag_duration_map[tag_key] = 0.0
                tag_duration_map[tag_key] += weighted_duration
        
        if not tag_duration_map:
            return 0
        
        # 计算总时长
        total_duration = sum(tag_duration_map.values())
        if total_duration == 0:
            return 0
        
        # 计算每个标签的占比并更新数据库
        now = timezone.now()
        updated_count = 0
        
        for (tag_level1, tag_level2), duration in tag_duration_map.items():
            # 计算占比（归一化到 0-1 范围）
            ratio = duration / total_duration
            
            # 使用占比作为分数（可以乘以系数调整范围）
            score = ratio
            
            # 更新或创建标签记录
            tag_obj, created = UserInterestTag.objects.update_or_create(
                unique_id=unique_id,
                tag_level1=tag_level1,
                tag_level2=tag_level2,
                defaults={
                    'user_id': user_id,
                    'score': round(score, 4),
                    'last_interaction_time': now,
                    'interaction_count': 1
                }
            )
            updated_count += 1
        
        # 清理低分标签，只保留TOP10
        _cleanup_low_score_tags(unique_id)
        
        print(f"[Sync Tags] unique_id: {unique_id}, processed {len(events)} events, updated {updated_count} tags")
        return updated_count
        
    except Exception as e:
        print(f"[Sync Tags Failed] unique_id: {unique_id}, error: {e}")
        return 0


def _get_tags_from_wallpaper_path(page_path):
    """从壁纸详情页路径提取标签列表
    
    Args:
        page_path: 页面路径，如 /wallpaper/805559
        
    Returns:
        list: [(tag_level1, tag_level2), ...] 标签元组列表
    """
    try:
        if '/wallpaper/' not in page_path:
            return []
        
        wallpaper_id_str = page_path.split('/wallpaper/')[-1].strip()
        wallpaper_id_str = wallpaper_id_str.split('?')[0].split('#')[0]
        
        if not wallpaper_id_str.isdigit():
            return []
        
        wallpaper_id = int(wallpaper_id_str)
        
        # 获取壁纸及其标签
        wallpaper = Wallpapers.objects.prefetch_related('tags').get(id=wallpaper_id)
        tags = wallpaper.tags.all()
        
        result = []
        for tag in tags:
            # 将标签名称转换为 (level1, level2) 格式
            tag_name = tag.name.lower()
            # 如果标签名包含空格，第一个词为 level1，其余为 level2
            parts = tag_name.split()
            if len(parts) == 1:
                result.append((parts[0], None))
            else:
                result.append((parts[0], ' '.join(parts[1:])))
        
        return result
        
    except Wallpapers.DoesNotExist:
        return []
    except Exception as e:
        print(f"[Get Tags From Wallpaper Failed] path: {page_path}, error: {e}")
        return []


def filter_by_ctr(user_tags, min_ctr=0.01):
    """根据CTR过滤用户标签，保留高点击率的标签
    
    Args:
        user_tags: 用户标签列表，每个元素包含 tag_level1, tag_level2
        min_ctr: 最小CTR阈值（默认0.01）
        
    Returns:
        list: 过滤后的标签列表
    """
    from models.models import WallpaperTag, WallpaperTagCTR
    
    try:
        best_tags = []
        
        for tag_info in user_tags:
            tag_level1 = tag_info.get('tag_level1')
            tag_level2 = tag_info.get('tag_level2')
            
            if not tag_level1:
                continue
            
            # 查询标签
            tag_query = WallpaperTag.objects.filter(name__icontains=tag_level1)
            if tag_level2:
                tag_query = tag_query.filter(name__icontains=tag_level2)
            
            matched_tag = tag_query.first()
            if not matched_tag:
                continue
            
            # 查询CTR数据
            try:
                ctr_data = WallpaperTagCTR.objects.get(tag=matched_tag)
                ctr = ctr_data.click_count / ctr_data.impression_count if ctr_data.impression_count > 0 else 0
                
                # CTR高于阈值的标签保留
                if ctr >= min_ctr:
                    best_tags.append({
                        **tag_info,
                        'ctr': ctr,
                        'tag_id': matched_tag.id
                    })
            except WallpaperTagCTR.DoesNotExist:
                # 没有CTR数据的标签也保留（新标签）
                best_tags.append({
                    **tag_info,
                    'ctr': 0,
                    'tag_id': matched_tag.id
                })
        
        # 按CTR降序排序
        best_tags.sort(key=lambda x: x['ctr'], reverse=True)
        
        return best_tags
        
    except Exception as e:
        print(f"[Filter By CTR Failed] error: {e}")
        return user_tags


def get_layer_score_wallpapers(best_tags, platform, limit=300):
    """根据分层评分获取壁纸ID列表
    
    核心逻辑：
    1. 根据标签的兴趣等级分配不同数量的壁纸
    2. 核心兴趣标签：每个取10张
    3. 主要兴趣标签：每个取5张
    4. 潜在兴趣标签：每个取2张
    
    Args:
        best_tags: 过滤后的高CTR标签列表
        platform: 平台类型 'PC' 或 'PHONE'
        limit: 最大返回数量
        
    Returns:
        list: 壁纸ID列表
    """
    try:
        recommended_ids = []
        seen_ids = set()
        
        for tag_info in best_tags:
            if len(recommended_ids) >= limit:
                break
            
            tag_level1 = tag_info.get('tag_level1')
            tag_level2 = tag_info.get('tag_level2')
            interest_level = tag_info.get('interest_level', 'potential')
            
            # 根据兴趣等级决定获取数量
            if interest_level == 'core':
                count = 10
            elif interest_level == 'main':
                count = 5
            else:
                count = 2
            
            # 获取该标签的壁纸
            tag_wallpaper_ids = _get_wallpapers_by_tag(
                tag_level1,
                tag_level2,
                platform,
                count,
                exclude_ids=seen_ids
            )
            
            for wid in tag_wallpaper_ids:
                if wid not in seen_ids:
                    recommended_ids.append(wid)
                    seen_ids.add(wid)
        
        return recommended_ids[:limit]
        
    except Exception as e:
        print(f"[Get Layer Score Wallpapers Failed] error: {e}")
        return []




