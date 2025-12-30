import streamlit as st
import pandas as pd
import os
import time
from datetime import date, datetime

# 1. 規格定義
COLUMNS = ['編號', '倉庫', '分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本']
DESIGN_COLUMNS = ['售出時間', '作品名稱', '材料明細', '材料小計', '工資', '雜支', '運費', '總成本', '建議售價x3', '建議售價x5', '備註']

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv'

# 2. 自動建立檔案功能
def init_files():
    # 如果找不到庫存檔，建立一個空的
    if not os.path.exists(DEFAULT_CSV_FILE):
        pd.DataFrame(columns=COLUMNS).to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    # 如果找不到銷售紀錄檔，建立一個空的
    if not os.path.exists(DESIGN_SALES_FILE):
        pd.DataFrame(columns=DESIGN_COLUMNS).to_csv(DESIGN_SALES_FILE, index=False, encoding='utf-8-sig')

init_files()

# 3. 初始化 Session State
if 'inventory' not in st.session_state:
    st.session_state['inventory'] = pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig')
if 'design_sales' not in st.session_state:
    st.session_state['design_sales'] = pd.read_csv(DESIGN_SALES_FILE, encoding='utf-8-sig')
if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 系統恢復", layout="wide")

# 4. 主介面
with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    admin_mode = (pwd == "admin123")
    page = st.radio("前往", ["📦 庫存管理", "🧮 設計與成本計算"])

if page == "📦 庫存管理":
    st.header("📦 庫存管理")
    st.info("目前為空白資料庫，請使用下方功能建立新商品。")
    # 這裡可以放您原本建立新商品的表格代碼...
    st.dataframe(st.session_state['inventory'])

elif page == "🧮 設計與成本計算":
    st.header("🧮 設計與成本計算")
    # 此處會顯示工資、雜支、運費欄位
    if st.session_state['inventory'].empty:
        st.warning("目前庫存為空，請先前往庫存管理建立商品。")
    else:
        st.write("請開始您的設計...")
        # 顯示工資欄位的代碼...
