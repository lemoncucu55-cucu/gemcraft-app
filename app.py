import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================

# 系統定義的標準欄位
COLUMNS = [
    '編號', '倉庫', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

# 權限鎖定欄位
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
    """
    修正版：解決欄位位移問題。
    原理：優先使用標題名稱對齊，若無標題則按順序對齊。
    """
    # 清理標題文字
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    
    # 如果偵測到 label 欄位，先行移除
    if 'label' in df.columns:
        df = df.drop(columns=['label'])

    # 建立一個乾淨的 DataFrame 容器
    new_df = pd.DataFrame(columns=COLUMNS)
    
    # 嘗試對齊欄位 (邏輯：如果檔案中有這個名稱，就填入對應欄位)
    for col in COLUMNS:
        if col in df.columns:
            new_df[col] = df[col]
        else:
            # 針對可能出現的異名進行容錯處理
            rename_map = {'Code': '編號', 'Name': '名稱', 'Qty': '進貨數量(顆)', 'Stock': '庫存(顆)'}
            found = False
            for old_n, new_n in rename_map.items():
                if old_n == col and new_n in df.columns:
                    new_df[col] = df[new_n]
                    found = True
            if not found:
                new_df[col] = "" # 真的找不到就填空

    # 數據轉型與消毒
    new_df['倉庫'] = new_df['倉庫'].replace(['', 'nan', 'None'], 'Imeng').fillna('Imeng')
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        new_df[col] = pd.to_numeric(new_df[col], errors='coerce').fillna(0)
    
    return new_df[COLUMNS]

def make_inventory_label(row):
    try: sz = f"{float(row.get('寬度mm',0))}mm"
    except: sz = "0mm"
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
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    
    st.divider()
    uploaded_file = st.file_uploader("📥 匯入資料 (修正位移)", type=['csv'])
    if uploaded_file and st.button("🚨 執行精準匯入"):
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            st.session_state['inventory'] = robust_import_inventory(df)
            save_inventory()
            st.success("欄位已精準對齊！")
            time.sleep(1); st.rerun()
        except Exception as e: st.error(f"匯入失敗: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    tab1, tab2, tab4, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用與出庫", "🛠️ 修改與盤點"])
    
    with tab1: # 補貨
        inv = st.session_state['inventory']
        if not inv.empty:
            labels = [make_inventory_label(r) for _, r in inv.iterrows()]
            target = st.selectbox("選擇商品", labels)
            # 這裡用 index 抓回原始資料，避免因為 label 內容變動抓不到
            idx = labels.index(target)
            row = inv.iloc[idx]
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
                    save_inventory(); st.success("補貨完成"); st.rerun()

    with tab2: # 新增商品
        with st.form("add"):
            c1, c2, c3 = st.columns(3)
            wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES)
            cat = c2.selectbox("分類", ["天然石", "配件", "耗材"])
            name = c3.text_input("名稱")
            p = st.number_input("總價", 0.0) if st.session_state['admin_mode'] else 0.0
            q = st.number_input("數量", 1)
            if st.form_submit_button("新增"):
                nid = f"ST{int(time.time())}" # 簡易 ID
                new_r = {'編號': nid, '倉庫': wh, '分類': cat, '名稱': name, '庫存(顆)': q, '單顆成本': p/q if q>0 else 0}
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_r])], ignore_index=True)
                save_inventory(); st.success("已新增"); st.rerun()

    st.divider()
    st.subheader("📋 庫存清單")
    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True)
