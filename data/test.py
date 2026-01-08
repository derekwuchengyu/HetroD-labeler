from datetime import datetime

def parse_time_recording(file_path):
    """解析時間記錄檔案，計算總花費時間和按下次數"""
    
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    sessions = []  # 儲存每個工作階段
    current_session = None
    total_press_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('啟動時間：'):
            # 如果有前一個工作階段，先處理它
            if current_session:
                sessions.append(current_session)
            
            # 開始新的工作階段
            time_str = line.replace('啟動時間：', '')
            start_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            current_session = {
                'start_time': start_time,
                'press_times': [],
                'press_count': 0
            }
            
        elif line.startswith('按下時間：') and current_session:
            time_str = line.replace('按下時間：', '')
            press_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            current_session['press_times'].append(press_time)
            current_session['press_count'] += 1
            total_press_count += 1
    
    # 處理最後一個工作階段
    if current_session:
        sessions.append(current_session)
    
    # 計算每個工作階段的時間
    total_duration = 0
    session_details = []
    
    for i, session in enumerate(sessions, 1):
        if session['press_times']:
            # 從啟動時間到最後一個按下時間
            last_press_time = max(session['press_times'])
            duration = (last_press_time - session['start_time']).total_seconds()
        else:
            # 如果沒有按下時間，持續時間為0
            duration = 0
        
        total_duration += duration
        session_details.append({
            'session': i,
            'start_time': session['start_time'],
            'duration_seconds': duration,
            'duration_minutes': duration / 60,
            'press_count': session['press_count']
        })
    
    return {
        'sessions': session_details,
        'total_duration_seconds': total_duration,
        'total_duration_minutes': total_duration / 60,
        'total_duration_hours': total_duration / 3600,
        'total_press_count': total_press_count
    }

def format_duration(seconds):
    """將秒數格式化為時分秒"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}小時 {minutes}分鐘 {secs}秒"

# 主程式
if __name__ == "__main__":
    # file_path = "label_time_recording.txt"
    file_path = "label_time_recording_730_500.txt"
    
    try:
        result = parse_time_recording(file_path)
        
        print("=" * 50)
        print("時間記錄分析結果")
        print("=" * 50)
        
        print(f"\n總工作階段數：{len(result['sessions'])}")
        print(f"總按下次數：{result['total_press_count']}")
        print(f"總花費時間：{format_duration(result['total_duration_seconds'])}")
        print(f"總花費時間（小時）：{result['total_duration_hours']:.2f} 小時")
        
        # print("\n各工作階段詳細資訊：")
        # print("-" * 50)
        
        # for session in result['sessions']:
        #     print(f"階段 {session['session']}:")
        #     print(f"  開始時間：{session['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        #     print(f"  持續時間：{format_duration(session['duration_seconds'])}")
        #     print(f"  按下次數：{session['press_count']}")
        #     print()
        
    except FileNotFoundError:
        print(f"找不到檔案：{file_path}")
    except Exception as e:
        print(f"處理檔案時發生錯誤：{e}")