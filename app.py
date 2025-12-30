import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================
COLUMNS = ['編號', '倉庫', '分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本']
DESIGN_SALES_COLUMNS = ['售出時間', '作品名稱', '材料明細', '材料小計', '工資', '雜支', '運費', '總成本', '建議售價x3', '建議售價x5', '備註']
HISTORY_COLUMNS = ['紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', '廠商', '數量變動', '進貨總價', '單價']

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv'

# ==========================================
# 2. 核心函式
# ==========================================
def save_data(df, filename):
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    except:
        st.error(f"儲存 {filename} 失敗")

def load_data(filename, columns):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename, encoding='utf-8-sig')
            # 自動修正欄位不足的情況
            for col in columns:
                if col not in df.columns:
                    df[col] = 0
            return df[columns]
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

# ==========================================
# 3. 初始化 (Session State)
# ==========================================
if 'inventory' not in st.session_state:
    st.session_state['inventory'] = load_data(DEFAULT_CSV_FILE, COLUMNS)
if 'history' not in st.session_state:
    st.session_state['history'] = load_data(HISTORY_FILE, HISTORY_COLUMNS)
if 'design_sales' not in st.session_state:
    st.session_state['design_sales'] = load_data(DESIGN_SALES_FILE, DESIGN_SALES_COLUMNS)
if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 4. UI 介面
# ==========================================
st.set_page_config(page_title="GemCraft 庫存管理", layout="wide")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    admin_mode = (pwd == "admin123")
    
    page = st.radio("前往", ["📦 庫存管理", "🧮 設計與成本計算", "📜 紀錄查詢"])

# --- 頁面：設計與成本計算 ---
if page == "🧮 設計與成本計算":
    st.header("🧮 作品設計")
    
    # 選項清單
    inv = st.session_state['inventory']
    if not inv.empty:
        # 建立標籤
        inv['label'] = inv.apply(lambda r: f"[{r['倉庫']}] {r['名稱']} ({r['寬度mm']}mm) | 存:{int(r['庫存(顆)'])}", axis=1)
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv['label'].tolist())
        qty = c2.number_input("數量", min_value=1, value=1)
        
        if st.button("📥 加入清單"):
            selected_item = inv[inv['label'] == pick].iloc[0]
            st.session_state['current_design'].append({
                '編號': selected_item['編號'],
                '名稱': selected_item['名稱'],
                '數量': qty,
                '成本': float(selected_item['單顆成本']),
                '小計': float(selected_item['單顆成本']) * qty
            })
            st.rerun()

    # 顯示目前清單
    if st.session_state['current_design']:
        df_curr = pd.DataFrame(st.session_state['current_design'])
        st.table(df_curr[['名稱', '數量']])
        
        mat_sum = df_curr['小計'].sum()
        
        st.divider()
        st.subheader("💰 成本與雜支紀錄")
        ca, cb, cc = st.columns(3)
        labor = ca.number_input("工資", min_value=0, value=0)
        misc = cb.number_input("雜支", min_value=0, value=0)
        ship = cc.number_input("運費", min_value=0, value=0)
        
        total_cost = mat_sum + labor + misc + ship
        
        if admin_mode:
            st.metric("總成本", f"${total_cost:.1f}")
            st.write(f"(材料 ${mat_sum} + 工資 ${labor} + 雜支 ${misc} + 運費 ${ship})")

        with st.form("sale_form"):
            work_name = st.text_input("作品名稱", "未命名作品")
            if st.form_submit_button("✅ 售出並存檔"):
                # 扣庫存邏輯
                for item in st.session_state['current_design']:
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == item['編號'], '庫存(顆)'] -= item['數量']
                
                # 紀錄銷售
                new_sale = {
                    '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    '作品名稱': work_name,
                    '材料明細': str(st.session_state['current_design']),
                    '材料小計': mat_sum,
                    '工資': labor, '雜支': misc, '運費': ship,
                    '總成本': total_cost,
                    '建議售價x3': round(total_cost * 3),
                    '建議售價x5': round(total_cost * 5),
                    '備註': ""
                }
                st.session_state['design_sales'] = pd.concat([st.session_state['design_sales'], pd.DataFrame([new_sale])], ignore_index=True)
                
                save_data(st.session_state['inventory'], DEFAULT_CSV_FILE)
                save_data(st.session_state['design_sales'], DESIGN_SALES_FILE)
                st.session_state['current_design'] = []
                st.success("已存檔！")
                st.rerun()

# --- 頁面：庫存管理 (簡易版展示) ---
elif page == "📦 庫存管理":
    st.header("庫存清單")
    st.dataframe(st.session_state['inventory'])
