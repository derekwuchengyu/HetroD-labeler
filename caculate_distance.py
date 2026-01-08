import json 
import cv2 
import pandas as pd
import numpy as np
from tqdm import tqdm
import multiprocessing
import os


# load the track dict 
with open('./data/track_frame_dict.json', 'r', encoding='utf-8') as f:
    track_dict = json.load(f)

ortho_px_to_meter = 0.0499967249445942

# load the trackid_objects.json
with open('./data/trackid_objects.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
ego_id_list = list(data.keys())


def calc_min_distance(args):
    ego_id, track_dict, data, ortho_px_to_meter = args
    result = {}
    ego_id_frame_list = list(track_dict[str(ego_id)].keys())
    other_actor_id_list = data[ego_id]

    for other_id in other_actor_id_list:
        other_actor_id_frame_list = list(track_dict[str(other_id)].keys())

        ego_traj = np.array([
            (track_dict[str(ego_id)][frame][0]['xCenter'] / ortho_px_to_meter,
             -track_dict[str(ego_id)][frame][0]['yCenter'] / ortho_px_to_meter)
            for frame in ego_id_frame_list
        ])
        other_traj = np.array([
            (track_dict[str(other_id)][frame][0]['xCenter'] / ortho_px_to_meter,
             -track_dict[str(other_id)][frame][0]['yCenter'] / ortho_px_to_meter)
            for frame in other_actor_id_frame_list
        ])

        if ego_traj.size > 0 and other_traj.size > 0:
            dist_matrix = np.linalg.norm(ego_traj[:, None, :] - other_traj[None, :, :], axis=2)
            min_distance = np.min(dist_matrix)
            result[f"{ego_id}_{other_id}"] = min_distance
    return result

if __name__ == "__main__":
    # 建立暫存資料夾
    os.makedirs('./data/tmp_distance_jsons', exist_ok=True)

    args_list = [(ego_id, track_dict, data, ortho_px_to_meter) for ego_id in ego_id_list]

    # 分別儲存每個 ego_id 的結果
    with multiprocessing.Pool(processes=64) as pool:
        for res, ego_id in zip(
            tqdm(pool.imap_unordered(calc_min_distance, args_list), total=len(args_list), desc="計算最短距離"),
            ego_id_list
        ):
            file_path = f'./data/tmp_distance_jsons/min_distance_{ego_id}.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False, indent=2)

    # 合併所有結果
    distance_result = {}
    for ego_id in ego_id_list:
        file_path = f'./data/tmp_distance_jsons/min_distance_{ego_id}.json'
        with open(file_path, 'r', encoding='utf-8') as f:
            res = json.load(f)
            distance_result.update(res)

    with open('./data/min_distance_result.json', 'w', encoding='utf-8') as f:
        json.dump(distance_result, f, ensure_ascii=False, indent=2)
    print("最接近距離結果已儲存至 ./data/min_distance_result.json")








