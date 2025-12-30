import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定與初始化
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
    return f"[{row.get('倉庫','Imeng')}] ({row.get('五行','')}) {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}) | 存:{stock_val}"

def get_dynamic_options(col, defaults):
    opts = set(defaults)
    if not st.session_state['inventory'].empty:
        exist = st.session_state['inventory'][col].astype(str).dropna().unique().tolist()
        opts.update([x for x in exist if x.strip() and x != 'nan'])
    return ["➕ 手動輸入/新增"] + sorted(list(opts))

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE): st.session_state['inventory'] = robust_import_inventory(pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig'))
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
if 'history' not in st.session_state:
    if os.path.exists(HISTORY_FILE): st.session_state['history'] = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
    else: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
if 'current_design' not in st.session_state: st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

# ==========================================
# 2. 側邊欄
# ==========================================
with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 紀錄明細查詢", "🧮 設計與成本計算"])
    st.divider()
    st.header("📥 下載報表")
    if not st.session_state['inventory'].empty:
        st.download_button("📥 下載目前庫存總表", st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig'), f'inv_{date.today()}.csv')
    
    st.divider()
    uploaded_file = st.file_uploader("📤 上傳資料修正位移", type=['csv'])
    if uploaded_file and st.button("🚨 執行修正匯入"):
        try:
            st.session_state['inventory'] = robust_import_inventory(pd.read_csv(uploaded_file, encoding='utf-8-sig'))
            save_inventory(); st.success("修正匯入成功"); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"匯入失敗: {e}")
    if st.button("🔴 重置系統"): st.session_state.clear(); st.rerun()

# ==========================================
# 3. 頁面邏輯
# ==========================================

# --- 頁面 A: 庫存管理 ---
if page == "📦 庫存管理與進貨":
    t1, t2, t3, t4 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用出庫", "🛠️ 修改盤點"])
    with t1:
        if not st.session_state['inventory'].empty:
            inv_l = st.session_state['inventory'].copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_l['label'].tolist())
            idx = inv_l[inv_l['label'] == target].index[0]
            row = st.session_state['inventory'].loc[idx]
            with st.form("restock"):
                qty = st.number_input("進貨數量", min_value=1)
                cost = st.number_input("進貨總價", min_value=0.0) if st.session_state['admin_mode'] else 0.0
                if st.form_submit_button("確認補貨"):
                    old_q, old_c = float(row['庫存(顆)']), float(row['單顆成本'])
                    new_q = old_q + qty
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                    if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = ((old_q*old_c)+cost)/new_q
                    save_inventory(); st.success("補貨成功"); time.sleep(1); st.rerun()
    with t2:
        with st.form("new_item"):
            c1, c2, c3 = st.columns(3)
            wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES); name = c2.text_input("名稱"); cat = c3.selectbox("分類", ["天然石", "配件", "耗材"])
            s1, s2, s3 = st.columns(3)
            w = s1.number_input("寬度mm", min_value=0.0); l = s2.number_input("長度mm", min_value=0.0); sh = s3.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            if st.form_submit_button("➕ 建立商品"):
                new_r = {'編號':f"ST{int(time.time())}", '倉庫':wh, '分類':cat, '名稱':name, '寬度mm':w, '長度mm':l, '形狀':sh, '庫存(顆)':0, '單顆成本':0}
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_r])], ignore_index=True)
                save_inventory(); st.success("建立成功"); st.rerun()
    # (出庫與盤點略，僅顯示庫存表)
    st.divider()
    vdf = st.session_state['inventory'].copy()
    if not st.session_state['admin_mode']: vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
    st.dataframe(vdf, use_container_width=True)

# --- 頁面 B: 紀錄查詢 ---
elif page == "📜 紀錄明細查詢":
    st.subheader("📜 歷史紀錄")
    df_h = st.session_state['history'].copy()
    if not st.session_state['admin_mode']: df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
    st.dataframe(df_h, use_container_width=True)

# --- 頁面 C: 設計與計算 (保證顯示版) ---
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計與成本核算")

    # 🔴 這裡就是您之前沒看到的區塊，我把它放到最醒目的位置
    st.error("👇 步驟 1：員工請先在此輸入費用 (若無請維持 0)")
    f1, f2, f3 = st.columns(3)
    labor = f1.number_input("🛠️ 製作工資", min_value=0.0, step=10.0, key="lab_new")
    misc = f2.number_input("📦 雜支包材", min_value=0.0, step=10.0, key="mis_new")
    ship = f3.number_input("🚚 物流運費", min_value=0.0, step=10.0, key="shi_new")

    st.divider()
    st.info("👇 步驟 2：選擇材料加入清單")
    if not st.session_state['inventory'].empty:
        inv_d = st.session_state['inventory'].copy()
        inv_d['lbl'] = inv_d.apply(make_inventory_label, axis=1)
        c1, c2 = st.columns([3, 1])
        sel = c1.selectbox("選擇材料", inv_d['lbl'].tolist(), key="sel_new")
        idx = inv_d[inv_d['lbl'] == sel].index[0]
        qty = c2.number_input("數量", min_value=0, max_value=int(float(inv_d.loc[idx, '庫存(顆)'])), value=0, key="qty_new")
        
        if st.button("⬇️ 加入清單"):
            if qty > 0:
                st.session_state['current_design'].append({
                    '編號': inv_d.loc[idx, '編號'], '名稱': inv_d.loc[idx, '名稱'], 
                    '數量': qty, '單價': inv_d.loc[idx, '單顆成本'], 
                    '倉庫': inv_d.loc[idx, '倉庫'], '分類': inv_d.loc[idx, '分類'], '規格': format_size(inv_d.loc[idx])
                })
                st.rerun()

    if st.session_state['current_design']:
        st.markdown("##### 📋 目前清單")
        ddf = pd.DataFrame(st.session_state['current_design'])
        ddf['小計'] = ddf['數量'] * ddf['單價']
        st.table(ddf[['名稱', '數量']] if not st.session_state['admin_mode'] else ddf[['名稱', '數量', '單價', '小計']])

        if st.session_state['admin_mode']:
            total_m = ddf['小計'].sum()
            st.success(f"📊 主管結算：材料 ${total_m:.0f} + 附加 ${labor+misc+ship:.0f} = **總成本 ${total_m+labor+misc+ship:.0f}**")

        c1, c2 = st.columns(2)
        if c1.button("✅ 售出 (扣庫存並記錄費用)", use_container_width=True):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            for _, r in ddf.iterrows():
                st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == r['編號'], '庫存(顆)'] -= r['數量']
                log = {'紀錄時間': ts, '單號': 'SALE', '動作': "材料出庫", '倉庫': r['倉庫'], '編號': r['編號'], '分類': r['分類'], '名稱': r['名稱'], '規格': r['規格'], '廠商': '-', '數量變動': -r['數量'], '進貨總價': 0, '單價': r['單價']}
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
            if (labor+misc+ship) > 0:
                fee_log = {'紀錄時間': ts, '單號': 'FEE', '動作': f"附加費(工{labor}/雜{misc}/運{ship})", '倉庫': '-', '編號': '-', '分類': '費用', '名稱': '設計費/運費', '規格': '-', '廠商': '-', '數量變動': 0, '進貨總價': labor+misc+ship, '單價': labor+misc+ship}
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([fee_log])], ignore_index=True)
            save_inventory(); save_history(); st.session_state['current_design'] = []; st.success("售出成功"); time.sleep(1); st.rerun()
        if c2.button("🗑️ 清空清單", use_container_width=True): st.session_state['current_design'] = []; st.rerun()
