import json
from datetime import datetime
from pathlib import Path

class SpecialScenarioHandler:
    def __init__(self, output_dir="./special_scenarios"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.filename = self.output_dir / "special_scenarios.json"
    
    def record_special_scenario(self, video_name, frame_number, actor_id, label_info=None):
        """
        記錄特別scenario到檔案
        
        Args:
            video_name: 視頻名稱
            frame_number: 當前幀號
            actor_id: Actor ID
            label_info: 額外的標籤資訊
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "video": video_name,
            "frame": frame_number,
            "actor_id": actor_id,
            "label_info": label_info
        }
        
        # 讀取現有資料
        records = []
        if self.filename.exists():
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            except:
                records = []
        
        # 新增記錄
        records.append(record)
        
        # 寫入檔案
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        print(f"已記錄特別scenario: {video_name} - Frame {frame_number}")
