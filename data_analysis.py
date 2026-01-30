# labeled_scenarios.json 
import json 
import matplotlib.pyplot as plt
from collections import Counter
import argparse

def load_labeled_scenarios(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

if __name__ == "__main__":
    argv = argparse.ArgumentParser()
    argv.add_argument('-i', '--id', type=str, default='00', help='Data index to XX_labeled_scenarios.json')
    args = argv.parse_args()
    file_path = f'./data/{args.id}_labeled_scenarios.json'

    idx_to_label = {
        0: "None",
        1: "直行 + 左轉",
        2: "左轉 + 直行",
        3: "並行 機車加速通過",
        4: "並行 機車等速通過",
        5: "並行 機車減速",
        6: "繞過前方車輛",
        7: "被 右側 cut-in",
        8: "被 左側 cut-in",
        9: "右轉 + 機車直行與待轉",
        10: "左轉 + 機車待轉",
        11: "右轉 + 行人通過",
        12: "左轉 + 行人通過",
        13: "cut-out + 右側直行",
        14: "cut-out + 左側直行",
        15: "左轉 + 左側機車通過",
        88: "不確定",
    }

    scenarios = load_labeled_scenarios(file_path)
    # print(scenarios.keys())

    label_counts = {k: 0 for k in idx_to_label.keys()}
    
    for key in scenarios.keys():
        ego_id = scenarios[key]['ego_id']
        actor_id = scenarios[key]['actor_id']
        min_frame = scenarios[key]['min_frame']
        max_frame = scenarios[key]['max_frame']
        label_idx = scenarios[key]['label_idx']

        # ignore index 0 (None)

        # 確保 label_idx 在有效範圍內
        if (1 <= label_idx <= 15) or label_idx == 88 or label_idx == 99:
            label_counts[label_idx] += 1
    
    print("Label 統計結果:")
    print("=" * 70)
    print(f"{'index':<3} | {'次數':<6} | {'百分比'} | {'標籤名稱':<25}")
    print("-" * 70)
    
    total_count = sum(label_counts.values())
    for i, count in label_counts.items():
        percentage = (count / total_count * 100) if total_count > 0 else 0
        print(f"{i:2d}   | {count:5d}     | {percentage:5.1f}% | {idx_to_label[i]:<25} ")
    
    print("-" * 70)
    print(f"{'總計':<2} | {total_count:5d}     | 100.0%")
    print("=" * 70)



