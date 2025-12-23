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
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

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

def get_dynamic_options(col, defaults):
    opts = set(defaults)
    if not st.session_state['inventory'].empty:
        exist = st.session_state['inventory'][col].astype(str).dropna().unique().tolist()
        opts.update([x for x in exist if x.strip() and x != 'nan'])
    return ["➕ 手動輸入/新增"] + sorted(list(opts))

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
    
    if not st.session_state['inventory'].empty:
        csv_data = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv_data, f'inventory_{date.today()}.csv', "text/csv")
    
    if not st.session_state['history'].empty:
        history_csv = st.session_state['history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📜 下載紀錄 (CSV)", history_csv, f'history_{date.today()}.csv', "text/csv")

    st.divider()
    uploaded_file = st.file_uploader("📤 匯入修復", type=['csv'])
    if uploaded_file and st.button("🚨 執行精準匯入"):
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            st.session_state['inventory'] = robust_import_inventory(df)
            save_inventory(); st.success("已精準對齊！"); time.sleep(1); st.rerun()
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
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_l['label'].tolist(), key="tab1_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
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
                    save_inventory(); st.success("補貨完成"); st.rerun()

    with tab2: # 建立新商品
        with st.form("add_new"):
            c1, c2, c3 = st.columns(3)
            wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES)
            cat = c2.selectbox("分類", ["天然石", "配件", "耗材"])
            name = c3.text_input("名稱")
            
            c4, c5, c6 = st.columns(3)
            w = c4.number_input("寬度mm", 0.0)
            l = c5.number_input("長度mm", 0.0)
            shape = c6.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            if shape == "➕ 手動輸入/新增": shape = st.text_input("輸入形狀")
            
            c7, c8, c9 = st.columns(3)
            elem = c7.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS))
            if elem == "➕ 手動輸入/新增": elem = st.text_input("輸入五行")
            sup = c8.selectbox("廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS))
            if sup == "➕ 手動輸入/新增": sup = st.text_input("輸入廠商")
            qty = c9.number_input("進貨數量", 1)
            
            price = st.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
            
            if st.form_submit_button("➕ 新增商品"):
                nid = f"ST{int(time.time())}"
                new_item = {
                    '編號': nid, '倉庫': wh, '分類': cat, '名稱': name, '寬度mm': w, '長度mm': l, 
                    '形狀': shape, '五行': elem, '進貨總價': price, '進貨數量(顆)': qty, 
                    '進貨日期': date.today(), '進貨廠商': sup, '庫存(顆)': qty, '單顆成本': price/qty if qty>0 else 0
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_item])], ignore_index=True)
                save_inventory(); st.success(f"已新增至 {wh}"); st.rerun()

    with tab4: # 領用與出庫
        inv_o = st.session_state['inventory'].copy()
        if not inv_o.empty:
            inv_o['label'] = inv_o.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_o['label'].tolist(), key="tab4_sel")
            idx = inv_o[inv_o['label'] == target].index[0]
            row = st.session_state['inventory'].loc[idx]
            cur_s = int(row['庫存(顆)'])
            with st.form("out_form"):
                st.write(f"倉庫: **{row['倉庫']}** | 目前庫存: **{cur_s}**")
                qty_o = st.number_input("出庫數量", 0, cur_s, (1 if cur_s > 0 else 0))
                note = st.text_area("出庫原因/備註")
                if st.form_submit_button("確認出庫"):
                    if qty_o > 0:
                        st.session_state['inventory'].at[idx, '庫存(顆)'] -= qty_o
                        save_inventory(); st.warning("已扣除庫存"); time.sleep(1); st.rerun()
        else: st.info("無庫存")

    with tab3: # 修改與盤點
        if not st.session_state['inventory'].empty:
            df_e = st.session_state['inventory'].copy()
            df_e['label'] = df_e.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇修改項目", df_e['label'].tolist(), key="tab3_sel")
            idx = df_e[df_e['label'] == target].index[0]
            orig = st.session_state['inventory'].loc[idx]
            
            with st.form("edit_form"):
                st.write(f"正在修改編號: **{orig['編號']}**")
                c1, c2 = st.columns(2)
                nm = c1.text_input("商品名稱", orig['名稱'])
                wh = c2.selectbox("所屬倉庫", DEFAULT_WAREHOUSES, index=DEFAULT_WAREHOUSES.index(orig['倉庫']) if orig['倉庫'] in DEFAULT_WAREHOUSES else 0)
                
                c3, c4, c5 = st.columns(3)
                wm = c3.number_input("寬度mm", value=float(orig['寬度mm']))
                lm = c4.number_input("長度mm", value=float(orig['長度mm']))
                sh = c5.text_input("形狀", orig['形狀'])
                
                c6, c7 = st.columns(2)
                qt = c6.number_input("庫存量修正(盤點)", value=int(orig['庫存(顆)']))
                # 成本與廠商僅限主管修改
                co = c7.number_input("單顆成本修正", value=float(orig['單顆成本'])) if st.session_state['admin_mode'] else float(orig['單顆成本'])
                
                sup = st.text_input("進貨廠商修正", orig['進貨廠商']) if st.session_state['admin_mode'] else orig['進貨廠商']
                
                c_btn1, c_btn2 = st.columns([1, 4])
                submit = c_btn1.form_submit_button("💾 儲存修改")
                
                if submit:
                    st.session_state['inventory'].at[idx, '名稱'] = nm
                    st.session_state['inventory'].at[idx, '倉庫'] = wh
                    st.session_state['inventory'].at[idx, '寬度mm'] = wm
                    st.session_state['inventory'].at[idx, '長度mm'] = lm
                    st.session_state['inventory'].at[idx, '形狀'] = sh
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = qt
                    if st.session_state['admin_mode']:
                        st.session_state['inventory'].at[idx, '單顆成本'] = co
                        st.session_state['inventory'].at[idx, '進貨廠商'] = sup
                    save_inventory(); st.success("資料已更新"); time.sleep(1); st.rerun()
            
            if st.button("🗑️ 刪除此商品 (不可復原)", type="primary"):
                st.session_state['inventory'] = st.session_state['inventory'].drop(idx).reset_index(drop=True)
                save_inventory(); st.warning("已刪除商品"); time.sleep(1); st.rerun()
        else: st.info("無資料")

    st.divider()
    # 倉庫統計表
    st.subheader("📊 倉庫數據統計")
    if not st.session_state['inventory'].empty:
        df_s = st.session_state['inventory'].copy()
        summary = df_stats = df_s.groupby('倉庫').agg({'編號': 'count', '庫存(顆)': 'sum'}).rename(columns={'編號': '品項數量', '庫存(顆)': '顆數總計'})
        st.table(summary.astype(int))

    st.subheader("📋 庫存總表清單")
    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True)

# ------------------------------------------
# 頁面 B: 紀錄查詢
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 歷史紀錄")
    df_h = st.session_state['history'].copy()
    if not df_h.empty:
        if not st.session_state['admin_mode']:
            df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
        st.dataframe(df_h, use_container_width=True)
    else: st.info("無紀錄")

# ------------------------------------------
# 頁面 C: 設計與計算
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計")
    items = st.session_state['inventory'].copy()
    if not items.empty:
        items['lbl'] = items.apply(lambda r: f"[{r['倉庫']}] {r['名稱']} | 存:{int(r['庫存(顆)'])}", axis=1)
        sel = st.selectbox("選擇材料", items['lbl'])
        idx = items[items['lbl'] == sel].index[0]
        row = items.loc[idx]
        qty = st.number_input("數量", 1, max_value=int(row['庫存(顆)']))
        if st.button("⬇️ 加入作品清單"):
            st.session_state['current_design'].append({'編號':row['編號'], '名稱':row['名稱'], '數量':qty, '單價':row['單顆成本']})
            st.rerun()
        
        if st.session_state['current_design']:
            ddf = pd.DataFrame(st.session_state['current_design'])
            st.table(ddf[['名稱', '數量']] if not st.session_state['admin_mode'] else ddf)
            if st.button("✅ 售出 (扣除庫存)"):
                for x in st.session_state['current_design']:
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == x['編號'], '庫存(顆)'] -= x['數量']
                save_inventory(); st.session_state['current_design'] = []; st.success("已扣庫存"); st.rerun()
            if st.button("🗑️ 清空清單"):
                st.session_state['current_design'] = []; st.rerun()
