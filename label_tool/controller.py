from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QMainWindow
from PyQt6.QtGui import QIcon, QFont

from video_controller import video_controller
import orjson
import pickle
import os
from datetime import datetime
import pandas as pd  # 新增
# python -m PyQt6.uic.pyuic label.ui -o UI.py


class MainWindow_controller(QMainWindow):
    # 檔案快取
    _file_cache = {}
    
    def __init__(self, ui_class, DATA_ID='01'):
        super().__init__() 
        self.ui = ui_class()  # 使用傳入的 UI 類別
        self.ui.setupUi(self)

        # 根據 UI 模組決定 ToolTip 字體大小
        
        if "ui_ipad_mini" in ui_class.__module__.lower():
            self.setStyleSheet("QToolTip { font-size: 12pt; }")
        else:
            self.setStyleSheet("QToolTip { font-size: 24pt; }")


        self.data_path = "../data"
        self.DATA_ID = DATA_ID
        self.label_num = 2
        
        print(f"Loading track #{self.DATA_ID} data...")
        # we load the dict for ego id and object id list
        with open(f'{self.data_path}/{self.DATA_ID}_trackid_objects.json', 'r', encoding='utf-8') as f:
            self.id_list = orjson.loads(f.read())
        # load pet and min distance dictory 
        # with open(f'{self.data_path}/{self.DATA_ID}_pet_distance_dict.json', 'r', encoding='utf-8') as f:
        #     self.pet_min_distance_dict = orjson.loads(f.read())
        
        # --- 改為從 parquet 讀取 ---
        parquet_path = os.path.join(self.data_path, f"{self.DATA_ID}_pet_optimized.parquet")
        pet_df = pd.read_parquet(parquet_path)
        self.pet_min_distance_dict = {}
        for row in pet_df.itertuples(index=False):
            k1 = f"{row.track_id1}_{row.track_id2}"
            k2 = f"{row.track_id2}_{row.track_id1}"
            self.pet_min_distance_dict[k1] = {"pet": row.pet, "min_distance": row.min_distance}
            self.pet_min_distance_dict[k2] = {"pet": -row.pet, "min_distance": row.min_distance}
        # --- end parquet ---

        with open(f'{self.data_path}/{self.DATA_ID}_trackid_class.json', 'r', encoding='utf-8') as f:
            self.trackid_class = orjson.loads(f.read())

        ego_id_list = list(self.id_list.keys())

        self.ui.comboBox_ego_id.clear()
        for ego_id in ego_id_list:
            self.ui.comboBox_ego_id.addItem(ego_id)
        
        self.current_ego_id = self.ui.comboBox_ego_id.currentText()
        
        other_actor_id = self.id_list[str(self.current_ego_id)]
        self.ui.comboBox_other_actor_id.clear()
        for actor_id in other_actor_id:
            self.ui.comboBox_other_actor_id.addItem(str(actor_id))
        
        print("Initializing video controller...")
        self.video_controller = video_controller(data_path=self.data_path, ui=self.ui, DATA_ID=self.DATA_ID)

        
        self.update_current_pet_min_distance_dict()
        self.show_only_unlabeled_ego = False
        self.show_only_unlabeled = False
        self.label_tooltip_on = False  # 預設關閉

        self.update_other_actor_id_combobox()


        # setup combobox signal
        self.ui.comboBox_ego_id.currentIndexChanged.connect(self.update_other_actor_id_combobox)
        self.ui.comboBox_other_actor_id.currentIndexChanged.connect(self.update_combobox_label_info)
        self.ui.pushButton_set_new_ego_id_range.clicked.connect(self.confirm_set_new_ego_id_range)
        self.ui.pushButton_remove_ego_id.clicked.connect(self.confirm_remove_ego_id)  # 新增這行

        self.ui.pushButton_apply_actor_filter.clicked.connect(self.filter_actor_id_list)
        self.ui.pushButton_next_actor.clicked.connect(self.next_actor)
        self.ui.pushButton_prev_actor.clicked.connect(self.prev_actor)

        self.ui.pushButton_label_notice_on.setText("開啟label 提示")
        self.ui.pushButton_label_notice_on.clicked.connect(self.toggle_label_tooltips)


        # 設定 label 按鈕點擊事件
        for i in list(range(0, self.label_num+1))+[88]:
            try:
                btn = getattr(self.ui, f"pushButton_label_{i}")
                btn.clicked.connect(lambda checked, idx=i: self.set_label_button_selected(idx))
            except AttributeError:
                print(f"Warning: pushButton_label_{i} not found in UI.")

        # 加入 label=99 按鈕（多種scenario）
        self.ui.pushButton_label_99.clicked.connect(lambda checked: self.set_label_button_selected(99))
        self.ui.pushButton_special_scenario.clicked.connect(self.mark_special_scenario)

        self.selected_label_btn_idx = None  # 記錄目前選中的 label 按鈕
        # self.ui.pushButton_show_only_unlabeled.clicked.connect(self.toggle_show_only_unlabeled)
        self.ui.pushButton_this_ego_done.clicked.connect(self.mark_this_ego_done)
        self.ui.pushButton_show_unlabeled_ego.clicked.connect(self.toggle_show_only_unlabeled_ego)
        self.ui.pushButton_quick_setup.clicked.connect(self.quick_setup)

        # pushButton_quick_setup 
        # doubleSpinBox_pet_min --> -10
        # doubleSpinBox_pet_max --> 10
        # doubleSpinBox_distance_max --> 5
        # checkBox_pet --> True
        # checkBox_distance --> True


        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = os.path.join(self.data_path, "label_time_recording.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"啟動時間：{start_time}\n")
    def quick_setup(self):
        """快速設定功能"""
        self.click_time()  # 記錄按下時間
        
        # 設定 doubleSpinBox 數值
        self.ui.doubleSpinBox_pet_min.setValue(-15)
        self.ui.doubleSpinBox_pet_max.setValue(15)
        self.ui.doubleSpinBox_distance_max.setValue(5)
        
        # 設定 checkBox 為 True
        self.ui.checkBox_pet.setChecked(True)
        self.ui.checkBox_distance.setChecked(True)
        
        
    def click_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = os.path.join(self.data_path, "label_time_recording.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"按下時間：{current_time}\n")

    def toggle_show_only_unlabeled_ego(self):
        self.click_time()
        self.show_only_unlabeled_ego = not self.show_only_unlabeled_ego

        # 讀取所有 ego_id
        all_ego_id_list = list(self.id_list.keys())

        # 讀取已完成的 ego_id
        save_path = os.path.join(self.data_path, f"{self.DATA_ID}_ego_done.json")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                try:
                    ego_done_list = orjson.loads(f.read())
                except Exception:
                    ego_done_list = []
        else:
            ego_done_list = []
            with open(save_path, "wb") as f:
                f.write(orjson.dumps(ego_done_list))

        if self.show_only_unlabeled_ego:
            # 過濾未標註過的 ego_id
            filtered_ego_id_list = [eid for eid in all_ego_id_list if eid not in ego_done_list]
            self.ui.pushButton_show_unlabeled_ego.setText("Show all ego")
        else:
            filtered_ego_id_list = all_ego_id_list
            self.ui.pushButton_show_unlabeled_ego.setText("Only show unlabeled ego")

        # 更新 comboBox_ego_id
        self.ui.comboBox_ego_id.clear()
        for ego_id in filtered_ego_id_list:
            self.ui.comboBox_ego_id.addItem(ego_id)

        # 重新觸發更新
        self.update_other_actor_id_combobox()


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
        self.ui.pushButton_label_3.setToolTip("ego 與機踏車同車道並行，機踏車自側後方加速超越" if enable else "")
        self.ui.pushButton_label_4.setToolTip("ego 與機踏車同車道並行，機踏車等速並行" if enable else "")
        self.ui.pushButton_label_5.setToolTip("ego 與機踏車同車道並行，機踏車自側前方減速被ego超越" if enable else "")
        self.ui.pushButton_label_6.setToolTip("ego 前方同車道有停止車（等左轉/臨停）\n，ego 通過前未移動即算，需換道 (含佔用一點車道情況)，例：338,913,1096,1997" if enable else "")
        self.ui.pushButton_label_7.setToolTip("前方 {Car, Truck, Motor/Bike} 從右側 cut-in" if enable else "")
        self.ui.pushButton_label_8.setToolTip("前方 {Car, Truck, Motor/Bike} 從左側 cut-in" if enable else "")
        self.ui.pushButton_label_9.setToolTip("ego 右轉，右側機踏車直行通過（含待轉區）" if enable else "")
        self.ui.pushButton_label_10.setToolTip("ego 左轉，對向機踏車準備待轉" if enable else "")
        self.ui.pushButton_label_11.setToolTip("ego 右轉後遇見行人通過" if enable else "")
        self.ui.pushButton_label_12.setToolTip("ego 左轉後遇見行人通過" if enable else "")
        self.ui.pushButton_label_13.setToolTip("ego 向右切車道遇到右側直行汽機車" if enable else "")
        self.ui.pushButton_label_14.setToolTip("ego 向左切車道遇到左側直行汽機車" if enable else "")
        self.ui.pushButton_label_15.setToolTip("ego 左轉遇到左側機踏車通過" if enable else "")
        

    def filter_actor_id_list(self):
        self.click_time()
        use_pet = self.ui.checkBox_pet.isChecked()
        use_distance = self.ui.checkBox_distance.isChecked()

        ego_id = self.ui.comboBox_ego_id.currentText()
        actor_id_list = self.id_list[ego_id]

        print("Filtered actor ID")

        # 兩個條件都沒選直接 return
        if not use_pet and not use_distance:
            # 如果目前 combobox 內容和 actor_id_list 不一樣才重設
            if self.ui.comboBox_other_actor_id.count() != len(actor_id_list):
                self.update_combobox_label_info()
            return []

        pet_min = self.ui.doubleSpinBox_pet_min.value()
        pet_max = self.ui.doubleSpinBox_pet_max.value()
        dist_min = self.ui.doubleSpinBox_distance_min.value()
        dist_max = self.ui.doubleSpinBox_distance_max.value()

        # 檢查 spinbox 的值是否在範圍內
        min_dist_min, min_dist_max = self.min_distance_range if self.min_distance_range else (None, None)
        pet_range_min, pet_range_max = self.pet_range if self.pet_range else (None, None)
        print(" list by range:pet({} ~ {}), distance({} ~ {})".format(pet_min, pet_max, dist_min, dist_max))

        if use_pet and pet_range_min is not None and pet_min < pet_range_min:
            pet_min = pet_range_min
        if use_distance and min_dist_min is not None and dist_min < min_dist_min:
            dist_min = min_dist_min

        if use_distance:
            if min_dist_min is not None and (dist_max > min_dist_max):
                return []
        if use_pet:
            if pet_range_min is not None and (pet_max > pet_range_max):
                return []
            
        filtered_list = []
        for actor_id in actor_id_list:
            key = f"{ego_id}_{actor_id}"
            info = self.pet_min_distance_dict.get(key)
            if info is None:
                continue
            pet = info.get("pet", None)
            min_distance = info.get("min_distance", None)
            # pet_val = float('inf') if pet == 1000000 else pet

            # 條件判斷
            pet_ok = False
            dist_ok = False
            if use_pet:
                pet_ok = pet is not None and pet_min - 0.01 <= pet <= pet_max + 0.01
            if use_distance:
                dist_ok = min_distance is not None and dist_min - 0.01 <= min_distance <= dist_max  + 0.01

            # 只要有一個條件符合就納入
            if pet_ok or dist_ok:
                filtered_list.append(actor_id)
            

        # 依 min_distance 排序
        def get_min_distance(actor_id):
            key = f"{ego_id}_{actor_id}"
            info = self.pet_min_distance_dict.get(key)
            if info is not None:
                min_distance = info.get("min_distance", float('inf'))
                if min_distance == 100000 or min_distance is None:
                    return float('inf')
                return min_distance
            return float('inf')

        sorted_filtered_list = sorted(filtered_list, key=get_min_distance)

        self.ui.comboBox_other_actor_id.clear()
        for actor_id in sorted_filtered_list:
            self.ui.comboBox_other_actor_id.addItem(str(actor_id))

        print("Filtered actor ID list by range:", pet_min, pet_max, dist_min, dist_max)
        self.update_combobox_label_info()

    def confirm_remove_ego_id(self):
        self.click_time()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.NoIcon)
        msg.setWindowTitle("確認")
        msg.setText("你確定要移除這個 Ego ID 嗎？")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setWindowIcon(QIcon())  # 移除視窗 icon
        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Yes:
            print("已確認移除 Ego ID", self.ui.comboBox_ego_id.currentText())

            # remove ego id from file and from combobox and select next ego id
            with open(f'{self.data_path}/{self.DATA_ID}_trackid_objects.json', 'r', encoding='utf-8') as f:
                self.id_list = orjson.loads(f.read())
            
            current_index = self.ui.comboBox_ego_id.currentIndex()
            current_ego_id = self.ui.comboBox_ego_id.currentText()
            if not current_ego_id:
                return

            # 從 dict 移除
            if current_ego_id in self.id_list:
                del self.id_list[current_ego_id]
                # 寫回檔案
                with open(f'{self.data_path}/{self.DATA_ID}_trackid_objects.json', 'wb') as f:
                    f.write(orjson.dumps(self.id_list, option=orjson.OPT_INDENT_2))
                    
                # 更新 combobox
                self.ui.comboBox_ego_id.clear()
                for ego_id in self.id_list.keys():
                    self.ui.comboBox_ego_id.addItem(ego_id)

                # 設定 combobox index 為「原本的下一個」
                if self.ui.comboBox_ego_id.count() > 0:
                    # 如果原本是最後一個，選擇新的最後一個
                    if current_index >= self.ui.comboBox_ego_id.count():
                        self.ui.comboBox_ego_id.setCurrentIndex(self.ui.comboBox_ego_id.count() - 1)
                    else:
                        self.ui.comboBox_ego_id.setCurrentIndex(current_index)
                else:
                    self.ui.comboBox_other_actor_id.clear()
                    self.ui.label_info.setText("")

    def confirm_set_new_ego_id_range(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("確認")
        msg.setText("你確定要設定新的 Ego ID 範圍嗎？")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        ret = msg.exec()
        if ret == QMessageBox.StandardButton.Yes:
            # 執行你的動作
            print("已確認設定新的 Ego ID 範圍")

            self.video_controller.remove_frames_outside_range()
            self.video_controller.reloaded_track_dict()
            self.update_other_actor_id_combobox()

            # get ego id 
            # range_slider
        
    def update_current_pet_min_distance_dict(self):

        # get the current ego id 
        self.current_ego_id = self.ui.comboBox_ego_id.currentText()
        # get other actor id 
        other_actor_id = self.id_list[str(self.current_ego_id)]

        # create a dict, key = {other_actor_id}, value = min distance and pet 
        self.current_ped_min_distance_dict = {}
        min_distance_list = []
        pet_list = []
        for actor_id in other_actor_id:
            key = f"{self.current_ego_id}_{actor_id}"
            if key in self.pet_min_distance_dict:
                info = self.pet_min_distance_dict[key]
                self.current_ped_min_distance_dict[actor_id] = info
                min_distance = info.get("min_distance", None)
                pet = info.get("pet", None)
                # 排除極端值
                if min_distance is not None and min_distance != 100000:
                    min_distance_list.append(min_distance)
                if pet is not None and pet != 100000 and pet != 1000000:
                    pet_list.append(pet)
            else:
                self.current_ped_min_distance_dict[actor_id] = None

        # 計算範圍
        self.min_distance_range = (min(min_distance_list), max(min_distance_list)) if min_distance_list else (None, None)
        self.pet_range = (min(pet_list), max(pet_list)) if pet_list else (None, None)

        # setup 

        # 設定 spinbox 限制與數值
        # PET
        if self.pet_range[0] is not None and self.pet_range[1] is not None:
            self.ui.doubleSpinBox_pet_min.setMinimum(self.pet_range[0])
            self.ui.doubleSpinBox_pet_min.setMaximum(self.pet_range[1])
            self.ui.doubleSpinBox_pet_max.setMinimum(self.pet_range[0])
            self.ui.doubleSpinBox_pet_max.setMaximum(self.pet_range[1])

            self.ui.doubleSpinBox_pet_min.setValue(self.pet_range[0])
            self.ui.doubleSpinBox_pet_max.setValue(self.pet_range[1])

            
        # min_distance
        if self.min_distance_range[0] is not None and self.min_distance_range[1] is not None:
            self.ui.doubleSpinBox_distance_min.setMinimum(self.min_distance_range[0])
            self.ui.doubleSpinBox_distance_min.setMaximum(self.min_distance_range[1])
            self.ui.doubleSpinBox_distance_max.setMinimum(self.min_distance_range[0])
            self.ui.doubleSpinBox_distance_max.setMaximum(self.min_distance_range[1])
            
        
            self.ui.doubleSpinBox_distance_min.setValue(self.min_distance_range[0])
            self.ui.doubleSpinBox_distance_max.setValue(self.min_distance_range[1])

    def update_other_actor_id_combobox(self):
        self.current_ego_id = self.ui.comboBox_ego_id.currentText()
        if not self.current_ego_id or self.current_ego_id not in self.id_list:
            self.ui.comboBox_other_actor_id.clear()
            return

        actor_id_list = self.id_list[self.current_ego_id]

        # 只顯示未標註過的
        if self.show_only_unlabeled:
            save_path = os.path.join(self.data_path, f"{self.DATA_ID}_labeled_scenarios.json")
            if os.path.exists(save_path):
                with open(save_path, "r", encoding="utf-8") as f:
                    try:
                        labeled_dict = orjson.loads(f.read())
                    except Exception:
                        labeled_dict = {}
            else:
                labeled_dict = {}

            filtered_actor_id_list = []
            for actor_id in actor_id_list:
                key = f"{self.current_ego_id}_{actor_id}"
                if key not in labeled_dict:
                    filtered_actor_id_list.append(actor_id)
        else:
            filtered_actor_id_list = actor_id_list

        # 依 min_distance 排序
        def get_min_distance(actor_id):
            key = f"{self.current_ego_id}_{actor_id}"
            info = self.pet_min_distance_dict.get(key)
            if info is not None:
                min_distance = info.get("min_distance", float('inf'))
                # 排除極端值
                if min_distance == 100000 or min_distance is None:
                    return float('inf')
                return min_distance
            return float('inf')

        sorted_actor_id = sorted(filtered_actor_id_list, key=get_min_distance)

        self.ui.comboBox_other_actor_id.clear()
        for actor_id in sorted_actor_id:
            self.ui.comboBox_other_actor_id.addItem(str(actor_id))

        self.update_combobox_label_info()


        self.update_current_pet_min_distance_dict()

    def toggle_show_only_unlabeled(self):
        self.click_time()
        self.show_only_unlabeled = not self.show_only_unlabeled

        if self.show_only_unlabeled:
            self.ui.pushButton_show_only_unlabeled.setText("Show all actors")
        else:
            self.ui.pushButton_show_only_unlabeled.setText("Only show unlabeled actors")

        self.update_other_actor_id_combobox()

    def update_combobox_label_info(self):

        if self.ui.comboBox_other_actor_id.count() == 0:
            return  # 沒有內容就直接跳出
        # label_combobox_ego_id
        # x / x 
        total = self.ui.comboBox_ego_id.count()
        current_index = self.ui.comboBox_ego_id.currentIndex() + 1  # 1-based
        self.ui.label_combobox_ego_id.setText(f"{current_index} / {total}")

        # label_combobox_other_actor_id
        # x / x
        total = self.ui.comboBox_other_actor_id.count()
        current_index = self.ui.comboBox_other_actor_id.currentIndex() + 1  # 1-based
        self.ui.label_combobox_other_actor_id.setText(f"{current_index} / {total}")


        self.video_controller.update_video_info()
        # 新增: 更新 range slider bar
        self.video_controller.update_range_slider_bar()


        # update label info
        # get the current ego id
        # other actor id
        # other id class 
        # other id min distance and PET

        # 取得 ego_id
        ego_id = self.ui.comboBox_ego_id.currentText()
        # 取得 other actor id
        other_actor_id = self.ui.comboBox_other_actor_id.currentText()
        # 取得 other actor class
        other_actor_class = self.trackid_class.get(str(other_actor_id), "unknown")
        # 取得 min_distance 和 PET
        min_distance = None
        pet = None
        key = f"{ego_id}_{other_actor_id}"
        if key in self.pet_min_distance_dict:
            min_distance = self.pet_min_distance_dict[key].get("min_distance", None)
            pet = self.pet_min_distance_dict[key].get("pet", None)
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

            ("min distance range", f"{format_float(self.min_distance_range[0])} - {format_float(self.min_distance_range[1])}"),
            ("min pet range", f"{format_float(self.pet_range[0])} - {format_float(self.pet_range[1])}")
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


        # 取得 ego_id 與 actor_id
        ego_id = self.ui.comboBox_ego_id.currentText()
        actor_id = self.ui.comboBox_other_actor_id.currentText()
        key = f"{ego_id}_{actor_id}"

        # 讀取已標註 scenario
        save_path = os.path.join(self.data_path, f"{self.DATA_ID}_labeled_scenarios.json")
        selected_label_idx = None
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                try:
                    labeled_dict = orjson.loads(f.read())
                    if key in labeled_dict:
                        selected_label_idx = labeled_dict[key].get("label_idx", None)
                except Exception:
                    pass

        self.selected_label_idx = selected_label_idx

        # 讀取 label 99 標記
        complex_path = os.path.join(self.data_path, f"{self.DATA_ID}_complex_scenarios.json")
        self.selected_label_idx_99 = False
        if os.path.exists(complex_path):
            with open(complex_path, "r", encoding="utf-8") as f:
                try:
                    complex_dict = orjson.loads(f.read())
                    if key in complex_dict:
                        self.selected_label_idx_99 = True
                except Exception:
                    pass

        # 讀取特別scenario標記
        special_path = os.path.join(self.data_path, f"{self.DATA_ID}_special_scenarios.json")
        self.selected_special_scenario = False
        if os.path.exists(special_path):
            with open(special_path, "r", encoding="utf-8") as f:
                try:
                    special_dict = orjson.loads(f.read())
                    if key in special_dict:
                        self.selected_special_scenario = True
                except Exception:
                    pass

        # 設定按鈕顏色
        car_truck_labels = [0, 1, 2, 6, 7, 8, 13, 14, 88]
        motor_bike_labels = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 88]
        ped_labels = [0, 11, 12, 88]
        cls = self.trackid_class.get(str(actor_id), "unknown").lower()
        blue_labels = set()
        if cls in ["car", "truck"]:
            blue_labels = set(car_truck_labels)
        elif cls in ["motorcycle", "bicycle"]:
            blue_labels = set(motor_bike_labels)
        elif cls == "pedestrian":
            blue_labels = set(ped_labels)

        for i in list(range(0, self.label_num+1))+[88]:
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

    def next_actor(self):
        self.click_time()
        current_index = self.ui.comboBox_other_actor_id.currentIndex()
        total = self.ui.comboBox_other_actor_id.count()
        if total == 0:
            return
        next_index = current_index + 1
        if next_index < total:
            self.ui.comboBox_other_actor_id.setCurrentIndex(next_index)
        else:
            self.ui.comboBox_other_actor_id.setCurrentIndex(0)

        
        self.video_controller.range_slider.setMinimum(0)
        self.video_controller.setslidervalue(0)
        self.video_controller.current_frame_no = 0

    def prev_actor(self):
        self.click_time()
        current_index = self.ui.comboBox_other_actor_id.currentIndex()
        total = self.ui.comboBox_other_actor_id.count()
        if total == 0:
            return
        prev_index = current_index - 1
        if prev_index >= 0:
            self.ui.comboBox_other_actor_id.setCurrentIndex(prev_index)
        else:
            self.ui.comboBox_other_actor_id.setCurrentIndex(total - 1)

        
        self.video_controller.range_slider.setMinimum(0)
        self.video_controller.setslidervalue(0)
        self.video_controller.current_frame_no = 0

    def set_label_button_selected(self, selected_idx):
        self.click_time()

        # 1. 取得當前 Actor 的合法標籤範圍
        other_actor_id = self.ui.comboBox_other_actor_id.currentText()
        cls = self.trackid_class.get(str(other_actor_id), "unknown").lower()
        valid_indices = {0, 1, 2, 6, 7, 8, 88, 99}
        if cls in ["motorcycle", "bicycle"]:
            valid_indices = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 88, 99}
        elif cls == "pedestrian":
            valid_indices = {0, 11, 12, 88, 99}

        if selected_idx not in valid_indices:
            return

        # 2. 處理單一標籤選擇
        if selected_idx == 99:
            # Toggle 99 flag
            self.selected_label_idx_99 = not getattr(self, 'selected_label_idx_99', False)
        else:
            # 單一標籤選擇
            self.selected_label_idx = selected_idx
            self.selected_label_idx_99 = False  # 重置 99 flag

        # 3. 更新 UI 按鈕顏色
        blue_labels = valid_indices - {99}
        for i in list(range(0, self.label_num + 1)) + [88]:
            try:
                btn = getattr(self.ui, f"pushButton_label_{i}")
                if i == self.selected_label_idx:
                    btn.setStyleSheet("color: red;")
                elif i in blue_labels:
                    btn.setStyleSheet("color: gray;")
                else:
                    btn.setStyleSheet("color: white;")
            except AttributeError:
                continue

        # 4. 準備資料內容
        ego_id = self.ui.comboBox_ego_id.currentText()
        actor_id = self.ui.comboBox_other_actor_id.currentText()
        min_f, max_f = self.video_controller.range_slider.value()
        min_frame = self.video_controller.overlay_frame_list[min_f]
        max_frame = self.video_controller.overlay_frame_list[max_f]
        key = f"{ego_id}_{actor_id}"

        scenario_data = {
            "ego_id": ego_id,
            "actor_id": actor_id,
            "min_frame": min_frame,
            "max_frame": max_frame,
            "label_idx": self.selected_label_idx,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 5. 儲存至主檔案 (labeled_scenarios.json)
        self._save_to_json(f"{self.DATA_ID}_labeled_scenarios.json", key, scenario_data)

        # 6. 處理 label 99 的獨立存檔 (complex_scenarios.json)
        if self.selected_label_idx_99:
            self._save_to_json(f"{self.DATA_ID}_complex_scenarios.json", key, scenario_data)
        else:
            self._remove_from_json(f"{self.DATA_ID}_complex_scenarios.json", key)

        # 7. 更新按鈕顏色
        self.ui.pushButton_label_99.setStyleSheet("color: red;" if self.selected_label_idx_99 else "color: black;")

    def mark_special_scenario(self):
        self.click_time()
        ego_id = self.ui.comboBox_ego_id.currentText()
        actor_id = self.ui.comboBox_other_actor_id.currentText()
        key = f"{ego_id}_{actor_id}"

        # Toggle special scenario 標記
        self.selected_special_scenario = not getattr(self, 'selected_special_scenario', False)

        min_f, max_f = self.video_controller.range_slider.value()
        min_frame = self.video_controller.overlay_frame_list[min_f]
        max_frame = self.video_controller.overlay_frame_list[max_f]

        scenario_data = {
            "ego_id": ego_id,
            "actor_id": actor_id,
            "min_frame": min_frame,
            "max_frame": max_frame,
            "label_idx": self.selected_label_idx,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 根據狀態新增或刪除
        if self.selected_special_scenario:
            self._save_to_json(f"{self.DATA_ID}_special_scenarios.json", key, scenario_data)
        else:
            self._remove_from_json(f"{self.DATA_ID}_special_scenarios.json", key)

        # 更新按鈕顏色
        self.ui.pushButton_special_scenario.setStyleSheet("color: red;" if self.selected_special_scenario else "color: black;")
    def _load_json_file(self, path):
        """通用讀取輔助函式"""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    content = orjson.loads(f.read())
                except Exception:
                    content = {}
        else:
            content = {}
        return content

    def _save_to_json(self, file_name, key, data):
        """通用儲存輔助函式"""
        path = os.path.join(self.data_path, file_name)
        content = self._load_json_file(path)
        content[key] = data
        self._save_json_file(path, content)
        print(f"已儲存 scenario: {data}")

    def _remove_from_json(self, file_name, key):
        """通用刪除輔助函式"""
        path = os.path.join(self.data_path, file_name)
        content = self._load_json_file(path)
        if key in content:
            del content[key]
            self._save_json_file(path, content)
        print(f"已移除 scenario: {key}")


    def mark_this_ego_done(self):
        self.click_time()
        ego_id = self.ui.comboBox_ego_id.currentText()
        reply = QMessageBox.question(
            self,
            "確認",
            f"你確定要將 ego_id {ego_id} 標記為已完成嗎？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        save_path = os.path.join(self.data_path, f"{self.DATA_ID}_ego_done.json")
        ego_done_list = self._load_json_file(save_path)
        print(ego_done_list)

        if ego_id not in ego_done_list:
            ego_done_list.append(ego_id)
            self._save_json_file(save_path, ego_done_list)
            print(f"已標記 ego_id {ego_id} 為已完成")
        else:
            print(f"ego_id {ego_id} 已經標記過")

    def _save_json_file(self, path, content):
        """將 dict 內容存成 JSON 檔案（utf-8, pretty, 支援中文）"""
        with open(path, "wb") as f:
            f.write(orjson.dumps(content, option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS))

