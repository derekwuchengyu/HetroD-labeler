#!/bin/bash

# 使用 readlink 獲取腳本絕對路徑 (相容 sh/bash)
SCRIPT_PATH=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")

# 定義專案根目錄 (script 的上一層)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

cd "$PROJECT_ROOT"/label_tool
python -m PyQt6.uic.pyuic label.ui -o UI.py

cd "$PROJECT_ROOT"/refine_tool
python -m PyQt6.uic.pyuic label.ui -o UI.py

cd "$PROJECT_ROOT"/visual_tool
python -m PyQt6.uic.pyuic label.ui -o UI.py