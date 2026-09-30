import sys
sys.path.insert(0, '.')

# Test include_router manually
from fastapi import FastAPI
from routes import algorithm, dashboard

app = FastAPI(title="Test")

print("Before include_router:")
print(f"  app.routes: {len(app.routes)}")

app.include_router(dashboard.router, prefix="/api/dashboard")
print(f"After include_router(dashboard): {len(app.routes)}")

app.include_router(algorithm.router, prefix="/api/algorithm")
print(f"After include_router(algorithm): {len(app.routes)}")

print("All routes:")
for r in app.routes:
    if hasattr(r, 'path'):
        methods = getattr(r, 'methods', '')
        print(f'  {methods} {r.path}')