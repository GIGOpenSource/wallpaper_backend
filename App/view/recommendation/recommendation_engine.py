"""
Recommendation Engine - Unified Entry Point
Combines multiple recommendation algorithms to generate final wallpaper recommendations
"""
from App.view.recommendation.user_interest_algorithm import (
    get_user_top_tags,
    get_cold_start_wallpaper_ids,
    get_tag_based_wallpaper_ids
)
from App.view.recommendation.ctr_filter_algorithm import get_ctr_filtered_wallpaper_ids
from App.view.recommendation.layered_weight_algorithm import get_layered_weighted_wallpaper_ids


def get_recommended_wallpaper_ids(unique_id, platform='all', limit=20):
    """
    Core recommendation function called by _list_for_customer
    
    Combines multiple recommendation algorithms:
    1. User Interest Tag Algorithm (implemented)
    2. CTR Filter Algorithm (reserved)
    3. Layered Weight Sorting Algorithm (reserved)
    
    Args:
        unique_id: User unique identifier
        platform: Platform type 'PC', 'PHONE', or 'all'
        limit: Number of wallpapers to return
        
    Returns:
        list: Wallpaper ID list
    """
    # Check if user has tags (cold start vs personalized)
    top_tags = get_user_top_tags(unique_id)
    
    if not top_tags:
        # Cold start: use strategy-based recommendations
        return get_cold_start_wallpaper_ids(platform, limit)
    
    # Personalized recommendations
    # Currently using tag-based algorithm
    personalized_ids = get_tag_based_wallpaper_ids(unique_id, platform, limit)
    
    # TODO: Add more algorithms and combine results
    # Example future implementation:
    # ctr_ids = get_ctr_filtered_wallpaper_ids(unique_id, platform, limit)
    # weighted_ids = get_layered_weighted_wallpaper_ids(unique_id, platform, limit)
    
    # Combine results from different algorithms
    # For now, just return tag-based recommendations
    return personalized_ids
