import requests

# Test command-meta endpoint
r = requests.get('http://127.0.0.1:8000/api/command-meta')
result = r.json()
print('Version:', result.get('version'))
print('Commands count:', len(result.get('commands', [])))
for cmd in result.get('commands', []):
    action = cmd['action']
    name = cmd['name']
    quick = cmd['quick']
    llm_tool = cmd['llm_tool']
    print(f'  - {action}: {name} (quick={quick}, llm_tool={llm_tool})')

# Test overview command
r = requests.post('http://127.0.0.1:8000/api/command', json={'text': '看板总览'})
result = r.json()
print('\nOverview action:', result.get('action'))
print('Bridge ID:', result.get('bridge_id'))

# Test CPDV command
r = requests.post('http://127.0.0.1:8000/api/command', json={'text': '计算CPDV bridge_01 depth=0.2 distances=5,10,15,20,25'})
result = r.json()
print('\nCPDV action:', result.get('action'))
print('Status:', result.get('status'))
print('Bridge ID:', result.get('bridge_id'))
print('Need refresh:', result.get('need_refresh'))
if 'cpdv' in result:
    print('CPDV len:', len(result.get('cpdv', [])))

# Test list command
r = requests.post('http://127.0.0.1:8000/api/command', json={'text': '列出桥梁'})
result = r.json()
print('\nList action:', result.get('action'))
bridges = result.get('bridges', [])
print('Bridges count:', len(bridges))
for b in bridges:
    print(f'  - {b["id"]}: {b["name"]}')

# Test predict command (should return unavailable)
r = requests.post('http://127.0.0.1:8000/api/command', json={'text': '预测损伤'})
result = r.json()
print('\nPredict action:', result.get('action'))
print('Status:', result.get('status'))
print('Error:', result.get('error', 'N/A'))
print('Hint:', result.get('hint', 'N/A'))

# Test multi_crack command
r = requests.post('http://127.0.0.1:8000/api/command', json={'text': '多裂缝预测'})
result = r.json()
print('\nMulti_crack action:', result.get('action'))
print('Status:', result.get('status'))
print('Bridge ID:', result.get('bridge_id'))

# Test random_condition command
r = requests.post('http://127.0.0.1:8000/api/command', json={'text': '随机工况分析'})
result = r.json()
print('\nRandom_condition action:', result.get('action'))
print('Status:', result.get('status'))

# Test compare command (should need two bridges)
r = requests.post('http://127.0.0.1:8000/api/command', json={'text': '对比'})
result = r.json()
print('\nCompare action:', result.get('action'))
print('Status:', result.get('status'))
print('Hint:', result.get('hint', 'N/A'))