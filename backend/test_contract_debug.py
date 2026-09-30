import sys
sys.path.insert(0, '.')

from backend.routes.algorithm import _load_json
import json

# Simulate the contract endpoint logic
protocol = "backend_framework.protocols.data_loader.DataLoaderProtocol"
contracts = _load_json("contracts.json")

print(f"Protocol requested: '{protocol}'")
print(f"Protocol in contracts: {protocol in contracts}")
print(f"Available keys: {list(_load_json('contracts.json').keys())[:3]}")

if protocol in _load_json("contracts.json"):
    print("FOUND!")
else:
    print("NOT FOUND!")
    # Check for similar keys
    contracts = _load_json("contracts.json")
    for k in contracts.keys():
        if "data_loader" in k.lower():
            print(f"  Similar: {k}")