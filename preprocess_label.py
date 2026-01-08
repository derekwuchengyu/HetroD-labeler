
import pandas as pd
import json


# 算出有幾組pair 
# 先找出有幾個ego id 


# numVehicles 
# numVRUs



# 00_tracksMeta --> contain all tracks 


# file_path = './data/00_tracksMeta.csv'


# df = pd.read_csv(file_path)


# result = {}


# classes = df['class'].unique().tolist()
# print(f"所有 class 類型：{classes}")

# ['car', 'motorcycle', 'truck', 'pedestrian', 'bicycle']

# for idx, row in df.iterrows():
#     track_id_class = row['class']
#     track_id = row['trackId']
#     start = row['initialFrame']
#     end = row['finalFrame']
    
#     if not(track_id_class == 'car' or track_id_class == 'truck'):
#         continue

#     # 找出在這個 frame 範圍內出現的所有 trackId（包含自己）
#     mask = (df['initialFrame'] <= end) & (df['finalFrame'] >= start)
#     objects = df[mask]['trackId'].unique().tolist()

#     # remove 自己
#     if track_id in objects:
#         objects.remove(track_id)
#     result[track_id] = objects

# print(f"car 與 truck 類別的 trackId 數量: {len(result)}")
# # 1117 

# total_ids = sum(len(ids) for ids in result.values())
# print(f"所有 key 對應的 ids 總數: {total_ids}")

# # 所有 key 對應的 ids 總數: 135265


# with open('./data/trackid_objects.json', 'w', encoding='utf-8') as f:
#     json.dump(result, f, ensure_ascii=False, indent=2)
# print("result 已儲存至 ./data/trackid_objects.json")



# 

# track_file = './data/00_tracks.csv'
# track_csv = pd.read_csv(track_file)

# 建立 trackId 為 key 的 dict
# track_dict = {}
# for idx, row in track_csv.iterrows():
#     tid = int(row['trackId'])
    
#     # print(tid)
#     if tid not in track_dict:
#         track_dict[tid] = []
#     track_dict[tid].append(row.to_dict())
#     # break


# # 存成 JSON 檔案
# with open('./data/track_dict.json', 'w', encoding='utf-8') as f:
#     json.dump(track_dict, f, ensure_ascii=False, indent=2)
# print("track_dict 已儲存至 ./data/track_dict.json")


# track_frame_dict = {}
# for idx, row in track_csv.iterrows():
#     tid = int(row['trackId'])
#     frame = int(row['frame'])
#     if tid not in track_frame_dict:
#         track_frame_dict[tid] = {}
#     if frame not in track_frame_dict[tid]:
#         track_frame_dict[tid][frame] = []
#     track_frame_dict[tid][frame].append(row.to_dict())

# # 存成 JSON 檔案
# with open('./data/track_frame_dict.json', 'w', encoding='utf-8') as f:
#     json.dump(track_frame_dict, f, ensure_ascii=False, indent=2)
# print("track_frame_dict 已儲存至 ./data/track_frame_dict.json")



# 
file_path = './data/00_tracksMeta.csv'
df = pd.read_csv(file_path)

# 保存 trackId 與 class 的對應關係
trackid_class = {}
for idx, row in df.iterrows():
    track_id = row['trackId']
    track_class = row['class']
    trackid_class[track_id] = track_class

# save 
with open('./data/trackid_class.json', 'w', encoding='utf-8') as f:
    json.dump(trackid_class, f, ensure_ascii=False, indent=2)
print("trackid_class 已儲存至 ./data/trackid_class.json")