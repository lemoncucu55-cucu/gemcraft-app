import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time
import numpy as np

# ==========================================
# 1. 核心設定
# ==========================================

COLUMNS = [
    '編號', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '編號', '分類', '名稱', '規格', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

DESIGN_HISTORY_COLUMNS = [
    '單號', '日期', '總顆數', '材料成本', '工資', '雜支', 
    '總成本', '售價(x3)', '售價(x5)', '明細內容'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DESIGN_HISTORY_FILE = 'design_sales_history.csv'

DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

# ==========================================
# 2. 核心函式 (強化容錯)
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

def robust_import(df, force_position=True):
    """資料清洗與強制對齊"""
    # 1. 強制對齊模式
    if force_position:
        if df.shape[1] > len(COLUMNS):
            df = df.iloc[:, :len(COLUMNS)]
        if df.shape[1] < len(COLUMNS):
            for i in range(len(COLUMNS) - df.shape[1]):
                df[f'temp_{i}'] = ""
        df.columns = COLUMNS
    else:
        # 2. 標準模式
        df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
        rename_map = {
            'Code': '編號', 'ID': '編號', 'Product ID': '編號',
            'Category': '分類', 'Name': '名稱', 'Title': '名稱',
            'Width': '寬度mm', 'Size': '寬度mm', 'Length': '長度mm',
            'Shape': '形狀', 'Element': '五行',
            'Price': '進貨總價', 'Cost': '進貨總價',
            'Qty': '進貨數量(顆)', 'Quantity': '進貨數量(顆)',
            'Date': '進貨日期', 'Vendor': '進貨廠商',
            'Stock': '庫存(顆)', 'Unit Cost': '單顆成本'
        }
        df = df.rename(columns=rename_map)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = 0 if ('mm' in col or '價' in col or '數量' in col or '成本' in col) else ""

    # 3. 確保資料型態 (防止 NaN 崩潰)
    df = df[COLUMNS]
    numeric_cols = ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    text_cols = ['編號', '分類', '名稱', '形狀', '五行', '進貨廠商']
    for col in text_cols:
        df[col] = df[col].astype(str).replace('nan', '').replace('None', '').apply(lambda x: x.strip())

    return df

def make_inventory_label(row):
    sz = f"{float(row.get('寬度mm',0))}mm"
    return f"【{row.get('五行','')}】 {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}) | {row.get('進貨廠商','')} | 存:{row.get('庫存(顆)',0)}"

def make_design_label(row):
    sz = f"{float(row.get('寬度mm',0))}mm"
    return f"【{row.get('五行','')}】{row.get('名稱','')} | {row.get('形狀','')} ({sz}) | {row.get('進貨廠商','')} | ${float(row.get('單顆成本',0)):.2f}/顆 | 存:{row.get('庫存(顆)',0)}"

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
    group_cols = ['分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨廠商']
    
    df['庫存(顆)'] = pd.to_numeric(df['庫存(顆)'], errors='coerce').fillna(0)
    df['單顆成本'] = pd.to_numeric(df['單顆成本'], errors='coerce').fillna(0)
    
    orig_cnt = len(df)
    df['總成本'] = df['庫存(顆)'] * df['單顆成本']
    
    agg = df.groupby(group_cols, as_index=False).agg({
        '庫存(顆)': 'sum', '總成本': 'sum', '進貨日期': 'max'
    })
    agg['單顆成本'] = agg.apply(lambda r: (r['總成本'] / r['庫存(顆)']) if r['庫存(顆)'] > 0 else 0, axis=1)
    agg = agg.drop(columns=['總成本'])
    
    df_sorted = df.sort_values('進貨日期', ascending=False)
    base = df_sorted.drop_duplicates(subset=group_cols, keep='first')[['編號'] + group_cols]
    
    final = pd.merge(agg, base, on=group_cols, how='left')
    return robust_import(final, False), orig_cnt - len(final)

# ==========================================
# 3. 初始化 & 自動修復 Session
# ==========================================

if 'inventory' not in st.session_state:
    st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

# ★★★ 自動消毒：確保數值欄位沒有 NaN，防止 int() 轉換失敗 ★★★
if not st.session_state['inventory'].empty:
    numeric_cols = ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']
    for col in numeric_cols:
        st.session_state['inventory'][col] = pd.to_numeric(st.session_state['inventory'][col], errors='coerce').fillna(0)

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'design_history' not in st.session_state:
    st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 4. UI 介面
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    
    # 下載
    if not st.session_state['inventory'].empty:
        csv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_{date.today()}.csv', "text/csv")
    
    # 上傳救援
    st.markdown("### 📤 資料還原")
    uploaded_inv = st.file_uploader("上傳庫存備份 (CSV)", type=['csv'])
    
    if uploaded_inv:
        try:
            uploaded_inv.seek(0)
            try: raw_df = pd.read_csv(uploaded_inv, encoding='utf-8-sig')
            except: 
                uploaded_inv.seek(0)
                raw_df = pd.read_csv(uploaded_inv, encoding='big5')
            
            st.info(f"讀取到 {len(raw_df)} 筆資料")
            
            if st.button("🚨 強制對齊並還原 (解決空白問題)", type="primary"):
                st.session_state['inventory'] = robust_import(raw_df, force_position=True)
                save_inventory()
                st.success("還原成功！")
                time.sleep(1)
                st.rerun()
                
        except Exception as e: st.error(f"錯誤: {e}")

    st.divider()
    if st.button("🔴 重置系統 (清空所有資料)", type="secondary"):
        st.session_state.clear()
        st.rerun()

# ------------------------------------------
# 頁面 A
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "🛠️ 修改與盤點"])
    
    with tab1:
        inv_df = st.session_state['inventory']
        if not inv_df.empty:
            inv_df['label'] = inv_df.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_df['label'].tolist())
            
            rows = inv_df[inv_df['label'] == target]
            if not rows.empty:
                row = rows.iloc[0]
                idx = rows.index[0]
                
                with st.form("restock"):
                    st.write(f"目前庫存: **{row['庫存(顆)']}**")
                    c1, c2 = st.columns(2)
                    qty = c1.number_input("進貨數量", 1)
                    cost = c2.number_input("進貨總價", 0.0)
                    
                    if st.form_submit_button("📦 確認補貨"):
                        new_qty = float(row['庫存(顆)']) + qty
                        old_val = float(row['庫存(顆)']) * float(row['單顆成本'])
                        new_avg = (old_val + cost) / new_qty if new_qty > 0 else 0
                        
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = new_qty
                        st.session_state['inventory'].at[idx, '單顆成本'] = new_avg
                        st.session_state['inventory'].at[idx, '進貨日期'] = date.today()
                        save_inventory()
                        st.success("補貨完成")
                        st.rerun()
        else: st.info("無庫存")

    with tab2:
        with st.form("add"):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("分類", ["天然石", "配件", "耗材"])
            
            exist = []
            if not st.session_state['inventory'].empty:
                exist = sorted(st.session_state['inventory'][st.session_state['inventory']['分類']==cat]['名稱'].unique().tolist())
            name_sel = c2.selectbox("名稱", ["➕ 手動輸入"] + exist)
            name = st.text_input("輸入名稱") if name_sel == "➕ 手動輸入" else name_sel
            
            c3, c4 = st.columns(2)
            w = c3.number_input("寬度mm", 0.0, step=0.5)
            l = c4.number_input("長度mm", 0.0, step=0.5)
            
            c5, c6, c7 = st.columns(3)
            shape = c5.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            if shape == "➕ 手動輸入/新增": shape = st.text_input("輸入形狀")
            elem = c6.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS))
            if elem == "➕ 手動輸入/新增": elem = st.text_input("輸入五行")
            sup = c7.selectbox("廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS))
            if sup == "➕ 手動輸入/新增": sup = st.text_input("輸入廠商")
            
            c8, c9 = st.columns(2)
            price = c8.number_input("總價", 0.0)
            qty = c9.number_input("數量", 1)
            
            if st.form_submit_button("➕ 新增"):
                nid = generate_new_id(cat, st.session_state['inventory'])
                sl = l if l > 0 else (w if "圓" in shape else 0.0)
                new_item = {
                    '編號': nid, '分類': cat, '名稱': name,
                    '寬度mm': w, '長度mm': sl, '形狀': shape, '五行': elem,
                    '進貨總價': price, '進貨數量(顆)': qty, '進貨日期': date.today(),
                    '進貨廠商': sup, '庫存(顆)': qty, '單顆成本': price/qty if qty>0 else 0
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_item])], ignore_index=True)
                save_inventory()
                st.success(f"已新增 {name}")
                st.rerun()

    with tab3:
        if not st.session_state['inventory'].empty:
            df = st.session_state['inventory'].copy()
            df['label'] = df.apply(make_inventory_label, axis=1)
            target = st.selectbox("搜尋修改", df['label'])
            
            rows = df[df['label'] == target]
            if not rows.empty:
                orig = rows.iloc[0]
                mask = st.session_state['inventory']['編號'] == orig['編號']
                if mask.any():
                    idx = st.session_state['inventory'][mask].index[0]
                    
                    with st.form("edit"):
                        c1, c2, c3 = st.columns(3)
                        nm = c1.text_input("名稱", orig['名稱'])
                        wm = c2.number_input("寬度", value=float(orig['寬度mm']))
                        lm = c3.number_input("長度", value=float(orig['長度mm']))
                        
                        c4, c5, c6 = st.columns(3)
                        sh = c4.text_input("形狀", orig['形狀'])
                        el = c5.text_input("五行", orig['五行'])
                        sp = c6.text_input("廠商", orig['進貨廠商'])
                        
                        c7, c8 = st.columns(2)
                        # ★★★ 關鍵修復：這裡加了 int() 的安全轉換 ★★★
                        try:
                            current_stock = int(float(orig['庫存(顆)']))
                        except:
                            current_stock = 0
                            
                        qt = c7.number_input("庫存", value=current_stock)
                        co = c8.number_input("成本", value=float(orig['單顆成本']))
                        
                        if st.form_submit_button("💾 儲存"):
                            st.session_state['inventory'].at[idx, '名稱'] = nm
                            st.session_state['inventory'].at[idx, '寬度mm'] = wm
                            st.session_state['inventory'].at[idx, '長度mm'] = lm
                            st.session_state['inventory'].at[idx, '形狀'] = sh
                            st.session_state['inventory'].at[idx, '五行'] = el
                            st.session_state['inventory'].at[idx, '進貨廠商'] = sp
                            st.session_state['inventory'].at[idx, '庫存(顆)'] = qt
                            st.session_state['inventory'].at[idx, '單顆成本'] = co
                            
                            diff = qt - current_stock
                            if diff != 0:
                                log = {
                                    '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    '單號': 'AUDIT', '動作': '盤點修正',
                                    '編號': orig['編號'], '分類': orig['分類'], '名稱': nm,
                                    '規格': f"{wm}mm", '廠商': sp,
                                    '進貨數量': diff, '進貨總價': 0, '單價': co
                                }
                                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                            
                            save_inventory()
                            st.success("已更新")
                            time.sleep(1)
                            st.rerun()
                            
                    if st.button("🗑️ 刪除"):
                        st.session_state['inventory'] = st.session_state['inventory'].drop(idx).reset_index(drop=True)
                        save_inventory()
                        st.warning("已刪除")
                        st.rerun()
        else: st.info("無資料")

    st.divider()
    st.subheader("📋 庫存總表")
    if st.button("🔄 合併重複"):
        mdf, cnt = merge_inventory_duplicates(st.session_state['inventory'])
        st.session_state['inventory'] = mdf
        save_inventory()
        st.success(f"已合併 {cnt} 筆")
        st.rerun()
        
    vdf = st.session_state.get('inventory', pd.DataFrame())
    if not vdf.empty:
        vdf = vdf.sort_values(['分類', '名稱', '寬度mm', '編號'])
    st.dataframe(vdf, use_container_width=True, height=500, column_config={"進貨總價": st.column_config.NumberColumn(format="$%.2f"), "單顆成本": st.column_config.NumberColumn(format="$%.2f")})

# ------------------------------------------
# 頁面 B & C (簡化顯示)
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.dataframe(st.session_state['history'], use_container_width=True)

elif page == "🧮 設計與成本計算":
    st.subheader("🧮 設計")
    items = st.session_state['inventory']
    if not items.empty:
        eles = sorted(items['五行'].astype(str).unique())
        sel_e = st.multiselect("篩選", eles, default=eles)
        filt = items[items['五行'].isin(sel_e)].sort_values(['五行', '名稱'])
        
        if not filt.empty:
            filt['lbl'] = filt.apply(make_design_label, axis=1)
            c1, c2, c3 = st.columns([3, 1, 1])
            sel = c1.selectbox("選擇", filt['lbl'])
            qty = c2.number_input("數量", 1)
            if c3.button("⬇️ 加入"):
                r = filt[filt['lbl'] == sel].iloc[0]
                st.session_state['current_design'].append({
                    '編號': r['編號'], '名稱': r['名稱'], '五行': r['五行'],
                    '形狀': r['形狀'], '規格': f"{r['寬度mm']}mm", '廠商': r['進貨廠商'],
                    '單價': r['單顆成本'], '數量': qty, '小計': r['單顆成本']*qty
                })
                st.success("加入")
        
        if st.session_state['current_design']:
            df = pd.DataFrame(st.session_state['current_design'])
            st.dataframe(df)
            st.info(f"總成本: ${df['小計'].sum():.2f}")
            if st.button("✅ 售出"):
                for x in st.session_state['current_design']:
                    match = items[items['編號'] == x['編號']]
                    if not match.empty:
                        idx = match.index[0]
                        items.at[idx, '庫存(顆)'] -= x['數量']
                save_inventory()
                st.session_state['current_design'] = []
                st.success("完成")
                st.rerun()
            if st.button("🗑️ 清空"):
                st.session_state['current_design'] = []
                st.rerun()
