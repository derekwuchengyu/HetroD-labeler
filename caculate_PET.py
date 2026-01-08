import json 
import cv2 
import pandas as pd
import numpy as np 


lane_adjacent = {
    "lane_A": ["lane_B", "lane_C", "walker_area"],
    "lane_B": ["lane_A", "lane_C", "walker_area"],
    "lane_C": ["lane_A", "lane_B", "walker_area"],
    "lane_D": ["lane_E", "walker_area"],
    "lane_E": ["lane_D", "walker_area"],
    "lane_F": ["lane_G", "walker_area"],
    "lane_G": ["lane_F", "walker_area"],
    "lane_H": ["lane_I", "walker_area"],
    "lane_I": ["lane_H", "walker_area"],
    "walker_area": ["lane_A", "lane_B", "lane_C", "lane_D", "lane_E", "lane_F", "lane_G", "lane_H", "lane_I", "interscetion_area"],
    "interscetion_area": ["lane_A", "lane_B", "lane_C", "lane_D", "lane_E", "lane_F", "lane_G", "lane_H", "lane_I", "walker_area"]
}


# load the background image 
background = cv2.imread('./data/00_background.png')


# load the semantic background image
semantic_background = cv2.imread('./data/00_background_semantic.png')

# load the semantic color to class dict
with open('./data/area_color_class.json', 'r', encoding='utf-8') as f:
    color_class_dict = json.load(f)



# load the track dict 
with open('./data/track_frame_dict.json', 'r', encoding='utf-8') as f:
    track_dict = json.load(f)


def draw_rotated_bbox(img, x, y, width, length, heading, color=(0,255,0), thickness=2):
    # 建立 bbox 四個角的座標（以中心為原點）
    box = np.array([
        [-length/2, -width/2],
        [-length/2,  width/2],
        [ length/2,  width/2],
        [ length/2, -width/2]
    ])
    # 旋轉
    theta = np.deg2rad(-heading)
    rot = np.array([
        [np.cos(theta), -np.sin(theta)],
        [np.sin(theta),  np.cos(theta)]
    ])
    box = box @ rot.T
    # 平移到 (x, y)
    box += np.array([x, y])
    # 轉成 int
    box = box.astype(int)
    # 畫多邊形
    cv2.polylines(img, [box], isClosed=True, color=color, thickness=thickness)
ortho_px_to_meter = 0.0499967249445942

# load the trackid_objects.json
with open('./data/trackid_objects.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
ego_id_list = list(data.keys())


pet_result = {}


# counter = 0

for ego_id in ego_id_list:

    ego_id_frame_list = list(track_dict[str(ego_id)].keys())

    other_actor_id_list = data[ego_id]

    # for other_id in other_actor_id_list:
        # counter+=1

    
    for other_id in other_actor_id_list:

        other_actor_id_frame_list = list(track_dict[str(other_id)].keys())

        # get overlay frame list 

        overlay_frame_list = sorted(
            set(ego_id_frame_list) & set(other_actor_id_frame_list),
            key=lambda x: int(x)
        )

        # 取得 ego 每個 frame 的區域
        ego_area_seq = []
        for frame in overlay_frame_list:
            row = track_dict[str(ego_id)][frame][0]
            x = row['xCenter'] / ortho_px_to_meter
            y = -row['yCenter'] / ortho_px_to_meter
            color = semantic_background[int(y), int(x)].tolist()
            area_type = color_class_dict.get(str(color), 'unknown')
            ego_area_seq.append(area_type)

        # 取得 other actor 每個 frame 的區域
        other_area_seq = []
        for frame in overlay_frame_list:
            row = track_dict[str(other_id)][frame][0]
            x = row['xCenter'] / ortho_px_to_meter
            y = -row['yCenter'] / ortho_px_to_meter
            color = semantic_background[int(y), int(x)].tolist()
            area_type = color_class_dict.get(str(color), 'unknown')
            other_area_seq.append(area_type)

        # 計算 PET
        ego_exit_idx = None
        for idx, area in enumerate(ego_area_seq):
            # ego 最後一次在區域內（非 unknown）
            if area != 'unknown':
                ego_exit_idx = idx

        other_entry_idx = None
        if ego_exit_idx is not None:
            ego_last_area = ego_area_seq[ego_exit_idx]
            for idx in range(ego_exit_idx + 1, len(other_area_seq)):
                area = other_area_seq[idx]
                # 只要 other actor 進入任何非 unknown 區域就算 PET
                if area != 'unknown':
                    other_entry_idx = idx
                    break

        if ego_exit_idx is not None and other_entry_idx is not None:
            pet_frame = other_entry_idx - ego_exit_idx
            pet_result[f"{ego_id}_{other_id}"] = pet_frame
            print(f"ego_id: {ego_id}, other_id: {other_id}, PET: {pet_frame} frames")

# 可選：存成 json
with open('./data/pet_result.json', 'w', encoding='utf-8') as f:
    json.dump(pet_result, f, ensure_ascii=False, indent=2)
print("PET 結果已儲存至 ./data/pet_result.json")








