import cv2
import matplotlib.pyplot as plt

img_path = './data/00_background_semantic.png'
img = cv2.imread(img_path)
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

area_dict = {}

def onclick(event):
    if event.xdata is not None and event.ydata is not None:
        x, y = int(event.xdata), int(event.ydata)
        color = img_rgb[y, x].tolist()
        print(f"座標: ({x}, {y}), 顏色: {color}")
        area_class = input("請輸入此區域的 class：")
        area_dict[str(color)] = area_class
        print(f"已標註：{color} -> {area_class}")

fig, ax = plt.subplots()
ax.imshow(img_rgb)
cid = fig.canvas.mpl_connect('button_press_event', onclick)
plt.title('點選色塊並輸入區域 class')
plt.show()

# 標註結束後存檔
import json
with open('./data/area_color_class.json', 'w', encoding='utf-8') as f:
    json.dump(area_dict, f, ensure_ascii=False, indent=2)
print("標註結果已儲存至 ./data/area_color_class.json")