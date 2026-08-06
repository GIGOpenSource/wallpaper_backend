import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WallPaper.settings.pro')
django.setup()

from models.models import PageSpeed
from App.view.seo.page_speed.tools import get_site_prefix

prefix = get_site_prefix().rstrip('/')
print('site_prefix:', prefix)

updated = 0
same = 0
for obj in PageSpeed.objects.all().iterator():
    path = obj.page_path or ''
    if not path.startswith('/'):
        path = '/' + path
    new_url = f'{prefix}{path}'
    if obj.full_url != new_url:
        obj.full_url = new_url
        obj.save(update_fields=['full_url'])
        updated += 1
    else:
        same += 1

print(f'done: updated={updated}, unchanged={same}, total={updated + same}')
for o in PageSpeed.objects.all()[:5]:
    print(o.id, o.page_path, '->', o.full_url)
