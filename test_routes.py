import sys
sys.path.insert(0, '.')
from backend.main import app
print('App loaded successfully')
for route in app.routes:
    if hasattr(route, 'path'):
        methods = getattr(route, 'methods', '')
        print(f'{methods} {route.path}')