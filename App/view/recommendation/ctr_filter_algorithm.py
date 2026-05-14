"""
CTR-based Tag Filtering Recommendation Algorithm
Filters and ranks wallpapers based on click-through rate data
"""
from django.db.models import F
from models.models import WallpaperTagCTR, Wallpapers


def increment_tag_impressions(wallpaper_ids):
    """
    批量增加壁纸标签的曝光次数
    
    Args:
        wallpaper_ids: 壁纸ID列表
    """
    if not wallpaper_ids:
        return
    
    # 获取这些壁纸关联的所有标签ID（去重）
    tag_ids = set()
    wallpapers = Wallpapers.objects.filter(id__in=wallpaper_ids).prefetch_related('tags')
    
    for wallpaper in wallpapers:
        for tag in wallpaper.tags.all():
            tag_ids.add(tag.id)
    
    if not tag_ids:
        return
    
    # 批量增加曝光次数
    # 使用 get_or_create 确保记录存在，然后更新
    for tag_id in tag_ids:
        ctr_obj, created = WallpaperTagCTR.objects.get_or_create(tag_id=tag_id)
        if created:
            ctr_obj.impression_count = 1
            ctr_obj.save()
        else:
            WallpaperTagCTR.objects.filter(tag_id=tag_id).update(
                impression_count=F('impression_count') + 1
            )


def increment_tag_clicks(wallpaper_id):
    """
    增加壁纸标签的点击次数
    
    Args:
        wallpaper_id: 壁纸ID
    """
    if not wallpaper_id:
        return
    
    # 获取该壁纸关联的所有标签ID
    try:
        wallpaper = Wallpapers.objects.prefetch_related('tags').get(id=wallpaper_id)
        tag_ids = [tag.id for tag in wallpaper.tags.all()]
        
        if not tag_ids:
            return
        
        # 批量增加点击次数
        for tag_id in tag_ids:
            ctr_obj, created = WallpaperTagCTR.objects.get_or_create(tag_id=tag_id)
            if created:
                ctr_obj.click_count = 1
                ctr_obj.save()
            else:
                WallpaperTagCTR.objects.filter(tag_id=tag_id).update(
                    click_count=F('click_count') + 1
                )
    except Wallpapers.DoesNotExist:
        return


def get_ctr_filtered_wallpaper_ids(unique_id, platform, limit=20):
    """
    CTR-based tag filtering recommendation
    
    TODO: Implement CTR-based filtering logic
    - Analyze historical click data
    - Filter tags with low CTR
    - Rank wallpapers by predicted CTR
    
    Args:
        unique_id: User unique identifier
        platform: Platform type 'PC' or 'PHONE'
        limit: Number of wallpapers to return
        
    Returns:
        list: Wallpaper ID list
    """
    # TODO: Implement CTR filtering logic
    print("[CTR Filter] Not implemented yet")
    return []
