import sys
sys.path.insert(0, '.')
from routes import algorithm, dashboard, analysis, bridges, llm, command, external_code
print('All routes modules imported')

import main
print('Main module loaded')
app = main.app
print('App routes count:', len(app.routes))
for r in app.routes:
    if hasattr(r, 'path') and 'algorithm' in r.path:
        methods = getattr(r, 'methods', '')
        print(f'{methods} {r.path}')