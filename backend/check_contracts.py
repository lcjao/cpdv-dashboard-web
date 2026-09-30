import json
from pathlib import Path
DATA_DIR = Path(r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend\public\algorithm-map")
print('DATA_DIR:', DATA_DIR)
print('Exists:', DATA_DIR.exists())
contracts_path = DATA_DIR / 'contracts.json'
print('contracts.json exists:', contracts_path.exists())
if contracts_path.exists():
    with open(contracts_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print('Keys:', list(data.keys())[:3])