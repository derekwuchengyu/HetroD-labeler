import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from VideoController import BaseVideoController
import orjson


class video_controller(BaseVideoController):
    """Refine tool 專用的視訊控制器"""
    
    USE_SECONDARY_SLIDER = True
    BACKGROUND_FILENAME_TEMPLATE = "00_background.png"  # refine_tool 使用固定的背景檔名

    def __init__(self, data_path, ui, DATA_ID):
        super().__init__(data_path, ui, DATA_ID)

    def get_speed_map(self):
        """Refine tool 的速度選單"""
        return {
            "20": 20,
            "10": 10,
            "5": 5,
            "3": 3,
            "2": 2,
            "1": 1,
        }

    def update_video_info(self):
        """更新視訊資訊 - refine_tool 專用邏輯"""
        id_pair = self.ui.comboBox_ego_id.currentText()
        if not id_pair or "_" not in id_pair:
            return
            
        self.current_ego_id = id_pair.split("_")[0]
        self.current_other_actor_id = id_pair.split("_")[1]

        # 讀取 labeled frame info
        save_path = os.path.join(self.data_path, f"{self.DATA_ID}_labeled_scenarios.json")
        labeled_dict = {}
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                labeled_dict = orjson.loads(f.read())

        min_frame_in_all = labeled_dict.get(id_pair, {}).get("min_frame", None)
        max_frame_in_all = labeled_dict.get(id_pair, {}).get("max_frame", None)

        if self.current_ego_id not in self.track_dict:
            return
        if self.current_other_actor_id not in self.track_dict:
            return

        self.current_ego_id_frame_list = list(self.track_dict[str(self.current_ego_id)].keys())
        self.current_other_actor_id_frame_list = list(self.track_dict[str(self.current_other_actor_id)].keys())

        overlay_frames = sorted(
            set(self.current_ego_id_frame_list) & set(self.current_other_actor_id_frame_list),
            key=lambda x: int(x)
        )

        if not overlay_frames:
            return

        offset = 1200
        min_overlay = int(overlay_frames[0])
        max_overlay = int(overlay_frames[-1])
        min_target = max(0, min_overlay - offset)
        max_target = max_overlay + offset

        # 檢查是否有儲存的 ego frame range
        range_path = os.path.join(self.data_path, f"{self.DATA_ID}_ego_frame_range.json")
        if os.path.exists(range_path):
            with open(range_path, "r", encoding="utf-8") as f:
                try:
                    content = orjson.loads(f.read())
                except Exception:
                    content = {}
            if id_pair in content:
                print(f"Loaded ego frame range for {id_pair}: {content[id_pair]}")
                min_target = content[id_pair].get("min_frame", min_target)
                max_target = content[id_pair].get("max_frame", max_target)

        self.overlay_frame_list = [
            f for f in sorted(self.current_ego_id_frame_list, key=lambda x: int(x))
            if min_target <= int(f) <= max_target
        ]

        self.total_frame_count = len(self.overlay_frame_list)

        self.ui.slider_videoframe.setRange(0, self.total_frame_count - 1)
        self.secondary_slider.setRange(0, self.total_frame_count - 1)
        self.range_slider.setMinimum(0)
        self.range_slider.setMaximum(self.total_frame_count - 1)
        self.range_slider.setValue((0, self.total_frame_count - 1))

        # 設定初始位置
        if min_frame_in_all is not None and max_frame_in_all is not None:
            try:
                min_idx = self.overlay_frame_list.index(str(min_frame_in_all))
                max_idx = self.overlay_frame_list.index(str(max_frame_in_all))
                self.ui.slider_videoframe.setValue(min_idx)
                self.secondary_slider.setValue(min_idx)
                self.range_slider.setValue((min_idx, max_idx))
                self.current_frame_no = min_idx
            except ValueError:
                self.current_frame_no = 0
                self.ui.slider_videoframe.setValue(0)
                self.secondary_slider.setValue(0)
        else:
            self.current_frame_no = 0
            self.ui.slider_videoframe.setValue(0)
            self.secondary_slider.setValue(0)

        frame = self.image_background.copy()
        self._onscreen_render_cache = {}
        self._update_label_frame(frame)

    def get_export_ids(self):
        """取得匯出用的 ID - refine_tool 從 id_pair 解析"""
        id_pair = self.ui.comboBox_ego_id.currentText()
        if "_" in id_pair:
            return id_pair.split("_")[0], id_pair.split("_")[1]
        return "", ""

    def timer_timeout_job(self):
        """refine_tool 特有的 timer 邏輯"""
        frame = self.image_background.copy()
        self._update_label_frame(frame)
        min_frame, max_frame = self.range_slider.value()

        if self.videoplayer_state == "stop":
            self.videoplayer_state = "play"
            self.update_play_or_stop_button_text()

        # 計算步進值 - 支援 0.5 倍速
        speed = self.current_speed_interval
        
        if speed < 1:
            self._half_speed_accumulator += speed
            if self._half_speed_accumulator >= 1.0:
                step = int(self._half_speed_accumulator)
                self._half_speed_accumulator -= step
            else:
                return
        else:
            step = int(speed)

        if self.current_frame_no + step > max_frame:
            self.current_frame_no = max_frame
            self.videoplayer_state = "stop"
            self.update_play_or_stop_button_text()
        else:
            self.current_frame_no += step
            self.setslidervalue(self.current_frame_no)