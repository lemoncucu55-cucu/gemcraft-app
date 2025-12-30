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

# 2. 自動建立檔案功能 (防止因為找不到檔案而轉圈圈)
def init_files():
    if not os.path.exists(DEFAULT_CSV_FILE):
        pd.DataFrame(columns=COLUMNS).to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    if not os.path.exists(DESIGN_SALES_FILE):
        pd.DataFrame(columns=DESIGN_COLUMNS).to_csv(DESIGN_SALES_FILE, index=False, encoding='utf-8-sig')

init_files()

# 3. 初始化 Session State (安全載入)
def load_data(file, cols):
    try:
        df = pd.read_csv(file, encoding='utf-8-sig')
        for c in cols:
            if c not in df.columns: df[c] = 0
        return df[cols]
    except:
        return pd.DataFrame(columns=cols)

if 'inventory' not in st.session_state:
    st.session_state['inventory'] = load_data(DEFAULT_CSV_FILE, COLUMNS)
if 'design_sales' not in st.session_state:
    st.session_state['design_sales'] = load_data(DESIGN_SALES_FILE, DESIGN_COLUMNS)
if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 系統恢復", layout="wide")

# 4. 主介面
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    admin_mode = (pwd == "admin123")
    page = st.radio("前往", ["📦 庫存管理", "🧮 設計與成本計算"])

if page == "📦 庫存管理":
    st.header("📦 庫存管理")
    # 建立測試資料按鈕 (方便您快速恢復)
    if st.button("➕ 建立一筆測試材料"):
        new_data = {
            '編號': 'TEST01', '倉庫': 'Imeng', '分類': '天然石', '名稱': '波斯瑪瑙',
            '寬度mm': 6.0, '長度mm': 0, '形狀': '圓珠', '五行': '土', 
            '進貨總價': 100, '進貨數量(顆)': 50, '進貨日期': date.today(), 
            '進貨廠商': '自用', '庫存(顆)': 50, '單顆成本': 2.0
        }
        st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_data])], ignore_index=True)
        st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
        st.success("測試資料已建立！")
        st.rerun()
    
    st.dataframe(st.session_state['inventory'], use_container_width=True)

elif page == "🧮 設計與成本計算":
    st.header("🧮 作品設計")
    
    inv = st.session_state['inventory']
    if inv.empty:
        st.warning("目前庫存為空，請先在「庫存管理」建立商品。")
    else:
        # 材料選擇
        inv['label'] = inv.apply(lambda r: f"[{r['倉庫']}] {r['名稱']} ({r['寬度mm']}mm) | 存:{int(r['庫存(顆)'])}", axis=1)
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv['label'].tolist())
        qty = c2.number_input("數量", min_value=1, value=1)
        
        if st.button("📥 加入清單"):
            item = inv[inv['label'] == pick].iloc[0]
            st.session_state['current_design'].append({
                '編號': item['編號'], '名稱': item['名稱'], '數量': qty, '單價': float(item['單顆成本']), '小計': float(item['單顆成本']) * qty
            })
            st.rerun()

    # 顯示工資輸入框
    if st.session_state['current_design']:
        df_curr = pd.DataFrame(st.session_state['current_design'])
        st.table(df_curr[['名稱', '數量']])
        mat_sum = df_curr['小計'].sum()
        
        st.divider()
        st.subheader("💰 額外成本紀錄")
        ca, cb, cc = st.columns(3)
        labor = ca.number_input("🛠️ 工資 (元)", min_value=0, value=0)
        misc = cb.number_input("📦 雜支 (元)", min_value=0, value=0)
        ship = cc.number_input("🚚 運費 (元)", min_value=0, value=0)
        
        total_cost = mat_sum + labor + misc + ship
        
        if admin_mode:
            st.metric("作品總成本", f"${total_cost:.1f}")
            st.success(f"建議售價: x3=${round(total_cost*3)} | x5=${round(total_cost*5)}")
