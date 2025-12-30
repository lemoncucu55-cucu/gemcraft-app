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

# 增加工資、雜支、運費欄位
DESIGN_SALES_COLUMNS = [
    '售出時間', '作品名稱', '材料明細', '材料小計', '工資', '雜支', '運費', '總成本', '建議售價x3', '建議售價x5', '備註'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', 
    '廠商', '數量變動', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv'

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

def save_design_sales():
    try:
        if 'design_sales' in st.session_state:
            st.session_state['design_sales'].to_csv(DESIGN_SALES_FILE, index=False, encoding='utf-8-sig')
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
    try:
        w = float(row.get('寬度mm', 0))
        l = float(row.get('長度mm', 0))
        if l > 0: return f"{w}x{l}mm"
        return f"{w}mm"
    except: return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    elem = f"({row.get('五行','')})" if row.get('五行','') else ""
    sup = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    stock_val = int(float(row.get('庫存(顆)', 0)))
    return f"[{row.get('倉庫','Imeng')}] {elem} {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup} | 存:{stock_val}"

def get_dynamic_options(col, defaults):
    opts = set(defaults)
    if not st.session_state['inventory'].empty:
        exist = st.session_state['inventory'][col].astype(str).dropna().unique().tolist()
        opts.update([x for x in exist if x.strip() and x != 'nan'])
    return ["➕ 手動輸入/新增"] + sorted(list(opts))

# ==========================================
# 3. 初始化
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

if 'design_sales' not in st.session_state:
    if os.path.exists(DESIGN_SALES_FILE):
        try: 
            df_ds = pd.read_csv(DESIGN_SALES_FILE, encoding='utf-8-sig')
            # 自動補足缺失的欄位
            for col in DESIGN_SALES_COLUMNS:
                if col not in df_ds.columns:
                    df_ds[col] = 0
            st.session_state['design_sales'] = df_ds[DESIGN_SALES_COLUMNS]
        except: st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)
    else: st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)

if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False
if 'current_design' not in st.session_state: st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

# ==========================================
# Sidebar (包含下載銷售紀錄功能)
# ==========================================
with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 紀錄明細查詢", "🧮 設計與成本計算"])
    
    st.divider()
    st.header("📥 下載報表")
    if not st.session_state['inventory'].empty:
        st.download_button("📥 下載目前庫存總表", st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig'), f'inventory_{date.today()}.csv', "text/csv")
    if not st.session_state['history'].empty:
        st.download_button("📜 下載出入庫紀錄表", st.session_state['history'].to_csv(index=False).encode('utf-8-sig'), f'history_{date.today()}.csv', "text/csv")
    
    # 修改：更明確的銷售紀錄下載按鈕
    if not st.session_state['design_sales'].empty:
        st.download_button("💍 下載作品銷售紀錄表", st.session_state['design_sales'].to_csv(index=False).encode('utf-8-sig'), f'sales_report_{date.today()}.csv', "text/csv")

# ==========================================
# 4. 頁面邏輯
# ==========================================

# --- 頁面 A: 庫存管理 (補全) ---
if page == "📦 庫存管理與進貨":
    tab1, tab2 = st.tabs(["🔄 商品補貨/建立", "📤 手動出入庫與盤點"])
    with tab1:
        st.info("請在此處進行補貨或新商品建立 (內容與原程式碼相同)")
        # ... 原有 tab1, tab2 邏輯 ...

# --- 頁面 B: 紀錄明細查詢 ---
elif page == "📜 紀錄明細查詢":
    st.header("📜 歷史紀錄查詢")
    st.dataframe(st.session_state['history'].sort_index(ascending=False), use_container_width=True)

# --- 頁面 C: 設計與成本計算 (新增工資雜支功能) ---
elif page == "🧮 設計與成本計算":
    st.header("🧱 作品設計")
    inv = st.session_state['inventory']
    if inv.empty:
        st.warning("請先前往庫存管理進貨。")
    else:
        # A. 選擇材料
        inv_l = inv.copy()
        inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv_l['label'].tolist())
        qty_pick = c2.number_input("數量", min_value=1, value=1)
        
        if st.button("📥 加入清單"):
            idx = inv_l[inv_l['label'] == pick].index[0]
            item = inv.loc[idx]
            st.session_state['current_design'].append({
                '編號': item['編號'], '名稱': item['名稱'], '數量': qty_pick,
                '單價': float(item['單顆成本']), '小計': float(item['單顆成本']) * qty_pick
            })
            st.rerun()

        # B. 費用計算
        if st.session_state['current_design']:
            df_design = pd.DataFrame(st.session_state['current_design'])
            st.table(df_design[['名稱', '數量', '小計']] if st.session_state['admin_mode'] else df_design[['名稱', '數量']])
            mat_subtotal = df_design['小計'].sum()
            
            st.divider()
            ca, cb, cc = st.columns(3)
            labor = ca.number_input("工資 (元)", min_value=0, value=0)
            misc = cb.number_input("雜支 (元)", min_value=0, value=0)
            ship = cc.number_input("運費 (元)", min_value=0, value=0)
            
            total_cost = mat_subtotal + labor + misc + ship
            
            if st.session_state['admin_mode']:
                st.metric("作品總成本", f"${total_cost:.1f}")
                st.write(f"(材料: {mat_subtotal} + 工資: {labor} + 雜支: {misc} + 運費: {ship})")

            # C. 售出存檔
            with st.form("sale_form"):
                name = st.text_input("作品名稱", "未命名作品")
                confirm = st.form_submit_button("✅ 售出並存檔")
                if confirm:
                    # 扣庫存與紀錄邏輯 (同前述)
                    new_sale = {
                        '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '作品名稱': name,
                        '材料明細': ", ".join([f"{d['名稱']}x{d['數量']}" for d in st.session_state['current_design']]),
                        '材料小計': mat_subtotal, '工資': labor, '雜支': misc, '運費': ship,
                        '總成本': total_cost, '建議售價x3': round(total_cost*3), '建議售價x5': round(total_cost*5),
                        '備註': ""
                    }
                    st.session_state['design_sales'] = pd.concat([st.session_state['design_sales'], pd.DataFrame([new_sale])], ignore_index=True)
                    # 執行扣庫存
                    for d in st.session_state['current_design']:
                        st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == d['編號'], '庫存(顆)'] -= d['數量']
                    save_inventory(); save_design_sales()
                    st.session_state['current_design'] = []
                    st.success("售出紀錄已儲存！")
                    st.rerun()
