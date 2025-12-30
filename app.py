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

# 保持原始結構，避免 CSV 讀取報錯
DESIGN_SALES_COLUMNS = [
    '售出時間', '作品名稱', '材料明細', '總成本', '建議售價x3', '建議售價x5', '備註'
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
        try: st.session_state['design_sales'] = pd.read_csv(DESIGN_SALES_FILE, encoding='utf-8-sig')
        except: st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)
    else: st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)

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
        st.download_button("📥 下載目前庫存總表", st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig'), f'inventory_{date.today()}.csv', "text/csv")
    if not st.session_state['history'].empty:
        st.download_button("📜 下載出入庫紀錄表", st.session_state['history'].to_csv(index=False).encode('utf-8-sig'), f'history_{date.today()}.csv', "text/csv")
    if not st.session_state['design_sales'].empty:
        st.download_button("💍 下載設計作品紀錄", st.session_state['design_sales'].to_csv(index=False).encode('utf-8-sig'), f'design_sales_{date.today()}.csv', "text/csv")

# ------------------------------------------
# 頁面 A: 庫存管理與進貨
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    tab1, tab2, tab4, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用/出庫與入庫", "🛠️ 修改與盤點"])
    
    with tab1: # 補貨
        inv = st.session_state['inventory']
        if not inv.empty:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇補貨商品", inv_l['label'].tolist(), key="t1_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]
            with st.form("restock_form"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}**")
                c1, c2 = st.columns(2)
                qty = c1.number_input("進貨數量", min_value=1, value=1)
                cost = c2.number_input("進貨總價", min_value=0.0) if st.session_state['admin_mode'] else 0.0
                if st.form_submit_button("確認補貨"):
                    old_q, old_c = float(row['庫存(顆)']), float(row['單顆成本'])
                    new_q = old_q + qty
                    new_avg = ((old_q * old_c) + cost) / new_q if new_q > 0 else 0
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                    if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = new_avg
                    
                    log = {'紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'IN', '動作': '補貨入庫', '倉庫': row['倉庫'], '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'], '規格': format_size(row), '廠商': row['進貨廠商'], '數量變動': qty, '進貨總價': cost, '單價': (cost/qty if qty>0 else 0)}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    
                    save_inventory(); save_history(); st.success("已補貨並寫入歷史明細"); st.rerun()

    with tab2: # ✨ 建立新商品
        with st.form("add_new"):
            c1, c2, c3 = st.columns(3)
            wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES)
            cat = c2.selectbox("分類", ["天然石", "配件", "耗材"])
            name = c3.text_input("名稱")
            s1, s2, s3 = st.columns(3)
            w_mm = s1.number_input("寬度 (mm)", min_value=0.0, value=0.0)
            l_mm = s2.number_input("長度 (mm)", min_value=0.0, value=0.0)
            shape = s3.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            c4, c5, c6 = st.columns(3)
            elem = c4.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS))
            sup = c5.selectbox("進貨廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS))
            qty_init = c6.number_input("初始數量", min_value=1, value=1)
            price_init = st.number_input("初始進貨總價", min_value=0.0) if st.session_state['admin_mode'] else 0.0
            
            if st.form_submit_button("➕ 建立商品"):
                nid = f"ST{int(time.time())}"
                new_r = {
                    '編號': nid, '倉庫': wh, '分類': cat, '名稱': name, '寬度mm': w_mm, '長度mm': l_mm, 
                    '形狀': shape, '五行': elem, '進貨廠商': sup, '庫存(顆)': qty_init, 
                    '單顆成本': price_init/qty_init if qty_init > 0 else 0, '進貨日期': date.today(), '進貨總價': price_init
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_r])], ignore_index=True)
                
                log_new = {'紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'NEW', '動作': '新商品建立入庫', '倉庫': wh, '編號': nid, '分類': cat, '名稱': name, '規格': f"{w_mm}mm", '廠商': sup, '數量變動': qty_init, '進貨總價': price_init, '單價': price_init/qty_init if qty_init > 0 else 0}
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log_new])], ignore_index=True)
                
                save_inventory(); save_history(); st.success(f"已建立商品「{name}」並寫入明細"); st.rerun()

# ------------------------------------------
# 頁面 C: 設計與成本計算 (新增工資、雜支、運費功能)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.header("🧮 作品設計與成本計算")
    inv = st.session_state['inventory']
    if inv.empty:
        st.warning("目前無庫存資料。")
    else:
        inv_l = inv.copy()
        inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv_l['label'].tolist())
        qty_pick = c2.number_input("數量", min_value=1, value=1)
        if st.button("📥 加入材料清單"):
            idx = inv_l[inv_l['label'] == pick].index[0]
            item = inv.loc[idx]
            st.session_state['current_design'].append({
                '編號': item['編號'], '名稱': item['名稱'], '數量': qty_pick, 
                '單價': float(item['單顆成本']), '小計': float(item['單顆成本']) * qty_pick
            })
            st.rerun()

        if st.session_state['current_design']:
            df_curr = pd.DataFrame(st.session_state['current_design'])
            st.subheader("📋 目前設計清單")
            st.table(df_curr[['名稱', '數量', '小計']] if st.session_state['admin_mode'] else df_curr[['名稱', '數量']])
            
            # --- 計算邏輯：材料 + 額外費用 ---
            material_cost = df_curr['小計'].sum()
            
            st.divider()
            st.subheader("💰 額外費用輸入")
            ca, cb, cc = st.columns(3)
            labor_val = ca.number_input("🛠️ 工資 (元)", min_value=0, value=0, step=10)
            misc_val = cb.number_input("📦 雜支 (元)", min_value=0, value=0, step=5)
            ship_val = cc.number_input("🚚 運費 (元)", min_value=0, value=0, step=1)
            
            total_cost = material_cost + labor_val + misc_val + ship_val
            
            if st.session_state['admin_mode']:
                st.info(f"🧱 材料成本: ${material_cost:.1f} + 🛠️ 額外費用: ${labor_val + misc_val + ship_val}")
                st.metric("作品總成本", f"${total_cost:.1f}")
                s3, s5 = st.columns(2)
                s3.success(f"建議售價 (x3): ${round(total_cost * 3)}")
                s5.success(f"建議售價 (x5): ${round(total_cost * 5)}")

            with st.form("design_sale_form"):
                work_name = st.text_input("作品名稱", value="未命名作品")
                note = st.text_area("備註")
                if st.form_submit_button("✅ 售出 (自動扣庫存並儲存紀錄)"):
                    details = ", ".join([f"{d['名稱']}x{d['數量']}" for d in st.session_state['current_design']])
                    # 1. 扣庫存
                    for d in st.session_state['current_design']:
                        st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == d['編號'], '庫存(顆)'] -= d['數量']
                    
                    # 2. 存紀錄 (將額外費用紀錄在備註中，以免改動 CSV 表頭導致崩潰)
                    full_note = f"{note} [明細: 工資{labor_val}, 雜支{misc_val}, 運費{ship_val}]"
                    new_sale = {
                        '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        '作品名稱': work_name, 
                        '材料明細': details, 
                        '總成本': total_cost, 
                        '建議售價x3': round(total_cost * 3), 
                        '建議售價x5': round(total_cost * 5), 
                        '備註': full_note
                    }
                    st.session_state['design_sales'] = pd.concat([st.session_state['design_sales'], pd.DataFrame([new_sale])], ignore_index=True)
                    save_inventory(); save_design_sales(); st.session_state['current_design'] = []
                    st.success("已完成售出紀錄"); time.sleep(1); st.rerun()

        if st.button("🗑️ 清空設計清單"):
            st.session_state['current_design'] = []
            st.rerun()
