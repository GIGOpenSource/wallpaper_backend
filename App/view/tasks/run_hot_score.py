# App/view/tasks/run_hot_score.py
import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "WallPaper.settings.pro")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
django.setup()

from App.view.tasks.hot_score_update import update_hot_score_daily

if __name__ == '__main__':
    print("="*50)
    print("开始执行壁纸热门评分更新任务...")
    print("="*50)
    try:
        update_hot_score_daily()
        print("\n" + "="*50)
        print("任务执行完成！")
        print("="*50)
    except Exception as e:
        print(f"\n任务执行失败: {e}")
        import traceback
        traceback.print_exc()
