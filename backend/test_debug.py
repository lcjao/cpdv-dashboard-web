import sys
sys.path.insert(0, '.')

# Debug the algorithm module
from routes import algorithm
print('algorithm module:', algorithm)
print('algorithm.router:', getattr(algorithm, 'router', 'NOT FOUND'))
print('algorithm.router type:', type(getattr(algorithm, 'router', None)))

# Check if router has routes
if hasattr(algorithm, 'router'):
    print('algorithm.router.routes:', algorithm.router.routes)

# Now test main
import main
app = main.app
print('App routes:')
for r in app.routes:
    if hasattr(r, 'path'):
        methods = getattr(r, 'methods', '')
        print(f'  {methods} {r.path}')