import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WallPaper.settings.pro")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
django.setup()

from App.view.tasks.sync_wallpaper_counts import sync_wallpaper_all_counts

if __name__ == '__main__':
    print("="*50)
    print("开始执行壁纸计数同步任务（评论/点赞/收藏）...")
    print("="*50)
    try:
        sync_wallpaper_all_counts()
        print("\n" + "="*50)
        print("计数同步执行完成！")
        print("="*50)
    except Exception as e:
        print(f"\n任务执行失败: {e}")
        import traceback
        traceback.print_exc()