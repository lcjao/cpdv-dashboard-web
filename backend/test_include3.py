import sys
sys.path.insert(0, '.')

from fastapi import FastAPI
from routes import dashboard, algorithm

app = FastAPI(title="Test")

# Test 1: Include dashboard router directly
print("=== Test 1: include_router(dashboard.router) ===")
app.include_router(dashboard.router)
print(f"Routes after dashboard: {len(app.routes)}")
for r in app.routes:
    if hasattr(r, 'path'):
        print(f"  {getattr(r, 'methods', '')} {r.path}")

print()

# Test 2: Include algorithm router directly
print("=== Test 2: include_router(algorithm.router) ===")
app.include_router(algorithm.router)
print(f"Routes after algorithm: {len(app.routes)}")
for r in app.routes:
    if hasattr(r, 'path'):
        print(f"  {getattr(r, 'methods', '')} {r.path}")

# Test 3: Check if routes have path attribute
print("\n=== Checking route objects ===")
for r in app.routes:
    print(f"  type: {type(r).__name__}, path: {getattr(r, 'path', 'NO PATH')}, methods: {getattr(r, 'methods', '')}")