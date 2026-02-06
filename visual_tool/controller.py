import base64
from zipfile import Path
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QMainWindow, QProgressBar,
    QCheckBox, QVBoxLayout, QGroupBox
)
from PyQt6.QtGui import QIcon, QFont
import pandas as pd
import orjson
import os
from time import time
from video_controller import video_controller
from datetime import datetime
import platform
import base64
from pathlib import Path
#  python -m PyQt6.uic.pyuic label.ui -o UI.py


class MainWindow_controller(QMainWindow):
    def __init__(self, ui_class, DATA_ID='00'):
        super().__init__()
        self.ui = ui_class()
        self.ui.setupUi(self)

        # 設定要篩選的 label_idx 值
        self.MAX_LABEL_IDX = 15


        # 根據 UI 模組決定 ToolTip 字體大小
        if "ui_ipad_mini" in ui_class.__module__.lower():
            self.setStyleSheet("QToolTip { font-size: 12pt; }")
        else:
            self.setStyleSheet("QToolTip { font-size: 24pt; }")


        self.data_path = "../data"
        self.DATA_ID = DATA_ID

        self.show_label = set()

        print(f"Loading track #{self.DATA_ID} data...")
        start_time = time()
        self.pet_results_df = pd.read_parquet(f'../data/{self.DATA_ID}_pet_optimized.parquet')
        
        print(f"load pet_distance_dict.parquet time: {time() - start_time:.2f} sec")


        # # 建立 lookup table（O(1) 查詢）
        # self.pet_lookup = {}
        # for row in self.pet_results_df.itertuples(index=False):
        #     a1 = str(row.track_id1)
        #     a2 = str(row.track_id2)

        #     self.pet_lookup[(a1, a2)] = (row.min_distance, row.pet)
        #     self.pet_lookup[(a2, a1)] = (row.min_distance, -row.pet)

        print(f"load pet_lookup time: {time() - start_time:.2f} sec")

        # 讀取 label 99 標記
        complex_path = os.path.join(self.data_path, f"{self.DATA_ID}_complex_scenarios.json")
        if os.path.exists(complex_path):
            with open(complex_path, "r", encoding="utf-8") as f:
                self.complex_dict = orjson.loads(f.read())
        else:
            return

        # 讀取特別scenario標記
        special_path = os.path.join(self.data_path, f"{self.DATA_ID}_special_scenarios.json")
        if os.path.exists(special_path):
            with open(special_path, "r", encoding="utf-8") as f:
                self.special_dict = orjson.loads(f.read())
        else:
            return
        
        # load labeled scenarios 
        save_path = os.path.join(self.data_path, f"{self.DATA_ID}_labeled_scenarios.json")
        print(f"load labeled_scenarios.json time: {time() - start_time:.2f} sec")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                labeled_dict = orjson.loads(f.read())
        else:
            return
        print(f"load labeled_scenarios.json time: {time() - start_time:.2f} sec")
        start_time = time() 
        
        # unique_ego[ego_id][label_idx][actor_id] = (min_frame, max_frame)
        self.unique_ego = {}
        for key in labeled_dict.keys():
            ego_id = labeled_dict[key]['ego_id']
            actor_id = labeled_dict[key]['actor_id']
            min_frame = labeled_dict[key]['min_frame']
            max_frame = labeled_dict[key]['max_frame']
            label_idx = labeled_dict[key]['label_idx']
            if ego_id not in self.unique_ego:
                self.unique_ego[ego_id] = {}
            if label_idx not in self.unique_ego[ego_id]:
                self.unique_ego[ego_id][label_idx] = {}
            self.unique_ego[ego_id][label_idx][actor_id] = (min_frame, max_frame)

        print(f"load labeled_scenarios.json time: {time() - start_time:.2f} sec")
        start_time = time() 

        ego_ids = list(self.unique_ego.keys())
        self.ui.comboBox_ego_id.clear()
        for id in ego_ids:
            if len(set(self.unique_ego[id].keys())-{0}) == 0:
                continue
            self.ui.comboBox_ego_id.addItem(id)

        self.update_combobox_label_info()

        # 動態label checkbox區
        self.label_checkbox_group = QGroupBox("Labels")
        self.label_checkbox_layout = QVBoxLayout()
        self.label_checkbox_group.setLayout(self.label_checkbox_layout)
        # 嘗試加到 verticalLayoutWidget 的 layout
        if hasattr(self.ui, "verticalLayoutWidget"):
            layout = self.ui.verticalLayoutWidget.layout()
            if layout is not None:
                layout.addWidget(self.label_checkbox_group)

        self.label_checkboxes = {}  # {label_idx: QCheckBox}
        self.selected_labels = set()

        self.ui.comboBox_ego_id.currentIndexChanged.connect(self.update_label_checkboxes)
        self.ui.pushButton_next_actor.clicked.connect(self.next_actor)
        self.ui.pushButton_prev_actor.clicked.connect(self.prev_actor)

        self.video_controller = video_controller(data_path=self.data_path, ui=self.ui, DATA_ID=self.DATA_ID)

        self.update_label_checkboxes()
        # 預設顯示所有 label 的 agents
        self.show_label = set(self.unique_ego[self.ui.comboBox_ego_id.currentText()].keys())
        # 除了0 (None)
        self.show_label -= {0}
        self.update_agents_display()

        # 設定 label 按鈕點擊事件
        for i in list(range(0, self.MAX_LABEL_IDX+1))+[88]:
            btn = getattr(self.ui, f"pushButton_label_{i}")
            btn.clicked.connect(lambda checked, idx=i: self.set_label_button_selected(idx))

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
        self.ui.pushButton_label_13.setToolTip("ego 向右切出車道遇到右側直行汽機車" if enable else "")
        self.ui.pushButton_label_14.setToolTip("ego 向左切出車道遇到左側直行汽機車" if enable else "")
        self.ui.pushButton_label_15.setToolTip("ego 左轉遇到左側機踏車通過" if enable else "")
        
    def update_combobox_label_info(self):
        print("Updating combobox label info...")
        # label_combobox_ego_id
        # x / x 
        total = self.ui.comboBox_ego_id.count()
        current_index = self.ui.comboBox_ego_id.currentIndex() + 1  # 1-based
        self.ui.label_combobox_ego_id.setText(f"{current_index} / {total}")

        # self.video_controller.update_video_info()


        ego_id = self.ui.comboBox_ego_id.currentText()
        contain_labels = list(self.unique_ego[ego_id].keys())

        for i in range(0, self.MAX_LABEL_IDX + 1):
            btn = getattr(self.ui, f"pushButton_label_{i}")
            if i in self.show_label:
                btn.setStyleSheet("color: red;")
            elif i in contain_labels:
                btn.setStyleSheet("color: gray;")
            else:
                btn.setStyleSheet("color: white;")


        self.selected_label_idx_99 = False
        self.selected_special_scenario = False
        for label_id in contain_labels:
            for actor_id in self.unique_ego[ego_id][label_id].keys():
                current_id_pair = f"{ego_id}_{actor_id}"
                if current_id_pair in self.complex_dict:
                    self.selected_label_idx_99 = True
                if current_id_pair in self.special_dict:
                    self.selected_special_scenario = True

       
        # 設定 label_99 和 special_scenario 按鈕顏色
        self.ui.pushButton_label_99.setStyleSheet("color: red;" if self.selected_label_idx_99 else "color: black;")
        self.ui.pushButton_special_scenario.setStyleSheet("color: red;" if self.selected_special_scenario else "color: black;")


        return

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
        """
        Toggle show/hide labels agents in the video
        """
        ego_id = self.ui.comboBox_ego_id.currentText()
        contain_labels = list(self.unique_ego[ego_id].keys())
        if selected_idx not in contain_labels:
            return

        # toggle label selection
        if selected_idx in self.show_label:
            self.show_label.remove(selected_idx)
        else:
            self.show_label.add(selected_idx)

        self.update_agents_display()

        # 更新 UI 按鈕顏色
        for i in list(range(0, self.MAX_LABEL_IDX+1))+[88]:
            btn = getattr(self.ui, f"pushButton_label_{i}")
            if i in self.show_label:
                btn.setStyleSheet("color: red;")
            elif i in contain_labels:
                btn.setStyleSheet("color: gray;")
            else:
                btn.setStyleSheet("color: white;")

        # 同步 checkbox 狀態
        for label_idx, cb in self.label_checkboxes.items():
            cb.setChecked(label_idx in self.show_label)

    def update_label_checkboxes(self):
        # 清空舊的checkbox
        for cb in self.label_checkboxes.values():
            self.label_checkbox_layout.removeWidget(cb)
            cb.deleteLater()
        self.label_checkboxes.clear()
        self.selected_labels.clear()

        ego_id = self.ui.comboBox_ego_id.currentText()
        if not ego_id or ego_id not in self.unique_ego:
            self.show_label = set()
            self.video_controller.clear_agents()
            return

        label_indices = sorted(self.unique_ego[ego_id].keys())
        for label_idx in label_indices:
            cb = QCheckBox(f"Label {label_idx}")
            cb.stateChanged.connect(lambda state, idx=label_idx: self.on_label_checkbox_changed(idx, state))
            self.label_checkbox_layout.addWidget(cb)
            self.label_checkboxes[label_idx] = cb

        # 預設全選（不含0），如果沒有可選label則清空
        valid_labels = set(label_indices) - {0}
        self.show_label = valid_labels.copy()
        for label_idx, cb in self.label_checkboxes.items():
            cb.setChecked(label_idx in self.show_label)
        self.update_agents_display()

    def update_agents_display(self):
        ego_id = self.ui.comboBox_ego_id.currentText()
        if not ego_id or ego_id not in self.unique_ego or not self.show_label:
            self.video_controller.clear_agents()
            return
        agents = set()
        min_frame, max_frame = None, None
        # 收集所有 actor_id 與 frame 範圍
        for label_idx in self.unique_ego[ego_id].keys():
            for actor_id, (f0, f1) in self.unique_ego[ego_id][label_idx].items():
                if label_idx in self.show_label:
                    agents.add(actor_id)
                if min_frame is None or int(f0) < int(min_frame):
                    min_frame = f0
                if max_frame is None or int(f1) > int(max_frame):
                    max_frame = f1
        agent_list = list(agents)
        current_frame_no = self.video_controller.current_frame_no
        if agent_list and min_frame is not None and max_frame is not None and min_frame <= max_frame:
            self.video_controller.show_agents(ego_id, agent_list, min_frame, max_frame)
            if self.video_controller.total_frame_count > 0:
                frame_no = min(current_frame_no, self.video_controller.total_frame_count - 1)
                self.video_controller.setslidervalue(frame_no)
        else:
            self.video_controller.clear_agents()

    def on_label_checkbox_changed(self, label_idx, state):
        if state:
            self.show_label.add(label_idx)
        else:
            self.show_label.discard(label_idx)
        self.update_agents_display()
        # 同步 label button 顏色
        ego_id = self.ui.comboBox_ego_id.currentText()
        contain_labels = list(self.unique_ego[ego_id].keys())
        for i in list(range(0, self.MAX_LABEL_IDX+1))+[88]:
            btn = getattr(self.ui, f"pushButton_label_{i}")
            if i in self.show_label:
                btn.setStyleSheet("color: red;")
            elif i in contain_labels:
                btn.setStyleSheet("color: gray;")
            else:
                btn.setStyleSheet("color: white;")

    def update_video_for_selected_labels(self):
        # 已由 update_agents_display 取代
        pass