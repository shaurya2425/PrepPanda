import json
from pathlib import Path

path = Path(__file__).resolve().parent / 'results_improved.json'
with path.open('r', encoding='utf-8') as f:
    data = json.load(f)
best = data['best']
print('best config', best['config'])
print('aggregate p@5', best['p_at_5'], 'ndcg', best['ndcg_at_10'])
for idx, detail in enumerate(best['details'], 1):
    if detail['p_at_5'] > 0 or detail['ndcg_at_10'] > 0:
        print('question', idx, detail)
