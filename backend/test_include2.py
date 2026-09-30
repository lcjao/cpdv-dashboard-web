import sys
sys.path.insert(0, '.')

from fastapi import FastAPI
from routes import algorithm, dashboard

app = FastAPI(title="Test")

print("Before include_router:")
for i, r in enumerate(app.routes):
    print(f"  [{i}] {getattr(r, 'path', 'NO PATH')} {getattr(r, 'methods', '')}")

app.include_router(dashboard.router, prefix="/api/dashboard")
print(f"\nAfter include_router(dashboard): {len(app.routes)} routes")
for i, r in enumerate(app.routes):
    print(f"  [{i}] {getattr(r, 'path', 'NO PATH')} {getattr(r, 'methods', '')}")

app.include_router(algorithm.router, prefix="/api/algorithm")
print(f"\nAfter include_router(algorithm): {len(app.routes)} routes")
for i, r in enumerate(app.routes):
    print(f"  [{i}] {getattr(r, 'path', 'NO PATH')} {getattr(r, 'methods', '')}")

# Check if routes have the right path
print("\n--- Checking algorithm routes specifically ---")
for r in app.routes:
    if hasattr(r, 'path') and 'algorithm' in r.path:
        print(f"  FOUND: {r.path} {getattr(r, 'methods', '')}")