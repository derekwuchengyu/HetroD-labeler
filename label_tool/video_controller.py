import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from VideoController import BaseVideoController
import orjson


class video_controller(BaseVideoController):
    """Label tool 專用的視訊控制器"""
    
    USE_SECONDARY_SLIDER = True
    BACKGROUND_FILENAME_TEMPLATE = "{DATA_ID}_background.png"

    def __init__(self, data_path, ui, DATA_ID):
        super().__init__(data_path, ui, DATA_ID)


    def update_video_info(self):
        """更新視訊資訊 - label_tool 專用邏輯"""
        self.current_ego_id = self.ui.comboBox_ego_id.currentText()
        if not self.current_ego_id or self.current_ego_id not in self.track_dict:
            return

        self.current_ego_id_frame_list = list(self.track_dict[str(self.current_ego_id)].keys())
        self.current_other_actor_id = self.ui.comboBox_other_actor_id.currentText()
        
        if not self.current_other_actor_id or self.current_other_actor_id not in self.track_dict:
            return

        self.current_other_actor_id_frame_list = list(self.track_dict[str(self.current_other_actor_id)].keys())

        overlay_frames = sorted(
            set(self.current_ego_id_frame_list) & set(self.current_other_actor_id_frame_list),
            key=lambda x: int(x)
        )

        if overlay_frames:
            offset = 600
            min_overlay = int(overlay_frames[0])
            max_overlay = int(overlay_frames[-1])
            min_target = max(0, min_overlay - offset)
            max_target = max_overlay + offset
            self.overlay_frame_list = [
                f for f in sorted(self.current_ego_id_frame_list, key=lambda x: int(x))
                if min_target <= int(f) <= max_target
            ]

        self.total_frame_count = len(self.overlay_frame_list)

        self.ui.slider_videoframe.setRange(0, self.total_frame_count - 1)
        self.range_slider.setMinimum(0)
        self.range_slider.setMaximum(self.total_frame_count - 1)
        self.range_slider.setValue((0, self.total_frame_count - 1))

        # 根據 labeled_scenarios.json 設定預設 range
        labeled_path = os.path.join(self.data_path, f"{self.DATA_ID}_labeled_scenarios.json")
        key = f"{self.current_ego_id}_{self.current_other_actor_id}"
        min_idx = 0
        max_idx = self.total_frame_count - 1
        
        if os.path.exists(labeled_path):
            try:
                with open(labeled_path, "r", encoding="utf-8") as f:
                    labeled_dict = orjson.loads(f.read())
                info = labeled_dict.get(key)
                if info and "min_frame" in info and "max_frame" in info:
                    frame_to_idx = {int(f): idx for idx, f in enumerate(self.overlay_frame_list)}
                    min_frame = info["min_frame"]
                    max_frame = info["max_frame"]
                    min_idx = frame_to_idx.get(int(min_frame), min_idx)
                    max_idx = frame_to_idx.get(int(max_frame), max_idx)
                    self.range_slider.setValue((min_idx, max_idx))
                    self.current_frame_no = min_idx
                    self.ui.slider_videoframe.setValue(self.current_frame_no)
            except Exception:
                pass
        else:
            self.current_frame_no = 0
            self.ui.slider_videoframe.setValue(self.current_frame_no)

        frame = self.image_background.copy()
        self._onscreen_render_cache = {}
        self._update_label_frame(frame)
        self.update_range_slider_bar()

    def update_range_slider_bar(self):
        """更新 range_slider 的 bar 標記"""
        ego_id = self.ui.comboBox_ego_id.currentText()
        labeled_path = os.path.join(self.data_path, f"{self.DATA_ID}_labeled_scenarios.json")
        
        if not os.path.exists(labeled_path):
            if hasattr(self.range_slider, 'setSpanStyle'):
                self.range_slider.setSpanStyle([])
            return

        try:
            with open(labeled_path, "r", encoding="utf-8") as f:
                labeled_dict = orjson.loads(f.read())
        except Exception:
            if hasattr(self.range_slider, 'setSpanStyle'):
                self.range_slider.setSpanStyle([])
            return

        frame_to_idx = {int(f): idx for idx, f in enumerate(self.overlay_frame_list)}
        bar_ranges = []
        
        for key, info in labeled_dict.items():
            if not isinstance(info, dict):
                continue
            min_frame = info.get("min_frame")
            max_frame = info.get("max_frame")
            if min_frame is None or max_frame is None:
                continue
            if info.get("ego_id") != ego_id:
                continue
            min_idx = frame_to_idx.get(int(min_frame))
            max_idx = frame_to_idx.get(int(max_frame))
            if min_idx is not None and max_idx is not None:
                bar_ranges.append((min_idx, max_idx))

        if hasattr(self.range_slider, "setSpanStyle"):
            self.range_slider.setSpanStyle(bar_ranges)
        elif hasattr(self.range_slider, "setSpan"):
            self.range_slider.setSpan(bar_ranges)

    def get_export_ids(self):
        """取得匯出用的 ID"""
        return self.ui.comboBox_ego_id.currentText(), self.ui.comboBox_other_actor_id.currentText()