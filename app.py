import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================

# 新增「倉庫」欄位
COLUMNS = [
    '編號', '倉庫', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

SENSITIVE_COLUMNS = ['進貨總價', '單顆成本', '材料成本', '總成本', '單價', '小計', '售價(x3)', '售價(x5)']

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

DESIGN_HISTORY_COLUMNS = [
    '單號', '日期', '總顆數', '材料成本', '工資', '雜支', 
    '總成本', '售價(x3)', '售價(x5)', '明細內容'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DESIGN_HISTORY_FILE = 'design_sales_history.csv'

# 倉庫選項
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

def save_design_history():
    try:
        if 'design_history' in st.session_state:
            st.session_state['design_history'].to_csv(DESIGN_HISTORY_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def robust_import_inventory(df, force_position=True):
    if force_position:
        if df.shape[1] > len(COLUMNS): df = df.iloc[:, :len(COLUMNS)]
        elif df.shape[1] < len(COLUMNS):
            for i in range(len(COLUMNS) - df.shape[1]): df[f'temp_{i}'] = ""
        df.columns = COLUMNS
    else:
        df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
        # 如果舊檔沒有「倉庫」欄位，自動補上並設為 Imeng
        if '倉庫' not in df.columns:
            df['倉庫'] = "Imeng"
        
        rename_map = {'Code': '編號', 'Name': '名稱', 'Qty': '進貨數量(顆)', 'Stock': '庫存(顆)'}
        df = df.rename(columns=rename_map)
        for col in COLUMNS:
            if col not in df.columns: df[col] = ""

    df = df[COLUMNS].copy()
    # 確保倉庫欄位不為空，若空則設為 Imeng
    df['倉庫'] = df['倉庫'].replace(['', 'nan', 'None'], 'Imeng')
    
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for col in ['編號', '倉庫', '分類', '名稱', '形狀', '五行', '進貨廠商']:
        df[col] = df[col].astype(str).replace('nan', '').replace('None', '').apply(lambda x: x.strip())
    return df

def robust_import_sales(df):
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    for col in DESIGN_HISTORY_COLUMNS:
        if col not in df.columns: df[col] = ""
    df = df[DESIGN_HISTORY_COLUMNS].copy()
    num_cols = ['總顆數', '材料成本', '工資', '雜支', '總成本', '售價(x3)', '售價(x5)']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def format_size(row):
    try: return f"{float(row.get('寬度mm',0))}mm"
    except: return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    # Label 加入倉庫資訊方便辨識
    label = f"[{row.get('倉庫','Imeng')}] 【{row.get('五行','')}】 {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}) | 存:{row.get('庫存(顆)',0)}"
    if st.session_state.get('admin_mode', False):
        label += f" | 成本:${row.get('單顆成本',0):.2f}"
    return label

def make_design_label(row):
    sz = format_size(row)
    label = f"[{row.get('倉庫','Imeng')}] {row.get('名稱','')} ({sz}) | 存:{row.get('庫存(顆)',0)}"
    if st.session_state.get('admin_mode', False):
        label += f" | ${float(row.get('單顆成本',0)):.2f}/顆"
    return label

def get_dynamic_options(col, defaults):
    opts = set(defaults)
    if not st.session_state['inventory'].empty:
        exist = st.session_state['inventory'][col].astype(str).dropna().unique().tolist()
        opts.update([x for x in exist if x.strip() and x != 'nan'])
    return ["➕ 手動輸入/新增"] + sorted(list(opts))

def generate_new_id(category, df):
    prefix = {'天然石': 'ST', '配件': 'AC', '耗材': 'OT'}.get(category, "OT")
    if df.empty: return f"{prefix}0001"
    df_ids = df['編號'].astype(str)
    mask = df_ids.str.startswith(prefix, na=False)
    nums = df_ids[mask].str[2:].str.extract(r'(\d+)', expand=False).dropna().astype(int)
    next_num = 1 if nums.empty else nums.max() + 1
    return f"{prefix}{next_num:04d}"

def merge_inventory_duplicates(df):
    if df.empty: return df, 0
    # 合併準則加入「倉庫」
    group_cols = ['倉庫', '分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨廠商']
    df['庫存(顆)'] = pd.to_numeric(df['庫存(顆)'], errors='coerce').fillna(0)
    df['單顆成本'] = pd.to_numeric(df['單顆成本'], errors='coerce').fillna(0)
    orig_cnt = len(df)
    df['總成本_tmp'] = df['庫存(顆)'] * df['單顆成本']
    agg = df.groupby(group_cols, as_index=False).agg({'庫存(顆)': 'sum', '總成本_tmp': 'sum', '進貨日期': 'max'})
    agg['單顆成本'] = agg.apply(lambda r: (r['總成本_tmp'] / r['庫存(顆)']) if r['庫存(顆)'] > 0 else 0, axis=1)
    agg = agg.drop(columns=['總成本_tmp'])
    df_sorted = df.sort_values('進貨日期', ascending=False)
    base = df_sorted.drop_duplicates(subset=group_cols, keep='first')[['編號'] + group_cols]
    final = pd.merge(agg, base, on=group_cols, how='left')
    return robust_import_inventory(final, False), orig_cnt - len(final)

# ==========================================
# 3. 初始化 Session (強制修復版本)
# ==========================================

# A. 基礎初始化
if 'inventory' not in st.session_state:
    # 嘗試從檔案讀取
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            raw_df = pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig')
            st.session_state['inventory'] = robust_import_inventory(raw_df)
        except:
            st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else:
        st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'design_history' not in st.session_state:
    st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

if 'admin_mode' not in st.session_state:
    st.session_state['admin_mode'] = False

# B. ★ 強制檢查並補齊「倉庫」欄位 ★
# 這是修復 KeyError 的關鍵
if not st.session_state['inventory'].empty:
    # 如果缺少倉庫欄位，立刻補上
    if '倉庫' not in st.session_state['inventory'].columns:
        st.session_state['inventory']['倉庫'] = "Imeng"
    
    # 確保所有數值欄位正確，避免後續計算出錯
    for col in ['進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        if col in st.session_state['inventory'].columns:
            st.session_state['inventory'][col] = pd.to_numeric(st.session_state['inventory'][col], errors='coerce').fillna(0)

    # 再次確認欄位順序對齊 COLUMNS 定義
    existing_cols = [c for c in COLUMNS if c in st.session_state['inventory'].columns]
    st.session_state['inventory'] = st.session_state['inventory'][existing_cols]
# ==========================================
# 4. UI 介面
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    if pwd == "admin123":
        st.session_state['admin_mode'] = True
        st.success("主管模式已開啟")
    else:
        st.session_state['admin_mode'] = False

    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    
    if not st.session_state['inventory'].empty:
        csv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_{date.today()}.csv', "text/csv")
    
    st.divider()
    st.markdown("### 📤 資料還原區")
    uploaded_inv = st.file_uploader("1️⃣ 上傳庫存備份 (Inventory)", type=['csv'], key="up_inv")
    if uploaded_inv:
        try:
            raw_df = pd.read_csv(uploaded_inv, encoding='utf-8-sig')
            if st.button("🚨 庫存檔強制還原"):
                st.session_state['inventory'] = robust_import_inventory(raw_df)
                save_inventory(); st.success("已還原！"); time.sleep(1); st.rerun()
        except Exception as e: st.error(f"錯誤: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "🛠️ 修改與盤點"])
    
    with tab1:
        inv_df = st.session_state['inventory'].copy()
        if not inv_df.empty:
            inv_df['label'] = inv_df.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_df['label'].tolist())
            rows = inv_df[inv_df['label'] == target]
            if not rows.empty:
                row = rows.iloc[0]; idx = rows.index[0]
                with st.form("restock"):
                    st.write(f"倉庫: **{row['倉庫']}** | 目前庫存: **{row['庫存(顆)']}**")
                    c1, c2 = st.columns(2)
                    qty = c1.number_input("進貨數量", 1)
                    cost = c2.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
                    if st.form_submit_button("📦 確認補貨"):
                        old_q = float(row['庫存(顆)']); old_c = float(row['單顆成本'])
                        new_q = old_q + qty
                        new_avg = ((old_q * old_c) + cost) / new_q if new_q > 0 else 0
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                        if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = new_avg
                        
                        log = {
                            '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'RESTOCK', '動作': '補貨', 
                            '倉庫': row['倉庫'], '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'], 
                            '規格': format_size(row), '廠商': row['進貨廠商'], '進貨數量': qty, '進貨總價': cost, '單價': (cost/qty if qty>0 else 0)
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                        save_inventory(); st.success("補貨完成"); st.rerun()

    with tab2:
        with st.form("add"):
            c_wh, c1, c2 = st.columns([1, 1, 2])
            wh = c_wh.selectbox("存入倉庫", DEFAULT_WAREHOUSES) # 選擇 Imeng 或 千畇
            cat = c1.selectbox("分類", ["天然石", "配件", "耗材"])
            name = st.text_input("名稱")
            c3, c4, c5 = st.columns(3)
            w = c3.number_input("寬度mm", 0.0, step=0.5); l = c4.number_input("長度mm", 0.0, step=0.5)
            shape = c5.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            c6, c7, c8 = st.columns(3)
            elem = c6.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS))
            sup = c7.selectbox("廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS))
            qty = c8.number_input("進貨數量", 1)
            price = st.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
            
            if st.form_submit_button("➕ 新增商品"):
                nid = generate_new_id(cat, st.session_state['inventory'])
                new_item = {
                    '編號': nid, '倉庫': wh, '分類': cat, '名稱': name, '寬度mm': w, '長度mm': l, 
                    '形狀': shape, '五行': elem, '進貨總價': price, '進貨數量(顆)': qty, 
                    '進貨日期': date.today(), '進貨廠商': sup, '庫存(顆)': qty, '單顆成本': price/qty if qty>0 else 0
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_item])], ignore_index=True)
                save_inventory(); st.success(f"已存入 {wh} 倉庫"); st.rerun()

    with tab3:
        if not st.session_state['inventory'].empty:
            df_edit = st.session_state['inventory'].copy()
            df_edit['label'] = df_edit.apply(make_inventory_label, axis=1)
            target = st.selectbox("搜尋修改", df_edit['label'])
            rows = df_edit[df_edit['label'] == target]
            if not rows.empty:
                orig = rows.iloc[0]
                idx = st.session_state['inventory'][st.session_state['inventory']['編號'] == orig['編號']].index[0]
                with st.form("edit"):
                    c_wh, c_nm = st.columns(2)
                    wh = c_wh.selectbox("所屬倉庫", DEFAULT_WAREHOUSES, index=DEFAULT_WAREHOUSES.index(orig['倉庫']) if orig['倉庫'] in DEFAULT_WAREHOUSES else 0)
                    nm = c_nm.text_input("名稱", orig['名稱'])
                    c_qt, c_co = st.columns(2)
                    qt = c_qt.number_input("庫存量", value=int(float(orig['庫存(顆)'])))
                    co = c_co.number_input("單顆成本", value=float(orig['單顆成本'])) if st.session_state['admin_mode'] else float(orig['單顆成本'])
                    if st.form_submit_button("💾 儲存修改"):
                        st.session_state['inventory'].at[idx, '倉庫'] = wh
                        st.session_state['inventory'].at[idx, '名稱'] = nm
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = qt
                        if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = co
                        save_inventory(); st.success("已更新"); st.rerun()

    st.divider()
    # 新增：分倉庫統計總表
    st.subheader("📊 倉庫數據統計")
    if not st.session_state['inventory'].empty:
        summary = st.session_state['inventory'].groupby('倉庫').agg({
            '編號': 'count',
            '庫存(顆)': 'sum'
        }).rename(columns={'編號': '品項數量', '庫存(顆)': '顆數總計'})
        st.table(summary)
    
    st.subheader("📋 庫存總表清單")
    # 倉庫快速篩選
    sel_wh = st.multiselect("篩選倉庫", DEFAULT_WAREHOUSES, default=DEFAULT_WAREHOUSES)
    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        vdf = vdf[vdf['倉庫'].isin(sel_wh)]
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True, height=400)

# (其餘 📜 進貨紀錄 與 🧮 設計頁面 保持原邏輯，但在顯示時同樣會自動過濾敏感欄位)
# ------------------------------------------
# 頁面 B: 進貨紀錄
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 紀錄中心")
    df_h = st.session_state['history'].copy()
    if not df_h.empty:
        if not st.session_state['admin_mode']:
            df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
        st.dataframe(df_h, use_container_width=True)
    else: st.info("無紀錄")

# ------------------------------------------
# 頁面 C: 設計與成本
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計與扣庫存")
    items = st.session_state['inventory']
    if not items.empty:
        items['lbl'] = items.apply(make_design_label, axis=1)
        c1, c2, c3 = st.columns([3, 1, 1])
        sel = c1.selectbox("選擇材料 (含倉庫標示)", items['lbl'])
        qty = c2.number_input("使用數量", 1)
        if c3.button("⬇️ 加入設計"):
            r = items[items['lbl'] == sel].iloc[0]
            st.session_state['current_design'].append({
                '編號': r['編號'], '名稱': r['名稱'], '倉庫': r['倉庫'],
                '單價': r['單顆成本'], '數量': qty, '小計': r['單顆成本']*qty
            })
            st.rerun()
        
        if st.session_state['current_design']:
            df_cur = pd.DataFrame(st.session_state['current_design'])
            disp = df_cur.copy()
            if not st.session_state['admin_mode']: disp = disp.drop(columns=['單價', '小計'])
            st.dataframe(disp, use_container_width=True)
            if st.session_state['admin_mode']: st.info(f"設計總成本: ${df_cur['小計'].sum():.2f}")
            
            if st.button("✅ 確認售出 (自動扣除對應倉庫庫存)"):
                for x in st.session_state['current_design']:
                    # 準確扣除該編號的庫存
                    st.session_state['inventory'].loc[items['編號'] == x['編號'], '庫存(顆)'] -= x['數量']
                save_inventory(); st.session_state['current_design'] = []; st.success("已完成扣庫存"); time.sleep(1); st.rerun()
