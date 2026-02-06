from PyQt6 import QtCore
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QSlider, QPushButton, QMessageBox, QFileDialog
import numpy as np
import cv2
import orjson
import os
from superqt import QRangeSlider
import imageio


def draw_rotated_bbox(img, x, y, width, length, heading, color=(0,255,0), thickness=2):
    """繪製旋轉的邊界框"""
    box = np.array([
        [-length/2, -width/2],
        [-length/2,  width/2],
        [ length/2,  width/2],
        [ length/2, -width/2]
    ])
    theta = np.deg2rad(-heading)
    rot = np.array([
        [np.cos(theta), -np.sin(theta)],
        [np.sin(theta),  np.cos(theta)]
    ])
    box = box @ rot.T
    box += np.array([x, y])
    box = box.astype(int)
    cv2.fillPoly(img, [box], color=color)


ortho_px_to_meter = 0.0499967249445942


class DoubleClickButton(QPushButton):
    """支援雙擊事件的按鈕"""
    doubleClicked = QtCore.pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class BaseVideoController(object):
    """視訊控制器基底類別 - 包含所有共用功能"""

    # 子類別可覆寫的屬性
    USE_SECONDARY_SLIDER = False  # 是否使用 secondary_slider
    BACKGROUND_FILENAME_TEMPLATE = "{DATA_ID}_background.png"  # 背景圖檔名模板
    DEFAULT_TIMER_INTERVAL = 30  # 預設 timer interval (ms)
    

    def __init__(self, data_path, ui, DATA_ID):
        self.debug_mode = False
        
        self.data_path = data_path
        self.ui = ui
        self.DATA_ID = DATA_ID
        

        self.show_object_location_trigger = False
        self._onscreen_render_cache = {}
        self._slider_updating = False
        
        # 0.5 倍速用的累加器
        self._half_speed_accumulator = 0.0

        # 設定速度選單
        self.speed_map = self.get_speed_map()
        self.ui.comboBox_speed.clear()
        self.ui.comboBox_speed.addItems(list(self.speed_map.keys()))
        self.ui.comboBox_speed.setCurrentText("1")
        self.ui.comboBox_speed.currentTextChanged.connect(self.change_speed)
        self.current_speed_interval = self.speed_map["1"]

        # 建立 secondary_slider (子類別可選擇是否使用)
        if self.USE_SECONDARY_SLIDER:
            self.secondary_slider = QSlider(Qt.Orientation.Horizontal)
            self.secondary_slider.setRange(0, 1)
            self.secondary_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 0px;
                    background: #C0C0C0;
                }
                QSlider::handle:horizontal {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #666666, stop:1 #444444);
                    border: 1px solid #333;
                    width: 7px;
                    height: 20px;
                    margin: -10px 0;
                    border-radius: 4px;
                }
                QSlider::sub-page:horizontal, QSlider::add-page:horizontal {
                    background: transparent;
                }
            """)
            self.ui.verticalLayout.addWidget(self.secondary_slider)

        # 建立 range_slider
        self.range_slider = QRangeSlider(Qt.Horizontal)
        self.ui.verticalLayout.addWidget(self.range_slider)

        # 載入背景圖片
        bg_filename = self.BACKGROUND_FILENAME_TEMPLATE.format(DATA_ID=self.DATA_ID)
        self.image_background = cv2.imread(f'{self.data_path}/{bg_filename}')
        self.image_width = self.image_background.shape[1]
        self.image_height = self.image_background.shape[0]

        # 載入 trackid to class
        with open(f'{self.data_path}/{self.DATA_ID}_trackid_class.json', 'r', encoding='utf-8') as f:
            self.trackid_class = orjson.loads(f.read())

        # 載入 track dict
        if self.debug_mode:
            with open(f'{self.data_path}/{self.DATA_ID}_track_frame_dict_mini.json', 'r', encoding='utf-8') as f:
                self.track_dict = orjson.loads(f.read())
        else:
            with open(f'{self.data_path}/{self.DATA_ID}_track_frame_dict.json', 'r', encoding='utf-8') as f:
                self.track_dict = orjson.loads(f.read())

        self.current_frame_no = 0
        self.videoplayer_state = "play"
        self.counter = 0
        self.route_index = 0
        self.overlay_frame_list = []
        self.total_frame_count = 0
        self.current_ego_id = ""
        self.current_other_actor_id = ""

        # 初始化視訊資訊 - 由子類別實作
        self.update_video_info()
        self.set_video_player()

        # 替換 pushButton_play_or_stop 為 DoubleClickButton
        self._setup_play_button()

        # 連接信號
        self._connect_signals()

    def get_speed_map(self):
        """取得速度對應表 - 子類別可以覆寫"""
        return {
            "10": 10,
            "5": 5,
            "3": 3,
            "2": 2,
            "1": 1,
            "0.5": 0.5
        }

    def _setup_play_button(self):
        """設置播放按鈕"""
        orig_btn = self.ui.pushButton_play_or_stop
        parent = orig_btn.parent()
        geometry = orig_btn.geometry()
        orig_btn.hide()
        self.ui.pushButton_play_or_stop = DoubleClickButton(parent)
        self.ui.pushButton_play_or_stop.setGeometry(geometry)
        self.ui.pushButton_play_or_stop.setText(orig_btn.text())
        self.ui.pushButton_play_or_stop.show()

    def _connect_signals(self):
        """連接所有信號"""
        self.ui.pushButton_play_or_stop.clicked.connect(self.toggle_play_or_stop)
        self.ui.pushButton_play_or_stop.doubleClicked.connect(self.on_play_or_stop_double_clicked)
        self.update_play_or_stop_button_text()

        if hasattr(self.ui, 'pushButton_show_object_location'):
            self.ui.pushButton_show_object_location.clicked.connect(self.toggle_show_object_location)
        
        if hasattr(self.ui, 'pushButton_make_video_gif'):
            self.ui.pushButton_make_video_gif.clicked.connect(self.make_video_gif)

        self.ui.slider_videoframe.valueChanged.connect(self.getslidervalue)
        self.range_slider.valueChanged.connect(self.on_range_slider_changed)
        
        if self.USE_SECONDARY_SLIDER:
            self.secondary_slider.valueChanged.connect(self.on_secondary_slider_changed)

    def update_video_info(self):
        """更新視訊資訊 - 必須由子類別實作"""
        raise NotImplementedError("Subclasses must implement update_video_info()")

    def change_speed(self, speed_label):
        """改變播放速度"""
        self.current_speed_interval = self.speed_map.get(speed_label, 1)
        # 重置 0.5 倍速累加器
        self._half_speed_accumulator = 0.0

    def reloaded_track_dict(self):
        """重新載入 track dictionary"""
        with open(f'{self.data_path}/{self.DATA_ID}_track_frame_dict.json', 'r', encoding='utf-8') as f:
            self.track_dict = orjson.loads(f.read())

    def toggle_show_object_location(self):
        """切換顯示物體位置標記"""
        self.show_object_location_trigger = not self.show_object_location_trigger
        self._update_label_frame(self.image_background.copy())

    def update_play_or_stop_button_text(self):
        """更新播放/停止按鈕文字"""
        if self.videoplayer_state == "play":
            self.ui.pushButton_play_or_stop.setText("Stop")
        else:
            self.ui.pushButton_play_or_stop.setText("Play")

    def remove_frames_outside_range(self):
        """移除範圍外的 frames"""
        min_frame_idx, max_frame_idx = self.range_slider.value()
        current_ego_id = self.current_ego_id
        frame_keys = sorted(list(self.track_dict[str(current_ego_id)].keys()), key=lambda x: int(x))
        keep_keys = self.overlay_frame_list[min_frame_idx:max_frame_idx+1]

        for key in frame_keys:
            if key not in keep_keys:
                del self.track_dict[str(current_ego_id)][key]

        with open(f'{self.data_path}/{self.DATA_ID}_track_frame_dict.json', "wb") as f:
            f.write(orjson.dumps(self.track_dict, option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS))

        print(f"已移除 {current_ego_id} 不在 {min_frame_idx}~{max_frame_idx} 範圍的 frame")

    def set_video_player(self):
        """設定視訊播放器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.timer_timeout_job)
        self.timer.start(self.DEFAULT_TIMER_INTERVAL)
        self.ui.label_videoframe.setScaledContents(True)

    def _update_label_frame(self, frame):
        """更新畫面 frame"""
        bytesPerline = 3 * self.image_width
        frame = self._update_label_onscreen(frame)

        min_frame_idx = self.ui.slider_videoframe.value()
        if min_frame_idx < len(self.overlay_frame_list):
            self.abs_frame_no = int(self.overlay_frame_list[min_frame_idx])
        else:
            self.abs_frame_no = 0

        cv2.putText(
            frame, f"Frame: {self.abs_frame_no + 1}",
            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
            (255, 255, 255), 2, cv2.LINE_AA
        )

        qimg = QImage(frame, self.image_width, self.image_height, bytesPerline, QImage.Format.Format_RGB888).rgbSwapped()
        self.qpixmap = QPixmap.fromImage(qimg)
        self.ui.label_videoframe.setPixmap(self.qpixmap)
        self.ui.label_videoframe.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)

    def _update_label_onscreen(self, frame):
        """更新畫面上的標籤 - 使用快取機制"""
        current_ego_id = self.current_ego_id
        current_other_actor_id = self.current_other_actor_id
        cache_key = (
            str(current_ego_id),
            str(current_other_actor_id),
            self.current_frame_no,
            self.show_object_location_trigger
        )

        if cache_key in self._onscreen_render_cache:
            return self._onscreen_render_cache[cache_key].copy()

        if len(self.overlay_frame_list) <= self.current_frame_no:
            self.current_frame_no = 0
            self.ui.slider_videoframe.setValue(self.current_frame_no)

        if not self.overlay_frame_list:
            return frame

        current_frame = self.overlay_frame_list[self.current_frame_no]

        # 繪製 ego bbox
        try:
            row = self.track_dict[current_ego_id][current_frame][0]
            x = row['xCenter'] / ortho_px_to_meter
            y = -row['yCenter'] / ortho_px_to_meter
            heading = row['heading']
            width = row['width'] / ortho_px_to_meter
            length = row['length'] / ortho_px_to_meter
            draw_rotated_bbox(frame, x, y, width, length, heading)
        except:
            pass

        # 多 agent 顯示（如果 current_agent_ids 有內容就畫）
        if hasattr(self, "current_agent_ids") and self.current_agent_ids:
            for aid in self.current_agent_ids:
                try:
                    row = self.track_dict[aid][current_frame][0]
                    x = row['xCenter'] / ortho_px_to_meter
                    y = -row['yCenter'] / ortho_px_to_meter
                    heading = row['heading']
                    width = row['width'] / ortho_px_to_meter
                    length = row['length'] / ortho_px_to_meter
                    actor_class = self.trackid_class.get(str(aid), "unknown")
                    color = (255, 0, 0) if actor_class != "pedestrian" else (255, 0, 255)
                    if actor_class == "pedestrian":
                        cv2.circle(frame, (int(x), int(y)), 15, color, thickness=-1)
                    else:
                        draw_rotated_bbox(frame, x, y, width, length, heading, color=color)
                except:
                    pass

        # 繪製 other actor bbox
        other_actor_class = self.trackid_class.get(str(current_other_actor_id), "unknown")
        try:
            row = self.track_dict[current_other_actor_id][current_frame][0]
            x = row['xCenter'] / ortho_px_to_meter
            y = -row['yCenter'] / ortho_px_to_meter
            heading = row['heading']
            width = row['width'] / ortho_px_to_meter
            length = row['length'] / ortho_px_to_meter

            if other_actor_class == "pedestrian":
                cv2.circle(frame, (int(x), int(y)), 15, (255, 0, 0), thickness=-1)
            else:
                draw_rotated_bbox(frame, x, y, width, length, heading, color=(255,0,0))

            if self.show_object_location_trigger:
                cv2.circle(frame, (int(x), int(y)), 80, (0, 0, 255), thickness=10)
        except:
            pass

        self._onscreen_render_cache[cache_key] = frame.copy()
        return frame

    def play(self):
        """播放視訊"""
        self.videoplayer_state = "play"
        self.timer.start(self.DEFAULT_TIMER_INTERVAL)
        self.update_play_or_stop_button_text()

    def stop(self):
        """停止視訊"""
        self.videoplayer_state = "stop"
        self.timer.stop()
        self.update_play_or_stop_button_text()

    def toggle_play_or_stop(self):
        """切換播放/停止"""
        if self.videoplayer_state == "play":
            self.stop()
        else:
            self.play()

    def on_play_or_stop_double_clicked(self):
        """雙擊時重置到第一幀並播放"""
        self.current_frame_no = 0
        self.setslidervalue(0)
        self.play()

    def on_range_slider_changed(self, value):
        """range slider 改變時的處理"""
        min_frame, max_frame = value
        if self.current_frame_no < min_frame:
            self.setslidervalue(min_frame)
        elif self.current_frame_no > max_frame:
            self.setslidervalue(max_frame)

    def on_secondary_slider_changed(self, value):
        """secondary slider 改變時的處理"""
        if self._slider_updating:
            return
        try:
            self._slider_updating = True
            min_frame, max_frame = self.range_slider.value()

            if value < min_frame:
                min_frame = value
            if value > max_frame:
                max_frame = value

            self.range_slider.setValue((min_frame, max_frame))

            if self.ui.slider_videoframe.value() != value:
                self.ui.slider_videoframe.setValue(value)

            self.current_frame_no = value
            self._update_label_frame(self.image_background.copy())
            self.ui.slider_videoframe_label.setText(f"{self.current_frame_no + 1} / {self.total_frame_count}")
        finally:
            self._slider_updating = False

    def timer_timeout_job(self):
        """計時器超時處理 - 支援 0.5 倍速"""
        frame = self.image_background.copy()
        self._update_label_frame(frame)
        min_frame, max_frame = self.range_slider.value()

        if self.videoplayer_state == "stop":
            self.videoplayer_state = "play"
            self.update_play_or_stop_button_text()

        # 計算步進值
        speed = self.current_speed_interval
        
        if speed < 1:
            # 0.5 倍速：使用累加器
            self._half_speed_accumulator += speed
            if self._half_speed_accumulator >= 1.0:
                step = int(self._half_speed_accumulator)
                self._half_speed_accumulator -= step
            else:
                return  # 累加不足 1，不前進
        elif speed == 1:
            step = 1
        elif speed == 2:
            step = 2
        elif speed == 5:
            step = 5
        elif speed == 10:
            step = 10
        else:
            step = int(speed)

        if self.current_frame_no > max_frame:
            self.current_frame_no = max_frame
            self.videoplayer_state = "stop"
            self.update_play_or_stop_button_text()
        else:
            self.current_frame_no += step
        self.setslidervalue(self.current_frame_no)

    def getslidervalue(self, value=None):
        """取得 slider 值"""
        if self._slider_updating:
            return
        try:
            self._slider_updating = True
            min_frame, max_frame = self.range_slider.value()
            value = self.ui.slider_videoframe.value()

            if value < min_frame:
                value = min_frame
                if self.ui.slider_videoframe.value() != value:
                    self.ui.slider_videoframe.setValue(value)
            elif value > max_frame:
                value = max_frame
                if self.ui.slider_videoframe.value() != value:
                    self.ui.slider_videoframe.setValue(value)

            self.current_frame_no = value
            
            if self.USE_SECONDARY_SLIDER:
                self.secondary_slider.setValue(value)
            
            self._update_label_frame(self.image_background.copy())
            self.ui.slider_videoframe_label.setText(f"{self.current_frame_no + 1} / {self.total_frame_count}")
        finally:
            self._slider_updating = False

    def setslidervalue(self, value):
        """設定 slider 值"""
        if self._slider_updating:
            min_frame, max_frame = self.range_slider.value()
            self.current_frame_no = max(min_frame, min(max_frame, value))
            if self.USE_SECONDARY_SLIDER:
                self.secondary_slider.setValue(self.current_frame_no)
            self._update_label_frame(self.image_background.copy())
            self.ui.slider_videoframe_label.setText(f"{self.current_frame_no + 1} / {self.total_frame_count}")
            return

        try:
            self._slider_updating = True
            min_frame, max_frame = self.range_slider.value()
            value = max(min_frame, min(max_frame, value))
            self.current_frame_no = value

            if self.ui.slider_videoframe.value() != value:
                self.ui.slider_videoframe.setValue(value)
            
            if self.USE_SECONDARY_SLIDER and self.secondary_slider.value() != value:
                self.secondary_slider.setValue(value)

            self._update_label_frame(self.image_background.copy())
            self.ui.slider_videoframe_label.setText(f"{self.current_frame_no + 1} / {self.total_frame_count}")
        finally:
            self._slider_updating = False

    def Next_frame(self):
        """下一幀"""
        current_frame_no = self.ui.slider_videoframe.value()
        self.ui.slider_videoframe.setValue(current_frame_no + 1)

    def Prev_frame(self):
        """上一幀"""
        current_frame_no = self.ui.slider_videoframe.value()
        if current_frame_no - 1 >= 0:
            self.ui.slider_videoframe.setValue(current_frame_no - 1)

    def make_video_gif(self):
        """製作視訊/GIF"""
        msg = QMessageBox(None)
        msg.setWindowTitle("選擇輸出格式")
        msg.setText("請選擇要輸出的影片格式：")
        mp4_btn = msg.addButton("MP4", QMessageBox.ButtonRole.AcceptRole)
        gif_btn = msg.addButton("GIF", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg.addButton("Return", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == mp4_btn:
            self.export_video("mp4")
        elif msg.clickedButton() == gif_btn:
            self.export_video("gif")

    def get_export_ids(self):
        """取得匯出用的 ego_id 和 actor_id - 子類別可覆寫"""
        return self.current_ego_id, self.current_other_actor_id

    def export_video(self, mode):
        """匯出視訊"""
        ego_id, actor_id = self.get_export_ids()

        if mode == "mp4":
            file_filter = "MP4 files (*.mp4)"
            default_ext = ".mp4"
        else:
            file_filter = "GIF files (*.gif)"
            default_ext = ".gif"
        default_name = f"{ego_id}_{actor_id}{default_ext}"

        save_path, _ = QFileDialog.getSaveFileName(
            None, "儲存檔案", default_name, file_filter
        )
        if not save_path:
            return
        if not save_path.endswith(default_ext):
            save_path += default_ext

        frames = []
        for idx in range(self.range_slider.value()[0], self.range_slider.value()[1] + 1):
            frame = self.image_background.copy()
            frame = self.export_frame(frame, idx)
            frames.append(frame[..., ::-1])

        if mode == "gif":
            imageio.mimsave(save_path, frames, fps=30)
        else:
            h, w, _ = frames[0].shape
            out = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), 30, (w, h))
            for frame in frames:
                out.write(frame[..., ::-1])
            out.release()

        QMessageBox.information(None, "完成", f"已儲存 {mode.upper()} 檔案：\n{save_path}")

    def export_frame(self, frame, frame_no):
        """匯出單一 frame"""
        current_frame = self.overlay_frame_list[frame_no]
        current_ego_id = self.current_ego_id
        current_other_actor_id = self.current_other_actor_id

        try:
            row = self.track_dict[current_ego_id][current_frame][0]
            x = row['xCenter'] / ortho_px_to_meter
            y = -row['yCenter'] / ortho_px_to_meter
            heading = row['heading']
            width = row['width'] / ortho_px_to_meter
            length = row['length'] / ortho_px_to_meter
            draw_rotated_bbox(frame, x, y, width, length, heading)
        except:
            pass

        other_actor_class = self.trackid_class.get(str(current_other_actor_id), "unknown")
        try:
            row = self.track_dict[current_other_actor_id][current_frame][0]
            x = row['xCenter'] / ortho_px_to_meter
            y = -row['yCenter'] / ortho_px_to_meter
            heading = row['heading']
            width = row['width'] / ortho_px_to_meter
            length = row['length'] / ortho_px_to_meter

            if other_actor_class == "pedestrian":
                cv2.circle(frame, (int(x), int(y)), 15, (255, 0, 0), thickness=-1)
            else:
                draw_rotated_bbox(frame, x, y, width, length, heading, color=(255,0,0))
        except:
            pass

        return frame
