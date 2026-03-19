#!/bin/bash

# 切換到這個檔案所在的資料夾
cd "$(dirname "$0")"

echo "========================================="
echo " 工程材料碳足跡計算工具"
echo "========================================="
echo ""

# 檢查 Python 是否安裝
if ! command -v python3 &> /dev/null; then
    osascript -e 'display alert "找不到 Python 3" message "請先安裝 Python 3，前往 https://www.python.org 下載。" as critical'
    exit 1
fi

# 第一次執行時安裝套件
if [ ! -f ".installed" ]; then
    echo "首次執行，安裝必要套件（約需 1-2 分鐘）..."
    pip3 install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        osascript -e 'display alert "套件安裝失敗" message "請確認網路連線後再試一次。" as critical'
        exit 1
    fi
    touch .installed
    echo "套件安裝完成！"
fi

echo "啟動中，請稍候..."
echo "（關閉此視窗即可停止程式）"
echo ""

# 啟動 Streamlit
python3 -m streamlit run app.py \
    --server.headless true \
    --browser.gatherUsageStats false \
    --server.port 8501

