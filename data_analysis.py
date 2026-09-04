# labeled_scenarios.json 
import json 
import matplotlib.pyplot as plt
from collections import Counter
import argparse
from common_vars import LABEL_BUTTON_TEXTS

def load_labeled_scenarios(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

if __name__ == "__main__":
    argv = argparse.ArgumentParser()
    argv.add_argument('-i', '--id', type=str, default='00', help='Data index to XX_labeled_scenarios.json')
    args = argv.parse_args()
    # file_path = f'./data/{args.id}_labeled_scenarios.json'
    file_path = f'/home/hcis-s19/Documents/ChengYu/HetroD-labeler/data/{args.id}_labeled_scenarios.json'

    idx_to_label = LABEL_BUTTON_TEXTS

    scenarios = load_labeled_scenarios(file_path)
    # print(scenarios.keys())

    label_counts = {k: 0 for k in idx_to_label.keys()}
    unique_ego = set()
    
    for key in scenarios.keys():
        ego_id = scenarios[key]['ego_id']
        actor_id = scenarios[key]['actor_id']
        min_frame = scenarios[key]['min_frame']
        max_frame = scenarios[key]['max_frame']
        label_idx = scenarios[key]['label_idx']

        if label_idx != 0:
            unique_ego.add((ego_id, label_idx))

        # ignore index 0 (None)

        # 確保 label_idx 在有效範圍內
            if label_idx < 88 :
                label_counts[label_idx] += 1
    
    print("Label 統計結果:")
    print("=" * 70)
    print(f"{'index':<3} | {'次數':<6} | {'百分比'} | {'標籤名稱':<25}")
    print("-" * 70)
    
    total_count = sum(label_counts.values())
    for i, count in label_counts.items():
        if count == 0:
            continue
        percentage = (count / total_count * 100) if total_count > 0 else 0
        print(f"{i:2d}   | {count:5d}     | {percentage:5.1f}% | {idx_to_label[i]:<25} ")
    
    print("-" * 70)
    print(f"{'總計':<2} | {total_count:5d}     | 100.0%")
    print("=" * 70)

    print(f"獨立 (Ego, Label_idx) 車輛數量: {len(unique_ego)}")




