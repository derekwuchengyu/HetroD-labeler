import sys
import argparse
from PyQt6.QtWidgets import QApplication

def main():
    parser = argparse.ArgumentParser(description='Label Tool with different UI options')
    parser.add_argument('--ui', 
                        choices=['default', 'ipad'], 
                        default='default',
                        help='Choose UI layout: default or ipad')
    parser.add_argument('--data_id','-id',
                        type=str,
                        default='00',
                        help='Specify the DATA_ID to use')
    
    args = parser.parse_args()
    
    # 根據參數選擇 UI
    if args.ui == 'ipad':
        from UI_ipad_mini import Ui_MainWindow
    else:
        from UI import Ui_MainWindow
    
    # 建立應用程式
    app = QApplication(sys.argv)
    
    # 建立主視窗，傳入對應的 UI 類別
    from controller import MainWindow_controller
    window = MainWindow_controller(Ui_MainWindow, DATA_ID=args.data_id)
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
