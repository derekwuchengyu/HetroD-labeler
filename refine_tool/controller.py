from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QMainWindow, QProgressBar
from PyQt6.QtGui import QIcon, QFont
import pandas as pd
import orjson
import os
from time import time
from video_controller import video_controller
from datetime import datetime



class MainWindow_controller(QMainWindow):
    def __init__(self, ui_class):
        super().__init__() 
        self.ui = ui_class()  # 使用傳入的 UI 類別
        self.ui.setupUi(self)

        # 設定要篩選的 label_idx 值
        LABEL_IDX = 2

        # 根據 UI 模組決定 ToolTip 字體大小
        
        if "ui_ipad_mini" in ui_class.__module__.lower():
            self.setStyleSheet("QToolTip { font-size: 12pt; }")
        else:
            self.setStyleSheet("QToolTip { font-size: 24pt; }")


        self.data_path = "../data"

        start_time = time()
        # load trackid to class 
        with open(f'{self.data_path}/trackid_class.json', 'r', encoding='utf-8') as f:
            self.trackid_class = orjson.loads(f.read())
        print(f"load trackid_class.json time: {time() - start_time:.2f} sec")

        # with open(f'{self.data_path}/pet_distance_dict.json', 'r', encoding='utf-8') as f:
        #     self.pet_min_distance_dict = orjson.loads(f.read())
        self.pet_results_df = pd.read_parquet('../data/pet_results_optimized.parquet')
        
        print(f"load pet_distance_dict.parquet time: {time() - start_time:.2f} sec")


        # 建立 lookup table（O(1) 查詢）
        self.pet_lookup = {}
        for row in self.pet_results_df.itertuples(index=False):
            a1 = str(row.agent1_id)
            a2 = str(row.agent2_id)
            value = (row.min_distance, row.pet)

            self.pet_lookup[(a1, a2)] = value
            self.pet_lookup[(a2, a1)] = value

        print(f"load pet_lookup time: {time() - start_time:.2f} sec")

        # load labeled scenarios 
        save_path = os.path.join(self.data_path, "labeled_scenarios.json")
        print(f"load labeled_scenarios.json time: {time() - start_time:.2f} sec")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                labeled_dict = orjson.loads(f.read())
        else:
            return
        
        keys = list(labeled_dict.keys())

        self.ui.comboBox_ego_id.clear()

        """
        for id in keys:
            # if "label_idx": 5
            if labeled_dict[id].get("label_idx", None) == 0:
                continue
            self.ui.comboBox_ego_id.addItem(id)
        """

        for id in keys:
            if labeled_dict[id].get("label_idx", None) == LABEL_IDX:
                self.ui.comboBox_ego_id.addItem(id)


        self.current_id_pair = self.ui.comboBox_ego_id.currentText()

        self.video_controller = video_controller(data_path=self.data_path, ui=self.ui)
        self.label_tooltip_on = False  # 預設關閉

        self.ui.comboBox_ego_id.currentIndexChanged.connect(self.update_combobox_label_info)
        
        self.ui.pushButton_next_actor.clicked.connect(self.next_actor)
        self.ui.pushButton_prev_actor.clicked.connect(self.prev_actor)

        self.ui.pushButton_label_notice_on.setText("開啟label 提示")
        self.ui.pushButton_label_notice_on.clicked.connect(self.toggle_label_tooltips)

        # 設定 label 按鈕點擊事件
        for i in range(0, 14):
            btn = getattr(self.ui, f"pushButton_label_{i}")
            btn.clicked.connect(lambda checked, idx=i: self.set_label_button_selected(idx))
        
        # 加入 label=99 按鈕（多種scenario）
        self.ui.pushButton_label_99.clicked.connect(lambda checked: self.set_label_button_selected(99))
        self.ui.pushButton_special_scenario.clicked.connect(self.mark_special_scenario)

        self.selected_label_btn_idx = None  # 記錄目前選中的 label 按鈕

        self.ui.pushButton_check_label_done.clicked.connect(self.save_current_checked)

        self.update_combobox_label_info()

    def toggle_label_tooltips(self):
        self.label_tooltip_on = not self.label_tooltip_on
        self.set_label_tooltips(enable=self.label_tooltip_on)
        if self.label_tooltip_on:
            self.ui.pushButton_label_notice_on.setText("關閉label 提示")
        else:
            self.ui.pushButton_label_notice_on.setText("開啟label 提示")

    def set_label_tooltips(self, enable=True):
        self.ui.pushButton_label_1.setToolTip("ego 路口直行，遇到對向左轉 \n{Car, Truck, Motor/Bike}" if enable else "")
        self.ui.pushButton_label_2.setToolTip("ego 路口左轉，遇到對向直行 \n{Car, Truck, Motor/Bike}" if enable else "")
        self.ui.pushButton_label_3.setToolTip("ego 與機踏車並行，機踏車加速通過" if enable else "")
        self.ui.pushButton_label_4.setToolTip("ego 與機踏車並行，機踏車等速並行" if enable else "")
        self.ui.pushButton_label_5.setToolTip("ego 與機踏車並行，機踏車減速" if enable else "")
        self.ui.pushButton_label_6.setToolTip("ego 前方同車道有停止車（等左轉/臨停）\n，ego 通過前未移動即算，需換道 (含佔用一點車道情況)，例：338,913,1096,1997" if enable else "")
        self.ui.pushButton_label_7.setToolTip("前方 {Car, Truck, Motor/Bike} 從右側 cut-in" if enable else "")
        self.ui.pushButton_label_8.setToolTip("前方 {Car, Truck, Motor/Bike} 從左側 cut-in" if enable else "")
        self.ui.pushButton_label_9.setToolTip("ego 右轉，右側機踏車直行通過（含待轉區）" if enable else "")
        self.ui.pushButton_label_10.setToolTip("ego 左轉，對向機踏車準備待轉" if enable else "")
        self.ui.pushButton_label_11.setToolTip("ego 右轉後遇見行人通過" if enable else "")
        self.ui.pushButton_label_12.setToolTip("ego 左轉後遇見行人通過" if enable else "")
        
    def update_combobox_label_info(self):
        # label_combobox_ego_id
        # x / x 
        total = self.ui.comboBox_ego_id.count()
        current_index = self.ui.comboBox_ego_id.currentIndex() + 1  # 1-based
        self.ui.label_combobox_ego_id.setText(f"{current_index} / {total}")

        self.video_controller.update_video_info()

        current_id_pair = self.ui.comboBox_ego_id.currentText()

        ego_id = current_id_pair.split("_")[0]
        other_actor_id = current_id_pair.split("_")[1]

        ##
        checked_list = []
        path = os.path.join(self.data_path, "label_check.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                checked_list = f.read().splitlines()
        if current_id_pair in checked_list:
            self.ui.pushButton_check_label_done.setStyleSheet("color: red;")
        else:
            self.ui.pushButton_check_label_done.setStyleSheet("color: black;")

        # 讀取已標註 scenario
        save_path = os.path.join(self.data_path, "labeled_scenarios.json")
        selected_label_idx = None
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                try:
                    labeled_dict = orjson.loads(f.read())
                    if current_id_pair in labeled_dict:
                        selected_label_idx = labeled_dict[current_id_pair].get("label_idx", None)
                except Exception:
                    pass

        self.selected_label_idx = selected_label_idx

        # 讀取 label 99 標記
        complex_path = os.path.join(self.data_path, "complex_scenarios.json")
        self.selected_label_idx_99 = False
        if os.path.exists(complex_path):
            with open(complex_path, "r", encoding="utf-8") as f:
                try:
                    complex_dict = orjson.loads(f.read())
                    if current_id_pair in complex_dict:
                        self.selected_label_idx_99 = True
                except Exception:
                    pass

        # 讀取特別scenario標記
        special_path = os.path.join(self.data_path, "special_scenarios.json")
        self.selected_special_scenario = False
        if os.path.exists(special_path):
            with open(special_path, "r", encoding="utf-8") as f:
                try:
                    special_dict = orjson.loads(f.read())
                    if current_id_pair in special_dict:
                        self.selected_special_scenario = True
                except Exception:
                    pass

        # 設定按鈕顏色
        car_truck_labels = [0, 1, 2, 6, 7, 8, 13]
        motor_bike_labels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13]
        ped_labels = [0, 11, 12, 13]
        cls = self.trackid_class.get(str(other_actor_id), "unknown").lower()
        blue_labels = set()
        if cls in ["car", "truck"]:
            blue_labels = set(car_truck_labels)
        elif cls in ["motorcycle", "bicycle"]:
            blue_labels = set(motor_bike_labels)
        elif cls == "pedestrian":
            blue_labels = set(ped_labels)

        for i in range(0, 14):
            btn = getattr(self.ui, f"pushButton_label_{i}")
            if self.selected_label_idx is not None and i == self.selected_label_idx:
                btn.setStyleSheet("color: red;")
            elif i in blue_labels:
                btn.setStyleSheet("color: gray;")
            else:
                btn.setStyleSheet("color: white;")

        # 設定 label_99 和 special_scenario 按鈕顏色
        self.ui.pushButton_label_99.setStyleSheet("color: red;" if self.selected_label_idx_99 else "color: black;")
        self.ui.pushButton_special_scenario.setStyleSheet("color: red;" if self.selected_special_scenario else "color: black;")

        ## 
        # 取得 other actor class
        other_actor_class = self.trackid_class.get(str(other_actor_id), "unknown")
        # 取得 min_distance 和 PET
        min_distance = None
        pet = None

        ego_s = str(ego_id)
        other_s = str(other_actor_id)

        if hasattr(self, "pet_lookup"):
            result = self.pet_lookup.get((ego_s, other_s))
            if result is not None:
                min_distance, pet = result

        # 判斷 pet 是否為 1000000
        pet_str = "inf" if pet == 1000000 else (pet if pet is not None else "N/A")
        def format_float(val):
            return f"{val:.2f}" if isinstance(val, (float, int)) and val is not None else "N/A"

        # 準備要顯示的資料
        data = [
            ("Ego ID", ego_id),
            ("Other Actor ID", other_actor_id),
            ("Class", other_actor_class),
            ("Min Distance", format_float(min_distance)),
            ("PET", f"{format_float(pet) if pet_str != 'inf' else 'inf'}\n"),
        ]

        # 設定 tableWidget 行數與列數
        self.ui.tableWidget_label_info.setRowCount(len(data))
        self.ui.tableWidget_label_info.setColumnCount(2)
        self.ui.tableWidget_label_info.setHorizontalHeaderLabels(["項目", "數值"])

        # 設定字體大小
        font = QFont()

        if "ui_ipad_mini" in self.ui.__module__.lower():
            font.setPointSize(10)
        else:
            font.setPointSize(16)

        # 填入資料
        for row, (label, value) in enumerate(data):
            item_label = QTableWidgetItem(str(label))
            item_label.setFont(font)
            item_value = QTableWidgetItem(str(value))
            item_value.setFont(font)
            self.ui.tableWidget_label_info.setItem(row, 0, item_label)
            self.ui.tableWidget_label_info.setItem(row, 1, item_value)

    def next_actor(self):
        current_index = self.ui.comboBox_ego_id.currentIndex()
        total = self.ui.comboBox_ego_id.count()
        if total == 0:
            return
        next_index = current_index + 1
        if next_index < total:
            self.ui.comboBox_ego_id.setCurrentIndex(next_index)
        else:
            self.ui.comboBox_ego_id.setCurrentIndex(0)

        
        self.video_controller.range_slider.setMinimum(0)
        self.video_controller.setslidervalue(0)
        self.video_controller.current_frame_no = 0

    def prev_actor(self):
        current_index = self.ui.comboBox_ego_id.currentIndex()
        total = self.ui.comboBox_ego_id.count()
        if total == 0:
            return
        prev_index = current_index - 1
        if prev_index >= 0:
            self.ui.comboBox_ego_id.setCurrentIndex(prev_index)
        else:
            self.ui.comboBox_ego_id.setCurrentIndex(total - 1)

        
        self.video_controller.range_slider.setMinimum(0)
        self.video_controller.setslidervalue(0)
        self.video_controller.current_frame_no = 0

    def set_label_button_selected(self, selected_idx):
        id_pair = self.ui.comboBox_ego_id.currentText()
        ego_id, actor_id = id_pair.split("_")

        # 取得目前 class
        other_actor_class = actor_id
        other_actor_class = self.trackid_class.get(str(other_actor_class), "unknown").lower()
        car_truck_labels = [0, 1, 2, 6, 7, 8, 13]
        motor_bike_labels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13]
        ped_labels = [0, 11, 12, 13]
        blue_labels = set()
        if other_actor_class in ["car", "truck"]:
            blue_labels = set(car_truck_labels)
        elif other_actor_class in ["motorcycle", "bicycle"]:
            blue_labels = set(motor_bike_labels)
        elif other_actor_class == "pedestrian":
            blue_labels = set(ped_labels)

        # 加入 label=99 到所有合法範圍
        valid_indices = blue_labels | {99}

        # 如果選到的按鈕不在對應 class 的範圍，直接忽略
        if selected_idx not in valid_indices:
            return

        # 處理單一標籤選擇
        if selected_idx == 99:
            # Toggle 99 flag
            self.selected_label_idx_99 = not getattr(self, 'selected_label_idx_99', False)
            # 不改變主標籤
        else:
            # 單一標籤選擇
            self.selected_label_idx = selected_idx
            self.selected_label_idx_99 = False  # 重置 99 flag

        # 更新 UI 按鈕顏色
        for i in range(0, 14):
            btn = getattr(self.ui, f"pushButton_label_{i}")
            if i == self.selected_label_idx:
                btn.setStyleSheet("color: red;")
            elif i in blue_labels:
                btn.setStyleSheet("color: white;")
            else:
                btn.setStyleSheet("color: gray;")

        # 準備資料內容
        id = self.ui.comboBox_ego_id.currentText()
        ego_id, actor_id = id.split("_")
        
        min_frame, max_frame = self.video_controller.range_slider.value()  
        min_frame = self.video_controller.overlay_frame_list[min_frame]
        max_frame = self.video_controller.overlay_frame_list[max_frame]

        scenario = {
            "ego_id": ego_id,
            "actor_id": actor_id,
            "min_frame": min_frame,
            "max_frame": max_frame,
            "label_idx": self.selected_label_idx
        }
        key = f"{ego_id}_{actor_id}"

        # 儲存至主檔案 (labeled_scenarios.json)
        self._save_to_json("labeled_scenarios.json", key, scenario)

        # 處理 label 99 的獨立存檔 (complex_scenarios.json)
        if self.selected_label_idx_99:
            # 存入或更新獨立檔
            self._save_to_json("complex_scenarios.json", key, scenario)
        else:
            # 如果目前不含 99，嘗試從獨立檔移除該 key
            self._remove_from_json("complex_scenarios.json", key)

        # 更新按鈕顏色
        self.ui.pushButton_label_99.setStyleSheet("color: red;" if self.selected_label_idx_99 else "color: black;")

    def _save_to_json(self, file_name, key, data):
        """通用儲存輔助函式"""
        path = os.path.join(self.data_path, file_name)
        content = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = orjson.loads(f.read())
            except: content = {}
        
        content[key] = data
        flags = orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
        json_bytes = orjson.dumps(content, option=flags)
        with open(path, "wb") as f:
            f.write(json_bytes)

        print(f"已儲存 scenario: {data}")

    def _remove_from_json(self, file_name, key):
        """通用刪除輔助函式"""
        path = os.path.join(self.data_path, file_name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = orjson.loads(f.read())
                if key in content:
                    del content[key]
                    flags = orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS
                    json_bytes = orjson.dumps(content, option=flags)
                    with open(path, "wb") as f:
                        f.write(json_bytes)
            except: pass

        print(f"已移除 scenario: {key}")

    def click_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = os.path.join(self.data_path, "label_time_recording.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"按下時間：{current_time}\n")

    def save_current_checked(self):
        path = os.path.join(self.data_path, "label_check.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{self.ui.comboBox_ego_id.currentText()}\n")


        # make this button to red after clicked
        self.ui.pushButton_check_label_done.setStyleSheet("color: red;")

    def mark_special_scenario(self):
        id_pair = self.ui.comboBox_ego_id.currentText()
        ego_id, actor_id = id_pair.split("_")
        key = f"{ego_id}_{actor_id}"

        # Toggle special scenario 標記
        self.selected_special_scenario = not getattr(self, 'selected_special_scenario', False)

        min_frame, max_frame = self.video_controller.range_slider.value()  
        min_frame = self.video_controller.overlay_frame_list[min_frame]
        max_frame = self.video_controller.overlay_frame_list[max_frame]

        scenario = {
            "ego_id": ego_id,
            "actor_id": actor_id,
            "min_frame": min_frame,
            "max_frame": max_frame,
            "label_idx": self.selected_label_idx
        }

        # 根據狀態新增或刪除
        if self.selected_special_scenario:
            self._save_to_json("special_scenarios.json", key, scenario)
        else:
            self._remove_from_json("special_scenarios.json", key)

        # 更新按鈕顏色
        self.ui.pushButton_special_scenario.setStyleSheet("color: red;" if self.selected_special_scenario else "color: black;")
