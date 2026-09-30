import sys
sys.path.insert(0, '..')
from backend.main import app
print('App routes:')
for route in app.routes:
    if hasattr(route, 'path') and 'algorithm' in route.path:
        methods = getattr(route, 'methods', '')
        print(f'{methods} {route.path}')