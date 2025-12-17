import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 設定與欄位定義
# ==========================================

# 系統標準欄位 (順序很重要)
COLUMNS = [
    '編號', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

# 歷史紀錄欄位
HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '編號', '分類', '名稱', '規格', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

# 設計銷售紀錄欄位
DESIGN_HISTORY_COLUMNS = [
    '單號', '日期', '總顆數', '材料成本', '工資', '雜支', 
    '總成本', '售價(x3)', '售價(x5)', '明細內容'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DESIGN_HISTORY_FILE = 'design_sales_history.csv'

DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶"]
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

def normalize_columns(df, force_order=False):
    """
    標準化欄位。
    force_order=True 時，不看標題，直接依順序塞入資料 (暴力對齊)。
    """
    
    # === 模式 A: 暴力對齊 (解決亂碼/標題不對的問題) ===
    if force_order:
        # 如果欄位數量不一致，先補齊或裁切
        current_cols = len(df.columns)
        target_cols = len(COLUMNS)
        
        if current_cols < target_cols:
            # 欄位太少，補空白
            for i in range(target_cols - current_cols):
                df[f'temp_{i}'] = ""
        elif current_cols > target_cols:
            # 欄位太多，只取前面幾個
            df = df.iloc[:, :target_cols]
            
        # 直接強制改名
        df.columns = COLUMNS
        
    # === 模式 B: 智慧對應 (標準模式) ===
    else:
        # 清理標題
        clean_cols = [str(col).strip().replace('\ufeff', '') for col in df.columns]
        df.columns = clean_cols

        rename_map = {
            'Code': '編號', 'ID': '編號', 'No': '編號', 'Product ID': '編號',
            'Category': '分類', 'Type': '分類',
            'Name': '名稱', 'Title': '名稱', 'Product Name': '名稱',
            'Width': '寬度mm', 'Size': '寬度mm', '寬度': '寬度mm',
            'Length': '長度mm', '長度': '長度mm',
            'Shape': '形狀', 'Element': '五行',
            'Price': '進貨總價', 'Cost': '進貨總價', 'Total': '進貨總價',
            'Qty': '進貨數量(顆)', 'Quantity': '進貨數量(顆)', 'Amount': '進貨數量(顆)',
            'Date': '進貨日期', 'Vendor': '進貨廠商', 'Supplier': '進貨廠商', '廠商': '進貨廠商',
            'Stock': '庫存(顆)', '庫存': '庫存(顆)',
            'Unit Cost': '單顆成本', 'Avg Cost': '單顆成本'
        }
        df = df.rename(columns=rename_map)
        
        # 補齊
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = 0 if ('mm' in col or '價' in col or '數量' in col or '成本' in col) else ""

    # === 通用清理：確保數字是數字，文字是文字 ===
    numeric_cols = ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    text_cols = ['編號', '分類', '名稱', '形狀', '五行', '進貨廠商']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('nan', '').replace('None', '').apply(lambda x: x.strip())

    return df[COLUMNS]

def generate_new_id(category, df):
    prefix = {'天然石': 'ST', '配件': 'AC', '耗材': 'OT'}.get(category, "OT")
    if df.empty or '編號' not in df.columns: return f"{prefix}0001"
    df_ids = df['編號'].astype(str)
    mask = df_ids.str.startswith(prefix, na=False)
    nums = df_ids[mask].str[2:].str.extract(r'(\d+)', expand=False).dropna().astype(int)
    next_num = 1 if nums.empty else nums.max() + 1
    return f"{prefix}{next_num:04d}"

def merge_inventory_duplicates(df):
    if df.empty: return df, 0
    group_cols = ['分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨廠商']
    if not set(group_cols).issubset(df.columns): return df, 0
    
    # 確保數值正確
    df['庫存(顆)'] = pd.to_numeric(df['庫存(顆)'], errors='coerce').fillna(0)
    df['單顆成本'] = pd.to_numeric(df['單顆成本'], errors='coerce').fillna(0)
    
    orig_cnt = len(df)
    df['總成本'] = df['庫存(顆)'] * df['單顆成本']
    
    agg = df.groupby(group_cols, as_index=False).agg({
        '庫存(顆)': 'sum', '總成本': 'sum', '進貨日期': 'max'
    })
    agg['單顆成本'] = agg.apply(lambda r: (r['總成本'] / r['庫存(顆)']) if r['庫存(顆)'] > 0 else 0, axis=1)
    agg = agg.drop(columns=['總成本'])
    
    # 保留編號
    df_sorted = df.sort_values('進貨日期', ascending=False)
    base = df_sorted.drop_duplicates(subset=group_cols, keep='first')[['編號'] + group_cols]
    
    final = pd.merge(agg, base, on=group_cols, how='left')
    return normalize_columns(final), orig_cnt - len(final)

def format_size(row):
    try:
        w, l = float(row.get('寬度mm', 0)), float(row.get('長度mm', 0))
        if w > 0: return f"{w}mm" if (l==0 or l==w) else f"{w}x{l}mm"
    except: pass
    return ""

def make_inventory_label(row):
    sz = format_size(row)
    sz_d = f"({sz})" if sz else ""
    return f"【{row['五行']}】 {row['編號']} | {row['名稱']} | {row['形狀']} {sz_d} | {row['進貨廠商']} | 存:{row['庫存(顆)']}"

def make_design_label(row):
    sz = format_size(row)
    sz_d = f"({sz})" if sz else ""
    return f"【{row['五行']}】{row['名稱']} | {row['形狀']} {sz_d} | {row['進貨廠商']} | ${float(row['單顆成本']):.2f}/顆 | 存:{row['庫存(顆)']}"

def get_dynamic_options(col, defaults):
    opts = set(defaults)
    if not st.session_state['inventory'].empty:
        exist = st.session_state['inventory'][col].dropna().unique().tolist()
        opts.update([str(x) for x in exist if str(x).strip()])
    return ["➕ 手動輸入/新增"] + sorted(list(opts))

# ==========================================
# 3. 初始化 Session State
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df = pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig')
            st.session_state['inventory'] = normalize_columns(df)
        except: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'design_history' not in st.session_state:
    try:
        st.session_state['design_history'] = pd.read_csv(DESIGN_HISTORY_FILE, encoding='utf-8-sig')
    except: st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)

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
    
    # 下載區
    if not st.session_state['inventory'].empty:
        csv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_{date.today()}.csv', "text/csv")
        
    if not st.session_state['design_history'].empty:
        d_csv = st.session_state['design_history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載訂單售出紀錄 (CSV)", d_csv, f'sales_{date.today()}.csv', "text/csv")
        
    st.divider()
    
    # ★★★ 強力修復上傳區 ★★★
    st.markdown("### 📤 資料還原")
    uploaded_inv = st.file_uploader("上傳庫存備份 (CSV)", type=['csv'])
    
    if uploaded_inv:
        try:
            uploaded_inv.seek(0)
            # 嘗試讀取檔案
            try:
                raw_df = pd.read_csv(uploaded_inv, encoding='utf-8-sig')
            except:
                uploaded_inv.seek(0)
                try: raw_df = pd.read_csv(uploaded_inv, encoding='big5')
                except: 
                    uploaded_inv.seek(0)
                    raw_df = pd.read_csv(uploaded_inv, engine='python')
            
            st.warning("請檢查下方預覽，如果欄位是亂碼或空白，請按「強制對齊」按鈕。")
            st.dataframe(raw_df.head(3), use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 標準還原 (建議先試這個)"):
                    st.session_state['inventory'] = normalize_columns(raw_df, force_order=False)
                    save_inventory()
                    st.success("還原成功！")
                    time.sleep(1)
                    st.rerun()
            with col2:
                if st.button("⚠️ 強制使用欄位順序對齊"):
                    st.session_state['inventory'] = normalize_columns(raw_df, force_order=True)
                    save_inventory()
                    st.success("已強制對齊並還原！")
                    time.sleep(1)
                    st.rerun()
                    
        except Exception as e: st.error(f"讀取錯誤: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "🛠️ 修改與盤點"])
    
    # Tab 1
    with tab1:
        inv_df = st.session_state['inventory']
        if not inv_df.empty:
            inv_df['label'] = inv_df.apply(make_inventory_label, axis=1)
            target_label = st.selectbox("選擇商品", inv_df['label'].tolist())
            target_rows = inv_df[inv_df['label'] == target_label]
            
            if not target_rows.empty:
                target_row = target_rows.iloc[0]
                target_idx = target_rows.index[0]
                with st.form("restock"):
                    st.write(f"目前庫存: **{target_row['庫存(顆)']}**")
                    c1, c2 = st.columns(2)
                    qty = c1.number_input("進貨數量", 1)
                    cost = c2.number_input("進貨總價", 0.0, format="%.2f")
                    if st.form_submit_button("📦 確認補貨"):
                        new_qty = target_row['庫存(顆)'] + qty
                        old_val = target_row['庫存(顆)'] * target_row['單顆成本']
                        new_avg = (old_val + cost) / new_qty if new_qty > 0 else 0
                        st.session_state['inventory'].at[target_idx, '庫存(顆)'] = new_qty
                        st.session_state['inventory'].at[target_idx, '單顆成本'] = new_avg
                        st.session_state['inventory'].at[target_idx, '進貨日期'] = date.today()
                        
                        log = {
                            '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                            '單號': 'RESTOCK', '動作': '補貨',
                            '編號': target_row['編號'], '分類': target_row['分類'], '名稱': target_row['名稱'],
                            '規格': format_size(target_row), '廠商': target_row['進貨廠商'],
                            '進貨數量': qty, '進貨總價': cost, '單價': cost/qty if qty>0 else 0
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                        save_inventory()
                        st.success("成功！")
                        st.rerun()
            else: st.warning("請重新選擇")
        else: st.info("無庫存")

    # Tab 2
    with tab2:
        with st.container():
            st.markdown("##### 1. 基本資料")
            c1, c2 = st.columns([1, 2])
            with c1: new_cat = st.selectbox("分類", ["天然石", "配件", "耗材"])
            with c2:
                exist_names = sorted(st.session_state['inventory'][st.session_state['inventory']['分類'] == new_cat]['名稱'].unique().tolist()) if not st.session_state['inventory'].empty else []
                name_sel = st.selectbox("名稱", ["➕ 手動輸入/新增"] + exist_names)
                final_name = st.text_input("↳ 新名稱") if name_sel == "➕ 手動輸入/新增" else name_sel

            st.markdown("##### 2. 規格 (mm)")
            c3a, c3b = st.columns(2)
            with c3a:
                w_sel = st.selectbox("寬度", get_dynamic_options('寬度mm', []))
                fw = st.number_input("↳ 輸入", 0.0, step=0.5) if w_sel == "➕ 手動輸入/新增" else float(w_sel)
            with c3b: fl = st.number_input("長度 (圓珠不填)", 0.0, step=0.5)

        with st.form("add"):
            st.markdown("##### 3. 詳細資訊")
            c4, c5, c6 = st.columns(3)
            with c4: 
                s_sel = st.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
                f_shape = st.text_input("↳ 新形狀") if s_sel == "➕ 手動輸入/新增" else s_sel
            with c5: 
                e_sel = st.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS))
                f_elem = st.text_input("↳ 新五行") if e_sel == "➕ 手動輸入/新增" else e_sel
            with c6: 
                p_sel = st.selectbox("廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS))
                f_sup = st.text_input("↳ 新廠商") if p_sel == "➕ 手動輸入/新增" else p_sel

            c7, c8, c9 = st.columns(3)
            with c7: price = st.number_input("總價", 0.0, format="%.2f")
            with c8: qty = st.number_input("數量", 1)
            with c9: p_date = st.date_input("日期", value=date.today())
            
            if st.form_submit_button("➕ 新增入庫"):
                sl = fl if fl > 0 else (fw if "圓" in f_shape else 0.0)
                nid = generate_new_id(new_cat, st.session_state['inventory'])
                new_row = {
                    '編號': nid, '分類': new_cat, '名稱': final_name, 
                    '寬度mm': fw, '長度mm': sl, '形狀': f_shape, '五行': f_elem, 
                    '進貨總價': price, '進貨數量(顆)': qty, '進貨日期': p_date, '進貨廠商': f_sup,
                    '庫存(顆)': qty, '單顆成本': price/qty if qty>0 else 0
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_row])], ignore_index=True)
                save_inventory()
                st.success(f"已新增：{final_name}")
                time.sleep(1)
                st.rerun()

    # Tab 3
    with tab3:
        inv_df = st.session_state['inventory']
        if not inv_df.empty:
            edit_df = inv_df.copy()
            edit_df['label'] = edit_df.apply(make_inventory_label, axis=1)
            sel_label = st.selectbox("🔍 搜尋商品", edit_df['label'].tolist())
            
            target_subset = edit_df[edit_df['label'] == sel_label]
            if not target_subset.empty:
                orig_row = target_subset.iloc[0]
                # 這裡修正語法，使用安全的 index 獲取
                real_inv = st.session_state['inventory']
                # 找出符合編號的索引
                match_indices = real_inv[real_inv['編號'] == orig_row['編號']].index
                
                if not match_indices.empty:
                    orig_idx = match_indices[0]
                    with st.form("edit"):
                        c1, c2, c3 = st.columns(3)
                        with c1: ename = st.text_input("名稱", orig_row['名稱'])
                        with c2: ew = st.number_input("寬度", float(orig_row['寬度mm']))
                        with c3: el = st.number_input("長度", float(orig_row['長度mm']))
                        
                        c4, c5, c6 = st.columns(3)
                        
                        # Helper to handle options safely
                        def safe_idx(opts, val):
                            try: return opts.index(val) + 1
                            except: return 0
                            
                        shp_opts = get_dynamic_options('形狀', DEFAULT_SHAPES)
                        elm_opts = get_dynamic_options('五行', DEFAULT_ELEMENTS)
                        sup_opts = get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS)

                        # 使用 text_input 預設值，如果想改用 selectbox 請自行調整
                        with c4: eshape = st.text_input("形狀", orig_row['形狀'])
                        with c5: eelem = st.text_input("五行", orig_row['五行'])
                        with c6: esup = st.text_input("廠商", orig_row['進貨廠商'])

                        st.divider()
                        c7, c8 = st.columns(2)
                        old_qty = int(float(orig_row['庫存(顆)']))
                        with c7: estock = st.number_input(f"庫存 (原:{old_qty})", value=old_qty)
                        with c8: ecost = st.number_input("成本", float(orig_row['單顆成本']), format="%.2f")
                        
                        diff = estock - old_qty
                        if diff != 0: st.caption(f"⚠️ 差異: {diff}")

                        b1, b2 = st.columns(2)
                        with b1:
                            if st.form_submit_button("💾 儲存盤點"):
                                st.session_state['inventory'].at[orig_idx, '名稱'] = ename
                                st.session_state['inventory'].at[orig_idx, '寬度mm'] = ew
                                st.session_state['inventory'].at[orig_idx, '長度mm'] = el
                                st.session_state['inventory'].at[orig_idx, '形狀'] = eshape
                                st.session_state['inventory'].at[orig_idx, '五行'] = eelem
                                st.session_state['inventory'].at[orig_idx, '進貨廠商'] = esup
                                st.session_state['inventory'].at[orig_idx, '庫存(顆)'] = estock
                                st.session_state['inventory'].at[orig_idx, '單顆成本'] = ecost
                                
                                act = '盤點修正' if diff != 0 else '修改資料'
                                log = {
                                    '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    '單號': 'AUDIT', '動作': act,
                                    '編號': orig_row['編號'], '分類': orig_row['分類'], '名稱': ename,
                                    '規格': f"{ew}mm", '廠商': esup,
                                    '進貨數量': diff, '進貨總價': 0, '單價': ecost
                                }
                                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                                save_inventory()
                                st.success("已更新")
                                time.sleep(1)
                                st.rerun()
                        with b2:
                            if st.form_submit_button("🗑️ 刪除"):
                                st.session_state['inventory'] = st.session_state['inventory'].drop(orig_idx).reset_index(drop=True)
                                save_inventory()
                                st.success("已刪除")
                                time.sleep(1)
                                st.rerun()
                else: st.warning("找不到此商品")
        else: st.info("無庫存")

    st.divider()
    c1, c2 = st.columns([3, 1])
    with c1: st.markdown("### 📋 庫存總表")
    with c2:
        if st.button("🔄 合併重複"):
            mdf, cnt = merge_inventory_duplicates(st.session_state['inventory'])
            st.session_state['inventory'] = mdf
            save_inventory()
            st.success(f"已合併 {cnt}")
            time.sleep(1)
            st.rerun()

    df_view = st.session_state.get('inventory', pd.DataFrame())
    if not df_view.empty:
        df_view = df_view.sort_values(['分類', '名稱', '寬度mm'])
        
    all_txt = sorted(list(set(df_view.astype(str).values.flatten())))
    search = st.multiselect("🔍 搜尋", [x for x in all_txt if x and x!='nan'])
    
    if search:
        mask = df_view.astype(str).apply(lambda x: all(k in " ".join(x) for k in search), axis=1)
        df_view = df_view[mask]
        
    st.dataframe(df_view, use_container_width=True, height=400,
                 column_config={"進貨總價": st.column_config.NumberColumn(format="$%.2f"),
                                "單顆成本": st.column_config.NumberColumn(format="$%.2f")})

# ------------------------------------------
# 頁面 B: 紀錄
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 紀錄")
    t1, t2 = st.tabs(["流水帳", "訂單"])
    
    with t1:
        df = st.session_state['history'].copy()
        if '單號' in df.columns:
            cols = df.columns.tolist()
            cols.remove('單號'); cols.insert(1, '單號')
            df = df[cols]
        
        df.insert(0, "刪除", False)
        edf = st.data_editor(df, column_config={"刪除": st.column_config.CheckboxColumn(default=False)}, disabled=df.columns[1:], use_container_width=True)
        
        if st.button("🗑️ 刪除並還原"):
            dels = edf[edf['刪除']]
            if not dels.empty:
                for _, r in dels.iterrows():
                    match = st.session_state['inventory'][st.session_state['inventory']['編號'] == r['編號']]
                    if not match.empty:
                        idx = match.index[0]
                        cur = float(st.session_state['inventory'].at[idx, '庫存(顆)'])
                        chg = float(r['進貨數量'])
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = max(0, cur - chg)
                
                st.session_state['history'] = edf[~edf['刪除']].drop(columns=['刪除'])
                save_inventory()
                st.success("已還原")
                time.sleep(1)
                st.rerun()

    with t2:
        st.dataframe(st.session_state['design_history'], use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 設計")
    items = st.session_state['inventory']
    
    if not items.empty:
        eles = sorted(items['五行'].astype(str).unique())
        sel_e = st.multiselect("篩選五行", eles, default=eles)
        filt = items[items['五行'].isin(sel_e)].sort_values(['五行', '名稱'])
        
        if not filt.empty:
            filt['lbl'] = filt.apply(make_design_label, axis=1)
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1: sel = st.selectbox("選擇", filt['lbl'])
            with c2: qty = st.number_input("數量", 1)
            with c3: 
                st.write("")
                st.write("")
                if st.button("⬇️ 加入", type="primary"):
                    r = filt[filt['lbl'] == sel].iloc[0]
                    st.session_state['current_design'].append({
                        '編號': r['編號'], '名稱': r['名稱'], '五行': r['五行'],
                        '形狀': r['形狀'], '規格': format_size(r), '廠商': r['進貨廠商'],
                        '單價': r['單顆成本'], '數量': qty, '小計': r['單顆成本']*qty
                    })
                    st.success("加入成功")
            
            st.divider()
            
            if st.session_state['current_design']:
                dlist = st.session_state['current_design']
                dels = []
                mcost = 0
                for i, x in enumerate(dlist):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1: st.write(f"【{x['五行']}】{x['名稱']} ({x['規格']})")
                    with c2: st.write(f"${x['單價']:.2f} x {x['數量']}")
                    with c3: st.write(f"= ${x['小計']:.2f}")
                    with c4: 
                        if st.button("🗑️", key=f"d{i}"): dels.append(i)
                    mcost += x['小計']
                
                if dels:
                    for i in sorted(dels, reverse=True): del st.session_state['current_design'][i]
                    st.rerun()
                
                st.divider()
                c1, c2 = st.columns(2)
                with c1: labor = st.number_input("工資", 0, step=10)
                with c2: misc = st.number_input("雜支", 0, step=5)
                
                tot = mcost + labor + misc
                st.info(f"總成本: ${tot:.2f} (建議售價 x3: ${tot*3:.0f})")
                
                if st.button("✅ 售出 (扣庫存)", type="primary"):
                    oid = f"S-{datetime.now().strftime('%m%d-%H%M')}"
                    dets = []
                    for x in dlist:
                        match = items[items['編號'] == x['編號']]
                        if not match.empty:
                            idx = match.index[0]
                            cur = items.at[idx, '庫存(顆)']
                            items.at[idx, '庫存(顆)'] = cur - x['數量']
                            dets.append(f"{x['名稱']}x{x['數量']}")
                            
                            log = {
                                '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                '單號': oid, '動作': '售出',
                                '編號': x['編號'], '分類': '設計', '名稱': x['名稱'],
                                '規格': x['規格'], '廠商': '售出',
                                '進貨數量': -x['數量'], '進貨總價': 0, '單價': x['單價']
                            }
                            st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    
                    dlog = {
                        '單號': oid, '日期': date.today(), '總顆數': sum(x['數量'] for x in dlist),
                        '材料成本': mcost, '工資': labor, '雜支': misc,
                        '總成本': tot, '售價(x3)': tot*3, '售價(x5)': tot*5, '明細內容': "|".join(dets)
                    }
                    st.session_state['design_history'] = pd.concat([st.session_state['design_history'], pd.DataFrame([dlog])], ignore_index=True)
                    
                    save_inventory(); save_design_history()
                    st.session_state['current_design'] = []
                    st.success("完成！")
                    time.sleep(1)
                    st.rerun()
