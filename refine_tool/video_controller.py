from PyQt6 import QtCore 
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt
import numpy as np
import cv2 
import ujson
import os 
from superqt import QRangeSlider
from PyQt6.QtWidgets import QMessageBox, QFileDialog
import imageio


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
    # cv2.polylines(img, [box], isClosed=True, color=color, thickness=thickness)

    cv2.fillPoly(img, [box], color=color)

ortho_px_to_meter = 0.0499967249445942


class video_controller(object):
    def __init__(self, data_path,  ui):

        self.data_path = data_path
        self.ui = ui

        self.show_object_location_trigger = False  # 預設不顯示

        self._onscreen_render_cache = {}

        # 設定速度選單
        self.speed_map = {
            "6": 6,    
            "5": 5,    
            "4": 4,     
            "3": 3,    
            "2": 2,   
            "1": 1    
        }
        self.ui.comboBox_speed.clear()
        self.ui.comboBox_speed.addItems(list(self.speed_map.keys()))
        self.ui.comboBox_speed.setCurrentText("1")

        self.ui.comboBox_speed.currentTextChanged.connect(self.change_speed)
        
        self.current_speed_interval = self.speed_map["1"]



        # 動態新增 QRangeSlider
        self.range_slider = QRangeSlider(Qt.Horizontal)
        self.ui.verticalLayout.addWidget(self.range_slider)


        # load brackground image 
        self.image_background = cv2.imread(f'{self.data_path}/00_background.png')
        self.image_width = self.image_background.shape[1]
        self.image_height = self.image_background.shape[0]

        # load trackid to class 
        with open(f'{self.data_path}/trackid_class.json', 'r', encoding='utf-8') as f:
            self.trackid_class = ujson.load(f)

        # load the track dict 
        with open(f'{self.data_path}/track_frame_dict.json', 'r', encoding='utf-8') as f:
            self.track_dict = ujson.load(f)

        self.current_frame_no = 0
        self.videoplayer_state = "play"
        
        
        self.update_video_info()
        self.set_video_player()
        self.counter = 0

        self.route_index = 0

        self.ui.pushButton_play_or_stop.clicked.connect(self.toggle_play_or_stop)
        self.update_play_or_stop_button_text()
        
        self.ui.pushButton_show_object_location.clicked.connect(self.toggle_show_object_location)

        # connect button for video/gif export
        self.ui.pushButton_make_video_gif.clicked.connect(self.make_video_gif)


        self.ui.slider_videoframe.valueChanged.connect(self.getslidervalue)
        self.range_slider.valueChanged.connect(self.on_range_slider_changed)

        # 防止 setValue/valueChanged 互相遞迴的 reentrancy flag
        self._slider_updating = False

    def change_speed(self, speed_label):
        # print(speed_label)
        self.current_speed_interval = self.speed_map.get(speed_label, 30)
        

    def reloaded_track_dict(self):
        with open(f'{self.data_path}/track_frame_dict.json', 'r', encoding='utf-8') as f:
            self.track_dict = ujson.load(f)
    
    def toggle_show_object_location(self):
        self.show_object_location_trigger = not self.show_object_location_trigger
        self.__update_label_frame(self.image_background.copy())

    def update_play_or_stop_button_text(self):
        if self.videoplayer_state == "play":
            self.ui.pushButton_play_or_stop.setText("Stop")
        else:
            self.ui.pushButton_play_or_stop.setText("Play")

    
    def update_video_info(self):

        # get the current ego id 
        id_pair = self.ui.comboBox_ego_id.currentText()
        self.current_ego_id = id_pair.split("_")[0]
        self.current_other_actor_id = id_pair.split("_")[1]

        # get label frame info 

        save_path = os.path.join(self.data_path, "labeled_scenarios.json")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                labeled_dict = ujson.load(f)


        min_frame_in_all = labeled_dict.get(id_pair, {}).get("min_frame", None)
        max_frame_in_all = labeled_dict.get(id_pair, {}).get("max_frame", None)

        self.current_ego_id_frame_list = list(self.track_dict[str(self.current_ego_id)].keys())
        self.current_other_actor_id_frame_list = list(self.track_dict[str(self.current_other_actor_id)].keys())

        # get the overlay frame list 
        overlay_frames = sorted(
            set(self.current_ego_id_frame_list) & set(self.current_other_actor_id_frame_list),
            key=lambda x: int(x)
        )

    
        offset = 1000  # 前後各擴大多少 frame
        min_overlay = int(overlay_frames[0])
        max_overlay = int(overlay_frames[-1])
        # 擴大範圍
        min_target = min_overlay - offset  if min_overlay - offset >= 0 else 0
        max_target = max_overlay + offset
        # 取得 ego id frame list 在這個範圍內的 frame
        self.overlay_frame_list = [
            f for f in sorted(self.current_ego_id_frame_list, key=lambda x: int(x))
            if min_target <= int(f) <= max_target
        ]

        
        
        self.total_frame_count = len(self.overlay_frame_list)


        self.ui.slider_videoframe.setRange(0, self.total_frame_count-1)
        

        self.range_slider.setMinimum(0)
        self.range_slider.setMaximum(self.total_frame_count-1)
        self.range_slider.setValue((0, self.total_frame_count-1))

        
        # self.current_frame_no = 0                
        # self.ui.slider_videoframe.setValue(self.current_frame_no)  # 這行會同步滑軌


        # min_frame_in_all, max_frame_in_all
        # get relative frame index in overlay_frame_list
        
            
        min_idx = self.overlay_frame_list.index(str(min_frame_in_all))
        max_idx = self.overlay_frame_list.index(str(max_frame_in_all))
        self.ui.slider_videoframe.setValue(min_idx)
        self.range_slider.setValue((min_idx, max_idx))

        self.current_frame_no = min_idx            
        self.ui.slider_videoframe.setValue(self.current_frame_no)  # 這行會同步滑軌
    


        frame = self.image_background.copy()

        self._onscreen_render_cache = {}

        self.__update_label_frame(frame)

        
    def remove_frames_outside_range(self):
        # 取得 range_slider 範圍
        min_frame_idx, max_frame_idx = self.range_slider.value()

        # 取得 ego id 與 frame list
        current_ego_id = self.ui.comboBox_ego_id.currentText()
        frame_keys = sorted(list(self.track_dict[str(current_ego_id)].keys()), key=lambda x: int(x))

        # 要保留的 frame key
        keep_keys = frame_keys[min_frame_idx:max_frame_idx+1]

        # 移除不在範圍內的 frame
        for key in frame_keys:
            if key not in keep_keys:
                del self.track_dict[str(current_ego_id)][key]

        # 寫回檔案
        with open(f'{self.data_path}/track_frame_dict.json', 'w', encoding='utf-8') as f:
            ujson.dump(self.track_dict, f, ensure_ascii=False)

        print(f"已移除 {current_ego_id} 不在 {min_frame_idx}~{max_frame_idx} 範圍的 frame")
        
    def set_video_player(self):

        self.timer=QTimer() # init QTimer
        self.timer.timeout.connect(self.timer_timeout_job) # when timeout, do run one

        self.timer.start(30)
        
        # self.ui.label_videoframe.mousePressEvent = self.mouse_press_event # set_clicked_position
        # self.ui.label_videoframe.mouseReleaseEvent = self.mouse_release_event
        self.ui.label_videoframe.setScaledContents(True) 
        
    def __update_label_frame(self, frame):
        bytesPerline = 3 * self.image_width
        
        frame = self.__update_label_onscreen(frame)
        
        qimg = QImage(frame, self.image_width, self.image_height, bytesPerline, QImage.Format.Format_RGB888).rgbSwapped()
        self.qpixmap = QPixmap.fromImage(qimg)
        
        self.ui.label_videoframe.setPixmap(self.qpixmap)
        self.ui.label_videoframe.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter) # Center

    
    def __update_label_onscreen(self, frame):
        # 以 (ego_id, actor_id, current_frame_no, show_object_location_trigger) 當 key
        current_ego_id = self.current_ego_id
        current_other_actor_id = self.current_other_actor_id
        cache_key = (
            str(current_ego_id),
            str(current_other_actor_id),
            self.current_frame_no,
            self.show_object_location_trigger
        )

        # 如果已經 render 過，直接回傳快取內容（複製一份避免外部修改）
        if cache_key in self._onscreen_render_cache:
            return self._onscreen_render_cache[cache_key].copy()

        if len(self.overlay_frame_list) < self.current_frame_no:
            self.current_frame_no = 0                
            self.ui.slider_videoframe.setValue(self.current_frame_no)
            current_frame = self.overlay_frame_list[self.current_frame_no]
        else:
            current_frame = self.overlay_frame_list[self.current_frame_no]

        # vis ego bbox 
        row = self.track_dict[current_ego_id][current_frame][0]
        x = row['xCenter'] / ortho_px_to_meter
        y = -row['yCenter'] / ortho_px_to_meter
        heading = row['heading']
        width = row['width'] / ortho_px_to_meter
        length = row['length'] / ortho_px_to_meter
        draw_rotated_bbox(frame, x, y, width, length, heading)

        # vis other actor bbox
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
        self.videoplayer_state = "play"
        self.current_frame_no = 0
        # print(self.current_speed_interval)
        self.timer.start(30)
        self.update_play_or_stop_button_text()

    def stop(self):
        self.videoplayer_state = "stop"
        self.timer.stop()
        self.update_play_or_stop_button_text()


    def toggle_play_or_stop(self):
        if self.videoplayer_state == "play":
            self.stop()
        else:
            self.play()

    def on_range_slider_changed(self, value):
        min_frame, max_frame = value
        # 限制目前 frame 在範圍內
        if self.current_frame_no < min_frame:
            self.setslidervalue(min_frame)
        elif self.current_frame_no > max_frame:
            self.setslidervalue(max_frame)

    def timer_timeout_job(self):

        frame = self.image_background.copy()

        self.__update_label_frame(frame)
        min_frame, max_frame = self.range_slider.value()

        if self.videoplayer_state == "stop":
            self.videoplayer_state = "play"
            self.update_play_or_stop_button_text()


        if self.current_frame_no >= max_frame:
            self.videoplayer_state = "stop"
            self.update_play_or_stop_button_text()
        else:
            self.current_frame_no += self.current_speed_interval # 1
            # check range 
            if self.current_frame_no > max_frame:
                self.current_frame_no = max_frame
            self.setslidervalue(self.current_frame_no)

    def getslidervalue(self,  value=None):
        # 避免遞迴進入
        if self._slider_updating:
            return
        try:
            self._slider_updating = True
            min_frame, max_frame = self.range_slider.value()
            value = self.ui.slider_videoframe.value()
            # 限制 value 在範圍內
            if value < min_frame:
                value = min_frame
                if self.ui.slider_videoframe.value() != value:
                    self.ui.slider_videoframe.setValue(value)
            elif value > max_frame:
                value = max_frame
                if self.ui.slider_videoframe.value() != value:
                    self.ui.slider_videoframe.setValue(value)
            self.current_frame_no = value
            self.__update_label_frame(self.image_background.copy())
            self.ui.slider_videoframe_label.setText(f"{self.current_frame_no + 1} / {self.total_frame_count}")
        finally:
            self._slider_updating = False

    def setslidervalue(self, value):
        # 避免遞迴進入
        if self._slider_updating:
            # 仍需更新 current_frame_no 與顯示，但不要再次觸發 signal
            min_frame, max_frame = self.range_slider.value()
            self.current_frame_no = max(min_frame, min(max_frame, value))
            self.__update_label_frame(self.image_background.copy())
            self.ui.slider_videoframe_label.setText(f"{self.current_frame_no + 1} / {self.total_frame_count}")
            return

        try:
            self._slider_updating = True
            min_frame, max_frame = self.range_slider.value()
            value = max(min_frame, min(max_frame, value))
            self.current_frame_no = value
            # 只有當 value 不同時才 setValue，避免不必要的 signal
            if self.ui.slider_videoframe.value() != value:
                self.ui.slider_videoframe.setValue(value)
            self.__update_label_frame(self.image_background.copy())
            self.ui.slider_videoframe_label.setText(f"{self.current_frame_no + 1} / {self.total_frame_count}")
        finally:
            self._slider_updating = False



    def Next_frame(self):
        current_frame_no = self.ui.slider_videoframe.value()

        self.ui.slider_videoframe.setValue(current_frame_no+1)

    def Prev_frame(self):
        current_frame_no = self.ui.slider_videoframe.value()

        if current_frame_no-1 != 0:
            self.ui.slider_videoframe.setValue(current_frame_no-1)
            

    def make_video_gif(self):
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
        else:
            return

    def export_video(self, mode):
        # 取得 ego_id 和 actor_id
        id_pair = self.ui.comboBox_ego_id.currentText()
        ego_id = id_pair.split("_")[0]
        actor_id = id_pair.split("_")[1]    

        # 自動產生檔名
        if mode == "mp4":
            file_filter = "MP4 files (*.mp4)"
            default_ext = ".mp4"
        else:
            file_filter = "GIF files (*.gif)"
            default_ext = ".gif"
        default_name = f"{ego_id}_{actor_id}{default_ext}"

        # 選擇儲存路徑，預設檔名
        save_path, _ = QFileDialog.getSaveFileName(
            None, "儲存檔案", default_name, file_filter
        )
        if not save_path:
            return
        if not save_path.endswith(default_ext):
            save_path += default_ext

        frames = []
        for idx in range(self.range_slider.value()[0], self.range_slider.value()[1]+1):
            # print(idx)
            frame = self.image_background.copy()
            frame = self.export_frame(frame, idx)
            frames.append(frame[..., ::-1])  # BGR to RGB

        if mode == "gif":
            imageio.mimsave(save_path, frames, fps=30)
        else:
            h, w, _ = frames[0].shape
            out = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), 30, (w, h))
            for frame in frames:
                out.write(frame[..., ::-1])  # RGB to BGR
            out.release()

        QMessageBox.information(None, "完成", f"已儲存 {mode.upper()} 檔案：\n{save_path}")

    def export_frame(self, frame, frame_no):

        current_frame = self.overlay_frame_list[frame_no]

        # vis ego bbox 
        current_ego_id = self.ui.comboBox_ego_id.currentText()
        row = self.track_dict[current_ego_id][current_frame][0]
        x = row['xCenter'] / ortho_px_to_meter
        y = -row['yCenter'] / ortho_px_to_meter
        heading = row['heading']
        width = row['width'] / ortho_px_to_meter
        length = row['length'] / ortho_px_to_meter
        draw_rotated_bbox(frame, x, y, width, length, heading)

        # vis other actor bbox
        id_pair = self.ui.comboBox_ego_id.currentText()
        current_other_actor_id = id_pair.split("_")[1]

        # get the other actor class
        other_actor_class = self.trackid_class.get(str(current_other_actor_id), "unknown")
        # print(other_actor_class) # motorcycle, car, truck, bus, pedestrian, bicycle

        # print(current_other_actor_id, current_frame)

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