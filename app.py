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
    '廠商', '數量變動', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv' # 新增歷史紀錄存檔
DEFAULT_WAREHOUSES = ["Imeng", "千畇"]
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

# ==========================================
# 2. 核心函式
# ==========================================

def save_inventory():
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def save_history():
    try:
        if 'history' in st.session_state:
            st.session_state['history'].to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def robust_import_inventory(df):
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    if 'label' in df.columns:
        df = df.drop(columns=['label'])
    if '倉庫' not in df.columns:
        df.insert(1, '倉庫', 'Imeng')
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].copy()
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def format_size(row):
    try: return f"{float(row.get('寬度mm',0))}mm"
    except: return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    elem = f"({row.get('五行','')})" if row.get('五行','') else ""
    sup = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    stock_val = int(float(row.get('庫存(顆)',0)))
    return f"[{row.get('倉庫','Imeng')}] {elem} {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup} | 存:{stock_val}"

# ==========================================
# 3. 初始化與 UI
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try: st.session_state['inventory'] = robust_import_inventory(pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig'))
        except: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try: st.session_state['history'] = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        except: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
    else: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False
if 'current_design' not in st.session_state: st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 紀錄明細查詢", "🧮 設計與成本計算"])
    
    st.divider()
    st.header("📥 下載報表")
    if not st.session_state['inventory'].empty:
        csv_inv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載目前庫存總表", csv_inv, f'inventory_{date.today()}.csv', "text/csv")

    if not st.session_state['history'].empty:
        csv_hist = st.session_state['history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📜 下載出入庫紀錄表", csv_hist, f'history_{date.today()}.csv', "text/csv")

    st.divider()
    if st.button("🔴 重置系統", type="secondary"):
        st.session_state.clear(); st.rerun()

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    tab1, tab2, tab4, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用與出庫", "🛠️ 修改與盤點"])
    
    with tab1: # 補貨 (入庫紀錄)
        inv = st.session_state['inventory']
        if not inv.empty:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_l['label'].tolist(), key="tab1_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]
            with st.form("restock"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}**")
                c1, c2 = st.columns(2)
                qty = c1.number_input("進貨數量", min_value=1, value=1)
                cost = c2.number_input("進貨總價", min_value=0.0, value=0.0) if st.session_state['admin_mode'] else 0.0
                if st.form_submit_button("確認補貨"):
                    new_q = row['庫存(顆)'] + qty
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                    # 寫入歷史紀錄
                    log = {'紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'IN', '動作': '補貨入庫', '倉庫': row['倉庫'], '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'], '規格': format_size(row), '廠商': row['進貨廠商'], '數量變動': qty, '進貨總價': cost, '單價': (cost/qty if qty>0 else 0)}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    save_inventory(); save_history(); st.success("補貨入庫已記錄"); st.rerun()

    with tab4: # 領用與出庫 (出庫紀錄)
        inv_o = st.session_state['inventory'].copy()
        if not inv_o.empty:
            inv_o['label'] = inv_o.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇出庫商品", inv_o['label'].tolist(), key="tab4_sel")
            idx = inv_o[inv_o['label'] == target].index[0]
            row = st.session_state['inventory'].loc[idx]
            cur_s = int(float(row['庫存(顆)']))
            with st.form("out_form"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}**")
                qty_o = st.number_input("出庫數量", min_value=0, max_value=max(0, cur_s), value=0)
                reason = st.selectbox("原因", ["自用", "損壞", "樣品", "其他"])
                note = st.text_area("備註說明")
                if st.form_submit_button("確認出庫"):
                    if qty_o > 0:
                        st.session_state['inventory'].at[idx, '庫存(顆)'] -= qty_o
                        # 寫入歷史紀錄
                        log = {'紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'OUT', '動作': f'領用出庫({reason})', '倉庫': row['倉庫'], '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'], '規格': format_size(row), '廠商': row['進貨廠商'], '數量變動': -qty_o, '進貨總價': 0, '單價': row['單顆成本']}
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                        save_inventory(); save_history(); st.warning(f"出庫已記錄，備註：{note}"); time.sleep(1); st.rerun()

    st.divider()
    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True)

# ------------------------------------------
# 頁面 B: 紀錄明細查詢
# ------------------------------------------
elif page == "📜 紀錄明細查詢":
    st.subheader("📜 歷史出入庫明細 (含領用、出庫、補貨)")
    df_h = st.session_state['history'].copy()
    if not df_h.empty:
        if not st.session_state['admin_mode']:
            # 非主管鎖定財務欄位
            df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
        st.dataframe(df_h, use_container_width=True)
        
        if st.button("🗑️ 清空歷史紀錄 (慎用)"):
            if st.session_state['admin_mode']:
                st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
                save_history(); st.rerun()
            else: st.error("權限不足")
    else: st.info("尚無出入庫紀錄")
