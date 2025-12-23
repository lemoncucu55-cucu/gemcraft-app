import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================

# 新增「倉庫」欄位至核心定義
COLUMNS = [
    '編號', '倉庫', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

# 財務敏感欄位清單
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

# 倉庫與選項定義
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
    """強力匯入與格式校正"""
    if force_position:
        if df.shape[1] > len(COLUMNS): df = df.iloc[:, :len(COLUMNS)]
        elif df.shape[1] < len(COLUMNS):
            for i in range(len(COLUMNS) - df.shape[1]): df[f'temp_{i}'] = ""
        df.columns = COLUMNS
    else:
        df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
        if '倉庫' not in df.columns: df['倉庫'] = "Imeng"
        for col in COLUMNS:
            if col not in df.columns: df[col] = ""

    df = df[COLUMNS].copy()
    # 倉庫資料消毒
    df['倉庫'] = df['倉庫'].replace(['', 'nan', 'None'], 'Imeng').fillna('Imeng')
    # 數值資料消毒
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    # 文字資料消毒
    for col in ['編號', '倉庫', '分類', '名稱', '形狀', '五行', '進貨廠商']:
        df[col] = df[col].astype(str).replace('nan', '').replace('None', '').apply(lambda x: x.strip())
    return df

def format_size(row):
    try: return f"{float(row.get('寬度mm',0))}mm"
    except: return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    label = f"[{row.get('倉庫','Imeng')}] {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}) | 存:{int(float(row.get('庫存(顆)',0)))}"
    if st.session_state.get('admin_mode', False):
        label += f" | 成本:${row.get('單顆成本',0):.2f}"
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
# 3. 初始化 Session
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            st.session_state['inventory'] = robust_import_inventory(pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig'))
        except: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else:
        st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

# 強制檢查欄位完整性 (修復 KeyError)
if '倉庫' not in st.session_state['inventory'].columns:
    st.session_state['inventory']['倉庫'] = "Imeng"

if 'history' not in st.session_state: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
if 'design_history' not in st.session_state: st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)
if 'current_design' not in st.session_state: st.session_state['current_design'] = []
if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False

# ==========================================
# 4. UI 介面
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    if st.session_state['admin_mode']: st.success("🔓 主管模式已開啟")
    
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    
    if st.button("🔴 重置系統", type="secondary"):
        st.session_state.clear(); st.rerun()

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "🛠️ 修改與盤點"])
    
    with tab1: # 補貨
        inv_df = st.session_state['inventory'].copy()
        if not inv_df.empty:
            inv_df['label'] = inv_df.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_df['label'].tolist())
            row_match = inv_df[inv_df['label'] == target]
            if not row_match.empty:
                row = row_match.iloc[0]
                idx = st.session_state['inventory'][st.session_state['inventory']['編號'] == row['編號']].index[0]
                with st.form("restock"):
                    st.write(f"倉庫: **{row['倉庫']}** | 目前庫存: **{int(row['庫存(顆)'])}**")
                    c1, c2 = st.columns(2)
                    qty = c1.number_input("進貨數量", 1)
                    cost = c2.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
                    if st.form_submit_button("📦 確認補貨"):
                        old_q = float(row['庫存(顆)'])
                        old_c = float(row['單顆成本'])
                        new_q = old_q + qty
                        new_avg = ((old_q * old_c) + cost) / new_q if new_q > 0 else 0
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                        if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = new_avg
                        save_inventory(); st.success("補貨成功"); st.rerun()
        else: st.info("無庫存")

    with tab2: # 新增
        with st.form("add"):
            c_wh, c1, c2 = st.columns([1,1,2])
            wh = c_wh.selectbox("存入倉庫", DEFAULT_WAREHOUSES)
            cat = c1.selectbox("分類", ["天然石", "配件", "耗材"])
            name = st.text_input("名稱")
            c3, c4, c5 = st.columns(3)
            w = c3.number_input("寬度mm", 0.0); l = c4.number_input("長度mm", 0.0)
            shape = c5.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            price = st.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
            qty = st.number_input("數量", 1)
            if st.form_submit_button("➕ 新增"):
                nid = generate_new_id(cat, st.session_state['inventory'])
                new_item = {
                    '編號': nid, '倉庫': wh, '分類': cat, '名稱': name, '寬度mm': w, '長度mm': l, 
                    '形狀': shape, '五行': '無', '進貨總價': price, '進貨數量(顆)': qty, 
                    '進貨日期': date.today(), '進貨廠商': '自設', '庫存(顆)': qty, '單顆成本': price/qty if qty>0 else 0
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_item])], ignore_index=True)
                save_inventory(); st.success(f"已存入 {wh}"); st.rerun()

    with tab3: # 修改
        if not st.session_state['inventory'].empty:
            df_edit = st.session_state['inventory'].copy()
            df_edit['label'] = df_edit.apply(make_inventory_label, axis=1)
            target = st.selectbox("修改項目", df_edit['label'])
            row_e = df_edit[df_edit['label'] == target].iloc[0]
            idx_e = st.session_state['inventory'][st.session_state['inventory']['編號'] == row_e['編號']].index[0]
            with st.form("edit"):
                new_wh = st.selectbox("更改倉庫", DEFAULT_WAREHOUSES, index=DEFAULT_WAREHOUSES.index(row_e['倉庫']))
                new_qt = st.number_input("盤點庫存", value=int(row_e['庫存(顆)']))
                if st.form_submit_button("💾 儲存"):
                    st.session_state['inventory'].at[idx_e, '倉庫'] = new_wh
                    st.session_state['inventory'].at[idx_e, '庫存(顆)'] = new_qt
                    save_inventory(); st.success("更新完成"); st.rerun()

    st.divider()
    # 倉庫統計表 (修正小數點與數量問題)
    st.subheader("📊 倉庫數據統計")
    if not st.session_state['inventory'].empty:
        df_stats = st.session_state['inventory'].copy()
        df_stats['庫存(顆)'] = pd.to_numeric(df_stats['庫存(顆)'], errors='coerce').fillna(0)
        summary = df_stats.groupby('倉庫').agg({'編號': 'count', '庫存(顆)': 'sum'}).rename(columns={'編號': '品項數量', '庫存(顆)': '顆數總計'})
        summary = summary.astype(int) # 強制轉整數移除小數點
        st.table(summary)

    st.subheader("📋 庫存總表清單")
    if st.button("🔄 合併重複品項"):
        st.session_state['inventory'], _ = merge_inventory_duplicates(st.session_state['inventory'])
        save_inventory(); st.rerun()

    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True)

# ------------------------------------------
# 頁面 B & C (簡約處理顯示邏輯)
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 歷史紀錄")
    df_h = st.session_state['history'].copy()
    if not st.session_state['admin_mode'] and not df_h.empty:
        df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
    st.dataframe(df_h, use_container_width=True)

elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計")
    items = st.session_state['inventory'].copy()
    if not items.empty:
        items['lbl'] = items.apply(lambda r: f"[{r['倉庫']}] {r['名稱']} ({r['寬度mm']}mm) | 存:{int(r['庫存(顆)'])}", axis=1)
        c1, c2, c3 = st.columns([3,1,1])
        sel = c1.selectbox("選擇材料", items['lbl'])
        qty = c2.number_input("數量", 1)
        if c3.button("⬇️ 加入"):
            r = items[items['lbl'] == sel].iloc[0]
            st.session_state['current_design'].append({'編號':r['編號'], '名稱':r['名稱'], '數量':qty, '單價':r['單顆成本']})
            st.rerun()
        
        if st.session_state['current_design']:
            ddf = pd.DataFrame(st.session_state['current_design'])
            if not st.session_state['admin_mode']:
                st.table(ddf[['名稱', '數量']])
            else:
                ddf['小計'] = ddf['數量'] * ddf['單價']
                st.table(ddf)
                st.info(f"總成本: ${ddf['小計'].sum():.2f}")
            
            if st.button("✅ 售出 (扣除庫存)"):
                for x in st.session_state['current_design']:
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == x['編號'], '庫存(顆)'] -= x['數量']
                save_inventory(); st.session_state['current_design'] = []; st.success("已扣庫存"); st.rerun()
