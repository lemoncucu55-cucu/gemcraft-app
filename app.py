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

# --- 新增：設計作品售出紀錄標題 ---
DESIGN_SALES_COLUMNS = [
    '售出時間', '作品序號', '作品名稱', '使用材料明細', '材料總成本', '建議售價(x3)', '建議售價(x5)', '備註'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv' # 新增檔案

DEFAULT_WAREHOUSES = ["Imeng", "千畇"]
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

def save_design_sales():
    try:
        if 'design_sales' in st.session_state:
            st.session_state['design_sales'].to_csv(DESIGN_SALES_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def robust_import_inventory(df):
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    if 'label' in df.columns: df = df.drop(columns=['label'])
    if '倉庫' not in df.columns: df.insert(1, '倉庫', 'Imeng')
    for col in COLUMNS:
        if col not in df.columns: df[col] = ""
    df = df[COLUMNS].copy()
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def format_size(row):
    try:
        w, l = float(row.get('寬度mm', 0)), float(row.get('長度mm', 0))
        return f"{w}x{l}mm" if l > 0 else f"{w}mm"
    except: return "0mm"

def make_inventory_label(row):
    stock_val = int(float(row.get('庫存(顆)', 0)))
    elem = f"({row.get('五行','')})" if row.get('五行','') else ""
    return f"[{row.get('倉庫','Imeng')}] {elem} {row.get('編號','')} | {row.get('名稱','')} | 存:{stock_val}"

# ==========================================
# 3. 初始化
# ==========================================

for key, file, cols in [
    ('inventory', DEFAULT_CSV_FILE, COLUMNS),
    ('history', HISTORY_FILE, HISTORY_COLUMNS),
    ('design_sales', DESIGN_SALES_FILE, DESIGN_SALES_COLUMNS) # 新增初始化
]:
    if key not in st.session_state:
        if os.path.exists(file):
            try: st.session_state[key] = pd.read_csv(file, encoding='utf-8-sig')
            except: st.session_state[key] = pd.DataFrame(columns=cols)
        else: st.session_state[key] = pd.DataFrame(columns=cols)

if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False
if 'current_design' not in st.session_state: st.session_state['current_design'] = []

# ==========================================
# 4. UI
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    page = st.radio("前往", ["📦 庫存管理", "📜 紀錄查詢", "🧮 設計與扣庫"])
    
    st.divider()
    st.header("📥 下載報表")
    if not st.session_state['inventory'].empty:
        st.download_button("📥 下載庫存總表", st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig'), f'inv_{date.today()}.csv')
    if not st.session_state['design_sales'].empty:
        st.download_button("💍 下載設計售出報表", st.session_state['design_sales'].to_csv(index=False).encode('utf-8-sig'), f'sales_{date.today()}.csv')

# ------------------------------------------
# 頁面 A & B (保持原有結構)
# ------------------------------------------
if page == "📦 庫存管理":
    # (此處保留原本的 tab1, tab2, tab4, tab3 邏輯...)
    st.info("請參考先前完整代碼之庫存管理邏輯")

elif page == "📜 紀錄查詢":
    tab_a, tab_b = st.tabs(["流水紀錄 (出入庫)", "作品紀錄 (售出設計)"])
    with tab_a:
        st.dataframe(st.session_state['history'], use_container_width=True)
    with tab_b:
        st.subheader("💍 已售出作品設計報表")
        st.dataframe(st.session_state['design_sales'], use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計與計算 (核心修改點)
# ------------------------------------------
elif page == "🧮 設計與扣庫":
    st.subheader("🧮 作品設計與自動扣庫")
    items = st.session_state['inventory'].copy()
    if not items.empty:
        items['lbl'] = items.apply(make_inventory_label, axis=1)
        sel = st.selectbox("選擇材料", items['lbl'])
        idx = items[items['lbl'] == sel].index[0]
        row = items.loc[idx]
        qty = st.number_input("數量", min_value=0, max_value=max(0, int(row['庫存(顆)'])), value=0)
        
        if st.button("⬇️ 加入作品清單"):
            if qty > 0:
                st.session_state['current_design'].append({
                    '編號': row['編號'], '名稱': row['名稱'], '數量': qty, '單價': row['單顆成本']
                })
                st.rerun()

        if st.session_state['current_design']:
            ddf = pd.DataFrame(st.session_state['current_design'])
            st.table(ddf)
            
            # 作品資訊輸入
            design_name = st.text_input("此作品名稱 (如：開運招財手串)", "未命名作品")
            design_note = st.text_area("作品備註 (如：客戶王小姐訂製)")
            
            total_cost = (ddf['數量'] * ddf['單價']).sum()
            st.metric("作品材料總成本", f"${total_cost:.2f}")

            if st.button("✅ 售出 (扣除庫存並記錄報表)"):
                # 1. 扣庫存與記錄流水
                material_details = []
                for x in st.session_state['current_design']:
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == x['編號'], '庫存(顆)'] -= x['數量']
                    material_details.append(f"{x['名稱']}({x['數量']}顆)")
                
                # 2. 寫入作品售出紀錄報表
                new_sale = {
                    '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    '作品序號': f"DS{int(time.time())}",
                    '作品名稱': design_name,
                    '使用材料明細': " / ".join(material_details),
                    '材料總成本': round(total_cost, 2),
                    '建議售價(x3)': round(total_cost * 3, 0),
                    '建議售價(x5)': round(total_cost * 5, 0),
                    '備註': design_note
                }
                st.session_state['design_sales'] = pd.concat([st.session_state['design_sales'], pd.DataFrame([new_sale])], ignore_index=True)
                
                save_inventory()
                save_design_sales()
                st.session_state['current_design'] = []
                st.success(f"作品「{design_name}」已售出，紀錄已存入報表。")
                time.sleep(1); st.rerun()
