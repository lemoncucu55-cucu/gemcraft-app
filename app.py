import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================

COLUMNS = [
    '編號', '倉庫', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

SENSITIVE_COLUMNS = [
    '進貨總價', '單顆成本', '材料成本', '總成本', '單價', '小計', 
    '售價(x3)', '售價(x5)', '進貨數量(顆)', '進貨數量', '進貨日期', '進貨廠商', '廠商'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DEFAULT_WAREHOUSES = ["Imeng", "千畇"]
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]

# ==========================================
# 2. 核心函式
# ==========================================

def save_inventory():
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def robust_import_inventory(df):
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    if 'label' in df.columns:
        df = df.drop(columns=['label'])
    
    new_df = pd.DataFrame(columns=COLUMNS)
    for col in COLUMNS:
        if col in df.columns:
            new_df[col] = df[col]
        else:
            new_df[col] = ""

    new_df['倉庫'] = new_df['倉庫'].replace(['', 'nan', 'None'], 'Imeng').fillna('Imeng')
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        new_df[col] = pd.to_numeric(new_df[col], errors='coerce').fillna(0)
    
    return new_df[COLUMNS]

def format_size(row):
    try: return f"{float(row.get('寬度mm',0))}mm"
    except: return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    sup = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    return f"[{row.get('倉庫','Imeng')}] {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup} | 存:{int(row.get('庫存(顆)',0))}"

# ==========================================
# 3. 初始化與 UI
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            st.session_state['inventory'] = robust_import_inventory(pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig'))
        except: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else:
        st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False
if 'history' not in st.session_state: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
if 'current_design' not in st.session_state: st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    
    st.divider()
    st.header("📥 資料下載與還原")
    
    # --- 下載按鈕補回 ---
    if not st.session_state['inventory'].empty:
        csv_data = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv_data, f'inventory_{date.today()}.csv', "text/csv")
    
    if not st.session_state['history'].empty:
        history_csv = st.session_state['history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📜 下載進貨紀錄 (CSV)", history_csv, f'history_{date.today()}.csv', "text/csv")

    st.divider()
    uploaded_file = st.file_uploader("📤 匯入資料 (修正位移)", type=['csv'])
    if uploaded_file and st.button("🚨 執行精準匯入"):
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            st.session_state['inventory'] = robust_import_inventory(df)
            save_inventory()
            st.success("欄位已精準對齊！")
            time.sleep(1); st.rerun()
        except Exception as e: st.error(f"匯入失敗: {e}")

    st.divider()
    if st.button("🔴 重置系統", type="secondary"):
        st.session_state.clear(); st.rerun()

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab4, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用與出庫", "🛠️ 修改與盤點"])
    
    with tab1: # 補貨
        inv = st.session_state['inventory']
        if not inv.empty:
            # 建立帶有索引的 Label，防止名稱重複導致選擇錯誤
            inv_with_idx = inv.copy()
            inv_with_idx['label'] = inv_with_idx.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_with_idx['label'].tolist())
            
            # 找到原始資料的 index
            idx = inv_with_idx[inv_with_idx['label'] == target].index[0]
            row = inv.loc[idx]
            
            with st.form("restock"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}**")
                c1, c2 = st.columns(2)
                qty = c1.number_input("進貨數量", 1)
                cost = c2.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
                if st.form_submit_button("確認補貨"):
                    new_q = row['庫存(顆)'] + qty
                    new_c = ((row['庫存(顆)'] * row['單顆成本']) + cost) / new_q if new_q > 0 else 0
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                    if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = new_c
                    
                    # 紀錄流水帳
                    log = {
                        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'RESTOCK', '動作': '補貨',
                        '倉庫': row['倉庫'], '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'],
                        '規格': format_size(row), '廠商': row['進貨廠商'], '進貨數量': qty, '進貨總價': cost, '單價': (cost/qty if qty>0 else 0)
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    save_inventory(); st.success("補貨完成"); st.rerun()
        else: st.info("無庫存")

    # (tab2, tab4, tab3 等內容與上版本相同，保持功能穩定)
    # ... 為了長度簡略，以下為顯示部分 ...

    st.divider()
    # 倉庫數據統計
    st.subheader("📊 倉庫數據統計")
    if not st.session_state['inventory'].empty:
        df_stats = st.session_state['inventory'].copy()
        df_stats['庫存(顆)'] = pd.to_numeric(df_stats['庫存(顆)'], errors='coerce').fillna(0)
        summary = df_stats.groupby('倉庫').agg({'編號': 'count', '庫存(顆)': 'sum'}).rename(columns={'編號': '品項數量', '庫存(顆)': '顆數總計'})
        st.table(summary.astype(int))

    st.subheader("📋 庫存總表清單")
    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True)

# 頁面 B & C (歷史紀錄與設計)
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 歷史紀錄清單")
    df_h = st.session_state['history'].copy()
    if not df_h.empty:
        if not st.session_state['admin_mode']:
            df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
        st.dataframe(df_h, use_container_width=True)
    else: st.info("無紀錄")

elif page == "🧮 設計與成本計算":
    # 保持原有設計與扣庫存邏輯
    st.subheader("🧮 作品設計")
    # ... (程式碼省略)
