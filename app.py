import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================
COLUMNS = ['編號', '倉庫', '分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本']
SENSITIVE_COLUMNS = ['進貨總價', '單顆成本', '材料成本', '總成本', '單價', '小計', '售價(x3)', '售價(x5)', '進貨數量(顆)', '進貨數量', '進貨日期', '進貨廠商', '廠商']
HISTORY_COLUMNS = ['紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', '廠商', '數量變動', '進貨總價', '單價']

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DEFAULT_WAREHOUSES = ["Imeng", "千畇"]
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

# ==========================================
# 2. 核心函式
# ==========================================
def save_inventory():
    try: st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except: pass

def save_history():
    try: st.session_state['history'].to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    except: pass

def robust_import_inventory(df):
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    if '倉庫' not in df.columns: df.insert(1, '倉庫', 'Imeng')
    for col in COLUMNS:
        if col not in df.columns: df[col] = ""
    df = df[COLUMNS].copy()
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def format_size(row):
    w, l = float(row.get('寬度mm', 0)), float(row.get('長度mm', 0))
    return f"{w}x{l}mm" if l > 0 else f"{w}mm"

def make_inventory_label(row):
    sz, stock_val = format_size(row), int(float(row.get('庫存(顆)', 0)))
    sup = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    return f"[{row.get('倉庫','Imeng')}] ({row.get('五行','')}) {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup} | 存:{stock_val}"

# ==========================================
# 3. 初始化
# ==========================================
if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        st.session_state['inventory'] = robust_import_inventory(pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig'))
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    if os.path.exists(HISTORY_FILE): st.session_state['history'] = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
    else: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'current_design' not in st.session_state: st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

# 側邊欄權限
with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    page = st.radio("功能導航", ["📦 庫存管理與進貨", "📜 紀錄明細查詢", "🧮 設計與成本計算"])

# ------------------------------------------
# 頁面 A & B (略過)
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.info("請於此處管理進貨與庫存。")
elif page == "📜 紀錄明細查詢":
    st.subheader("📜 歷史出入庫明細")
    df_h = st.session_state['history'].copy()
    if not st.session_state['admin_mode']:
        df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
    st.dataframe(df_h, use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計與計算 (重新排列版)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計與成本核算")

    # --- 💡 關鍵更動：將費用填寫移到最上方，不受任何條件限制 ---
    st.error("⚠️ 員工請務必先填寫下方費用 (若無則維持 0)")
    f_c1, f_c2, f_c3 = st.columns(3)
    # 使用極度唯一的 key 值避免快取衝突
    labor_input = f_c1.number_input("🛠️ 製作工資", min_value=0.0, step=10.0, key="labor_v99")
    misc_input = f_c2.number_input("📦 雜支包材", min_value=0.0, step=10.0, key="misc_v99")
    ship_input = f_c3.number_input("🚚 物流運費", min_value=0.0, step=10.0, key="ship_v99")
    
    st.divider()

    # 材料選擇區
    if not st.session_state['inventory'].empty:
        items = st.session_state['inventory'].copy()
        items['lbl'] = items.apply(make_inventory_label, axis=1)
        sel_c, qty_c = st.columns([3, 1])
        sel = sel_c.selectbox("選擇材料", items['lbl'], key="sel_v99")
        idx = items[items['lbl'] == sel].index[0]
        cur_s = int(float(items.loc[idx, '庫存(顆)']))
        qty = qty_c.number_input("數量", min_value=0, max_value=max(0, cur_s), value=0, key="qty_v99")
        
        if st.button("⬇️ 加入清單"):
            if qty > 0:
                st.session_state['current_design'].append({
                    '編號': items.loc[idx, '編號'], '名稱': items.loc[idx, '名稱'], 
                    '數量': qty, '單價': items.loc[idx, '單顆成本'], '倉庫': items.loc[idx, '倉庫'],
                    '分類': items.loc[idx, '分類'], '規格': format_size(items.loc[idx])
                })
                st.rerun()

        # 結算顯示
        if st.session_state['current_design']:
            st.markdown("##### 📋 目前材料清單")
            ddf = pd.DataFrame(st.session_state['current_design'])
            ddf['小計'] = ddf['數量'] * ddf['單價']
            
            # 權限顯示
            show_cols = ['名稱', '數量', '單價', '小計'] if st.session_state['admin_mode'] else ['名稱', '數量']
            st.table(ddf[show_cols])

            # 主管總計區
            mat_total = ddf['小計'].sum()
            extra_total = labor_input + misc_input + ship_input
            if st.session_state['admin_mode']:
                st.success(f"📊 總計：材料 ${mat_total:.0f} + 附加費 ${extra_total:.0f} = **總成本 ${mat_total + extra_total:.0f}**")

            # 售出按鈕
            btn1, btn2 = st.columns(2)
            if btn1.button("✅ 確認售出 (自動記錄工資運費)", use_container_width=True):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                # 扣庫存與記錄材料
                for _, r in ddf.iterrows():
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == r['編號'], '庫存(顆)'] -= r['數量']
                    log = {'紀錄時間': ts, '單號': 'SALE', '動作': "材料出庫", '倉庫': r['倉庫'], '編號': r['編號'], '分類': r['分類'], '名稱': r['名稱'], '規格': r['規格'], '廠商': '-', '數量變動': -r['數量'], '進貨總價': 0, '單價': r['單價']}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                
                # 💡 強制存入工資雜支紀錄
                if extra_total > 0:
                    fee_log = {'紀錄時間': ts, '單號': 'FEE', '動作': f"附加費(工{labor_input}/雜{misc_input}/運{ship_input})", '倉庫': '-', '編號': '-', '分類': '費用', '名稱': '設計/運費總計', '規格': '-', '廠商': '-', '數量變動': 0, '進貨總價': extra_total, '單價': extra_total}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([fee_log])], ignore_index=True)
                
                save_inventory(); save_history()
                st.session_state['current_design'] = []
                st.success("紀錄已存入歷史明細！")
                time.sleep(1); st.rerun()

            if btn2.button("🗑️ 清空設計單", use_container_width=True):
                st.session_state['current_design'] = []
                st.rerun()
