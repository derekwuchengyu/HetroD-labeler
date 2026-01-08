import json 
import cv2 
import pandas as pd
import numpy as np 


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

keys = list(data.keys())
print(f"前 5 個 key: {keys[:5]}")
# 前 5 個 key: ['0', '2', '4', '6', '8']


# take the first key, then draw a video 

ego_id  = '6'
other_actor_id = data[ego_id]
# number of other actor 
print(f"ego_id {ego_id} 對應的其他 actor 數量: {len(other_actor_id)}")


# load the background image 
background = cv2.imread('./data/00_background.png')


# load the track dict 
with open('./data/track_frame_dict.json', 'r', encoding='utf-8') as f:
    track_dict = json.load(f)

print(f"track_dict 載入完成，總共有 {len(track_dict)} 個 trackId")

print(track_dict['0'].keys())

# draw the all frame 

img = background.copy()



for frame in sorted(track_dict[ego_id].keys(), key=int):
    row = track_dict[ego_id][frame][0]
    
    x = row['xCenter'] / ortho_px_to_meter
    y = -row['yCenter'] / ortho_px_to_meter
    heading = row['heading']
    width = row['width'] / ortho_px_to_meter
    length = row['length'] / ortho_px_to_meter
    draw_rotated_bbox(img, x, y, width, length, heading)
    
    # draw other actors
    for other_id in other_actor_id:
        # print(other_id)
        # print(track_dict[str(other_id)].keys())
        if frame in track_dict[str(other_id)].keys():
            other_row = track_dict[str(other_id)][frame][0]
            ox = other_row['xCenter'] / ortho_px_to_meter
            oy = -other_row['yCenter'] / ortho_px_to_meter
            oheading = other_row['heading']
            owidth = other_row['width'] / ortho_px_to_meter
            olength = other_row['length'] / ortho_px_to_meter
            draw_rotated_bbox(img, ox, oy, owidth, olength, oheading, color=(255,0,0))
    
    
    cv2.imshow('bbox', img)
    cv2.waitKey(50)  # 每張顯示 50ms

cv2.destroyAllWindows()


# row = track_dict['0']['0'][0]

# # get bounding box in pixel coordinate 

# x = row['xCenter'] / ortho_px_to_meter
# y = -row['yCenter'] / ortho_px_to_meter  # Y is negated for image coordinates
# heading = row['heading']  # Keep heading as-is (in degrees)
# width = row['width'] / ortho_px_to_meter
# length = row['length'] / ortho_px_to_meter



# # 複製背景避免直接修改原圖
# img = background.copy()
# draw_rotated_bbox(img, x, y, width, length, heading)



# cv2.imshow('bbox', img)
# cv2.waitKey(0)
# cv2.destroyAllWindows()



