import sys
sys.path.insert(0, '.')

from routes import dashboard, algorithm

print("dashboard.router:")
print(f"  prefix: {getattr(dashboard.router, 'prefix', 'NOT SET')}")
print(f"  routes: {len(dashboard.router.routes)}")
for r in dashboard.router.routes:
    print(f"  path: {getattr(r, 'path', 'NO PATH')} methods: {getattr(r, 'methods', '')}")

print("\nalgorithm.router:")
print(f"  prefix: {getattr(algorithm.router, 'prefix', 'NOT SET')}")
print(f"  routes: {len(algorithm.router.routes)}")
for r in algorithm.router.routes:
    print(f"  path: {getattr(r, 'path', 'NO PATH')} methods: {getattr(r, 'methods', '')}")