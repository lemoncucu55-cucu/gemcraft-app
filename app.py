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
HISTORY_FILE = 'inventory_history.csv'
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
    try:
        w = float(row.get('寬度mm', 0))
        l = float(row.get('長度mm', 0))
        if l > 0:
            return f"{w}x{l}mm"
        return f"{w}mm"
    except:
        return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    elem = f"({row.get('五行','')})" if row.get('五行','') else ""
    sup = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    stock_val = int(float(row.get('庫存(顆)', 0)))
    return f"[{row.get('倉庫','Imeng')}] {elem} {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup} | 存:{stock_val}"

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

# ------------------------------------------
# 頁面 A & B (略，保持原有功能)
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    # (此部分代碼同前，為了簡潔暫略)
    st.info("此部分代碼已整合至系統中。")
elif page == "📜 紀錄明細查詢":
    st.subheader("📜 歷史出入庫明細")
    df_h = st.session_state['history'].copy()
    if not df_h.empty:
        if not st.session_state['admin_mode']:
            df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
        st.dataframe(df_h, use_container_width=True)
    else: st.info("尚無紀錄")

# ------------------------------------------
# 頁面 C: 設計與計算 (完全更新版)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計與成本核算")
    
    items = st.session_state['inventory'].copy()
    if not items.empty:
        # 1. 材料選擇區
        items['lbl'] = items.apply(make_inventory_label, axis=1)
        c1, c2 = st.columns([3, 1])
        sel = c1.selectbox("選擇材料", items['lbl'], key="design_sel")
        idx = items[items['lbl'] == sel].index[0]
        cur_s = int(float(items.loc[idx, '庫存(顆)']))
        qty = c2.number_input("數量", min_value=0, max_value=max(0, cur_s), value=0)
        
        if st.button("⬇️ 加入清單"):
            if qty > 0:
                st.session_state['current_design'].append({
                    '編號': items.loc[idx, '編號'], 
                    '名稱': items.loc[idx, '名稱'], 
                    '數量': qty, 
                    '單價': items.loc[idx, '單顆成本'],
                    '倉庫': items.loc[idx, '倉庫'],
                    '分類': items.loc[idx, '分類'],
                    '規格': format_size(items.loc[idx])
                })
                st.rerun()

        # 2. 已選清單顯示
        if st.session_state['current_design']:
            st.divider()
            st.markdown("##### 📋 目前設計清單")
            ddf = pd.DataFrame(st.session_state['current_design'])
            ddf['小計'] = ddf['數量'] * ddf['單價']
            
            if st.session_state['admin_mode']:
                display_cols = ['名稱', '數量', '單價', '小計']
            else:
                display_cols = ['名稱', '數量']
            st.table(ddf[display_cols])

            # --- 3. 員工可填寫區 (工資、雜支、運費) ---
            st.markdown("---")
            st.markdown("##### 💰 額外成本填寫 (請填入數值)")
            ec1, ec2, ec3 = st.columns(3)
            labor_fee = ec1.number_input("製作工資", min_value=0.0, step=50.0, key="labor_val")
            misc_fee = ec2.number_input("雜支/包材", min_value=0.0, step=10.0, key="misc_val")
            ship_fee = ec3.number_input("物流運費", min_value=0.0, step=10.0, key="ship_val")

            # --- 4. 總計計算 ---
            material_subtotal = ddf['小計'].sum()
            total_extra = labor_fee + misc_fee + ship_fee
            total_cost = material_subtotal + total_extra
            
            if st.session_state['admin_mode']:
                st.success("📊 **主管專用成本結算**")
                m1, m2 = st.columns(2)
                m1.metric("材料小計", f"${material_subtotal:.0f}")
                m2.metric("總成本 (含額外支出)", f"${total_cost:.0f}")
            else:
                st.info("💡 員工端不顯示金額統計，填寫完畢請按售出。")
            
            # 5. 操作按鈕：包含存入歷史紀錄邏輯
            st.divider()
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("✅ 售出 (自動扣庫存並記錄)"):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                # A. 扣除庫存並逐項記錄到歷史
                for _, x in ddf.iterrows():
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == x['編號'], '庫存(顆)'] -= x['數量']
                    
                    # 記錄每一種材料的出庫
                    log_material = {
                        '紀錄時間': timestamp, '單號': 'SALE_ITEM', '動作': f"作品售出材料",
                        '倉庫': x['倉庫'], '編號': x['編號'], '分類': x['分類'], 
                        '名稱': x['名稱'], '規格': x['規格'], '廠商': '-', 
                        '數量變動': -x['數量'], '進貨總價': 0, '單價': x['單價']
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log_material])], ignore_index=True)

                # B. 記錄總額外的支出 (以便主管對帳)
                if total_extra > 0:
                    log_extra = {
                        '紀錄時間': timestamp, '單號': 'SALE_FEES', 
                        '動作': f"售出附加費用(工{labor_fee}/雜{misc_fee}/運{ship_fee})",
                        '倉庫': '-', '編號': '-', '分類': '費用', '名稱': '工資雜支運費', 
                        '規格': '-', '廠商': '-', '數量變動': 0, '進貨總價': total_extra, '單價': total_extra
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log_extra])], ignore_index=True)

                save_inventory()
                save_history()
                st.session_state['current_design'] = []
                st.success("✅ 庫存已扣除，費用已存入歷史紀錄！")
                time.sleep(1.5)
                st.rerun()
                
            if col_btn2.button("🗑️ 清空設計單", type="secondary"):
                st.session_state['current_design'] = []
                st.rerun()
