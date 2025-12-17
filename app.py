import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心邏輯與設定區
# ==========================================

# 系統標準欄位
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

# 預設選單資料
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

# ==========================================
# 2. 核心邏輯函式
# ==========================================

def save_inventory():
    """儲存庫存"""
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def save_design_history():
    """儲存銷售紀錄"""
    try:
        if 'design_history' in st.session_state:
            st.session_state['design_history'].to_csv(DESIGN_HISTORY_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def normalize_columns(df):
    """標準化欄位名稱並強制修復數據格式 (終極防呆版)"""
    
    # 1. 清理欄位名稱：轉字串 -> 去除前後空白 -> 移除 BOM 亂碼
    # 使用列表推導式，這是最穩定不報錯的寫法
    clean_cols = [str(col).strip().replace('\ufeff', '') for col in df.columns]
    df.columns = clean_cols

    # 2. 建立「同義詞字典」
    # 您的檔案已經是正確的中文，所以這裡主要是防呆
    rename_map = {
        'Code': '編號', 'ID': '編號', 'No': '編號',
        'Category': '分類', 'Type': '分類',
        'Name': '名稱', 'Title': '名稱',
        'Width': '寬度mm', 'Size': '寬度mm', '寬度': '寬度mm',
        'Length': '長度mm', '長度': '長度mm',
        'Shape': '形狀', 'Element': '五行',
        'Price': '進貨總價', 'Cost': '進貨總價',
        'Qty': '進貨數量(顆)', 'Quantity': '進貨數量(顆)',
        'Date': '進貨日期', 'Vendor': '進貨廠商', 'Supplier': '進貨廠商',
        'Stock': '庫存(顆)', '庫存': '庫存(顆)',
        'Unit Cost': '單顆成本', 'Avg Cost': '單顆成本'
    }
    df = df.rename(columns=rename_map)
    
    # 3. 補齊缺少的欄位
    for col in COLUMNS:
        if col not in df.columns:
            if 'mm' in col or '價' in col or '數量' in col or '成本' in col:
                df[col] = 0
            else:
                df[col] = ""
            
    # 4. 強制轉型：數值欄位 (解決 nan Error)
    numeric_cols = ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 5. 強制轉型：文字欄位 (解決 AttributeError)
    text_cols = ['編號', '分類', '名稱', '形狀', '五行', '進貨廠商']
    for col in text_cols:
        if col in df.columns:
            # 確保是字串，且去除 nan 和空白
            df[col] = df[col].astype(str).replace('nan', '').replace('None', '').apply(lambda x: x.strip())

    # 只回傳系統需要的標準欄位
    return df[COLUMNS]

def generate_new_id(category, df):
    prefix_map = {'天然石': 'ST', '配件': 'AC', '耗材': 'OT'}
    prefix = prefix_map.get(category, "OT")
    if df.empty or '編號' not in df.columns: return f"{prefix}0001"
    df_ids = df['編號'].astype(str)
    mask = df_ids.str.startswith(prefix, na=False)
    numeric_part = df_ids[mask].str[2:].str.extract(r'(\d+)', expand=False).dropna()
    if numeric_part.empty: next_num = 1
    else: next_num = numeric_part.astype(int).max() + 1
    return f"{prefix}{next_num:04d}"

def merge_inventory_duplicates(df):
    if df.empty: return df, 0
    group_cols = ['分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨廠商']
    if not set(group_cols).issubset(df.columns): return df, 0
    
    work_df = df.copy()
    work_df['庫存(顆)'] = pd.to_numeric(work_df['庫存(顆)'], errors='coerce').fillna(0)
    work_df['單顆成本'] = pd.to_numeric(work_df['單顆成本'], errors='coerce').fillna(0)
    original_count = len(work_df)
    
    work_df['總成本'] = work_df['庫存(顆)'] * work_df['單顆成本']
    
    agg = work_df.groupby(group_cols, as_index=False).agg({
        '庫存(顆)': 'sum', '總成本': 'sum', '進貨日期': 'max'
    })
    agg['單顆成本'] = agg.apply(lambda r: (r['總成本'] / r['庫存(顆)']) if r['庫存(顆)'] > 0 else 0, axis=1)
    agg = agg.drop(columns=['總成本'])
    
    work_df['進貨日期_排序'] = pd.to_datetime(work_df['進貨日期'], errors='coerce')
    base_rows = work_df.sort_values(['進貨日期_排序', '編號'], ascending=[False, False]).groupby(group_cols, as_index=False).first()
    
    final_df = pd.merge(agg, base_rows[['編號'] + group_cols], on=group_cols, how='left')
    return normalize_columns(final_df), original_count - len(final_df)

def format_size(row):
    try:
        w = float(row.get('寬度mm', 0))
        l = float(row.get('長度mm', 0))
        if w > 0:
            if l == 0 or l == w: return f"{w}mm"
            else: return f"{w}x{l}mm"
    except: pass
    return ""

def make_inventory_label(row):
    size_str = format_size(row)
    size_disp = f"({size_str})" if size_str else ""
    shape_str = str(row.get('形狀', '')).strip()
    supplier = str(row.get('進貨廠商', '')).strip()
    return f"【{str(row['五行'])}】 {str(row['編號'])} | {str(row['名稱'])} | {shape_str} {size_disp} | {supplier} | 存:{row['庫存(顆)']}"

def make_design_label(row):
    size_str = format_size(row)
    size_disp = f"({size_str})" if size_str else ""
    shape_str = str(row.get('形狀', '')).strip()
    supplier = str(row.get('進貨廠商', '')).strip()
    return f"【{str(row['五行'])}】{str(row['名稱'])} | {shape_str} {size_disp} | {supplier} | ${float(row['單顆成本']):.2f}/顆 | 存:{row['庫存(顆)']}"

def get_dynamic_options(column_name, default_list):
    options = set(default_list)
    if not st.session_state['inventory'].empty:
        if column_name in st.session_state['inventory'].columns:
            existing = st.session_state['inventory'][column_name].dropna().unique().tolist()
            options.update([str(x) for x in existing if str(x).strip() != ""])
    return ["➕ 手動輸入/新增"] + sorted(list(options))

# ==========================================
# 3. 初始化 Session State
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df = pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig')
            st.session_state['inventory'] = normalize_columns(df)
        except:
            st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'inventory' in st.session_state:
    st.session_state['inventory'] = normalize_columns(st.session_state['inventory'])

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
else:
    if '單號' not in st.session_state['history'].columns:
        st.session_state['history'].insert(1, '單號', '')

if 'design_history' not in st.session_state:
    if os.path.exists(DESIGN_HISTORY_FILE):
        try:
            st.session_state['design_history'] = pd.read_csv(DESIGN_HISTORY_FILE, encoding='utf-8-sig')
        except: st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)
    else: st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)

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
    
    # 下載區域
    if not st.session_state['inventory'].empty:
        csv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_{date.today()}.csv', "text/csv")
        
    if not st.session_state['design_history'].empty:
        d_csv = st.session_state['design_history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載訂單售出紀錄 (CSV)", d_csv, f'sales_{date.today()}.csv', "text/csv")
        
    st.divider()
    
    # ★★★ 修改：檔案上傳區加入「診斷預覽」功能 ★★★
    uploaded_inv = st.file_uploader("📤 上傳庫存備份 (CSV)", type=['csv'])
    if uploaded_inv:
        try:
            uploaded_inv.seek(0)
            try:
                # 優先嘗試 utf-8-sig (Excel 標準)
                raw_df = pd.read_csv(uploaded_inv, encoding='utf-8-sig')
            except:
                uploaded_inv.seek(0)
                try:
                    # 嘗試 big5 (中文舊版)
                    raw_df = pd.read_csv(uploaded_inv, encoding='big5')
                except:
                    uploaded_inv.seek(0)
                    # 嘗試 default engine='python'
                    raw_df = pd.read_csv(uploaded_inv, engine='python')
            
            with st.expander("📊 檔案診斷報告 (若資料空白請點開檢查)", expanded=True):
                st.warning("請檢查下方的「原始欄位名稱」是否正確顯示中文？")
                st.write("**電腦讀取到的欄位名稱：**", raw_df.columns.tolist())
                st.write("**檔案前 3 筆資料預覽：**")
                st.dataframe(raw_df.head(3), use_container_width=True)

            if st.button("確認還原此檔案"):
                st.session_state['inventory'] = normalize_columns(raw_df)
                save_inventory()
                st.success("✅ 庫存還原成功！")
                time.sleep(1)
                st.rerun()
                
        except Exception as e: st.error(f"讀取失敗: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "🛠️ 修改與盤點"])
    
    # === Tab 1: 補貨 ===
    with tab1:
        st.caption("已有編號商品補貨")
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
                    batch_no = st.text_input("進貨單號 (選填)", placeholder="Auto")
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
                            '單號': batch_no if batch_no else f"AUTO-{int(time.time())}",
                            '動作': '補貨',
                            '編號': target_row['編號'], '分類': target_row['分類'], '名稱': target_row['名稱'],
                            '規格': format_size(target_row), '廠商': target_row['進貨廠商'],
                            '進貨數量': qty, '進貨總價': cost, '單價': cost/qty if qty>0 else 0
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                        save_inventory()
                        st.success("補貨成功！")
                        st.rerun()
            else: st.warning("無法讀取此商品資料，請重新整理。")
        else: st.info("無庫存")

    # === Tab 2: 建立新商品 ===
    with tab2:
        with st.container():
            st.markdown("##### 1. 基本資料")
            c1, c2 = st.columns([1, 2])
            with c1: 
                new_cat = st.selectbox("分類 (產生編號用)", ["天然石", "配件", "耗材"])
            with c2:
                existing_names = []
                if not st.session_state['inventory'].empty:
                    cat_df = st.session_state['inventory'][st.session_state['inventory']['分類'] == new_cat]
                    existing_names = sorted(cat_df['名稱'].dropna().unique().astype(str).tolist())
                name_opts = ["➕ 手動輸入/新增"] + existing_names
                name_sel = st.selectbox("名稱", name_opts)
                final_name = st.text_input("↳ 輸入新名稱") if name_sel == "➕ 手動輸入/新增" else name_sel

            st.markdown("##### 2. 規格尺寸 (mm)")
            c3a, c3b = st.columns(2)
            with c3a:
                w_opts = get_dynamic_options('寬度mm', [])
                w_sel = st.selectbox("寬度/直徑", w_opts)
                final_w = st.number_input("↳ 輸入寬度", 0.0, step=0.5) if w_sel == "➕ 手動輸入/新增" else float(w_sel)
            with c3b:
                final_l = st.number_input("長度 (圓珠可不填)", 0.0, step=0.5)
                if final_l == 0.0 and final_w > 0: st.caption(f"預設為 {final_w}")

        prev_row = None
        if final_name and not st.session_state['inventory'].empty:
            same_name_df = st.session_state['inventory'][(st.session_state['inventory']['分類'] == new_cat) & (st.session_state['inventory']['名稱'] == final_name)]
            if not same_name_df.empty:
                prev_row = same_name_df.iloc[-1]

        with st.form("add_new"):
            st.markdown("##### 3. 詳細資訊")
            batch_id_new = st.text_input("進貨單號 (選填)", placeholder="Auto")

            shape_opts = get_dynamic_options('形狀', DEFAULT_SHAPES)
            elem_opts = get_dynamic_options('五行', DEFAULT_ELEMENTS)
            sup_opts = get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS)
            
            def get_idx(opts, val):
                try: return opts.index(val)
                except: return 0

            idx_s = get_idx(shape_opts, prev_row['形狀']) if prev_row is not None and '形狀' in prev_row else 0
            idx_e = get_idx(elem_opts, prev_row['五行']) if prev_row is not None else 0
            idx_p = get_idx(sup_opts, prev_row['進貨廠商']) if prev_row is not None else 0

            c4, c5, c6 = st.columns(3)
            with c4: s_sel = st.selectbox("形狀", shape_opts, index=idx_s)
            with c5: e_sel = st.selectbox("五行", elem_opts, index=idx_e)
            with c6: p_sel = st.selectbox("廠商", sup_opts, index=idx_p)
            
            mc1, mc2, mc3 = st.columns(3)
            final_shape = mc1.text_input("↳ 新形狀") if s_sel == "➕ 手動輸入/新增" else s_sel
            final_elem = mc2.text_input("↳ 新五行") if e_sel == "➕ 手動輸入/新增" else e_sel
            final_sup = mc3.text_input("↳ 新廠商") if p_sel == "➕ 手動輸入/新增" else p_sel

            c7, c8, c9 = st.columns(3)
            with c7: 
                price = st.number_input("進貨總價", 0.0, format="%.2f")
            with c8: qty = st.number_input("進貨數量", 1)
            with c9: p_date = st.date_input("進貨日期", value=date.today())
            
            if st.form_submit_button("➕ 確認新增入庫", type="primary"):
                if not all([final_name, final_shape, final_elem, final_sup]):
                    st.error("❌ 請填寫完整欄位")
                else:
                    save_l = final_l if final_l > 0 else (final_w if "圓" in final_shape or "珠" in final_shape else 0.0)
                    new_id = generate_new_id(new_cat, st.session_state['inventory'])
                    unit_cost = price / qty if qty > 0 else 0
                    
                    new_row = {
                        '編號': new_id, '分類': new_cat, '名稱': final_name, 
                        '寬度mm': final_w, '長度mm': save_l,
                        '形狀': final_shape, '五行': final_elem, 
                        '進貨總價': price, '進貨數量(顆)': qty, 
                        '進貨日期': p_date, '進貨廠商': final_sup,
                        '庫存(顆)': qty, '單顆成本': unit_cost
                    }
                    st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_row])], ignore_index=True)
                    
                    log = {
                        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        '單號': batch_id_new if batch_id_new else f"AUTO-{int(time.time())}", 
                        '動作': '進貨',
                        '編號': new_id, '分類': new_cat, '名稱': final_name,
                        '規格': f"{final_w}x{save_l}mm", '形狀': final_shape,
                        '廠商': final_sup, '進貨數量': qty, '進貨總價': price, '單價': unit_cost
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    save_inventory()
                    st.success(f"✅ 已新增：{final_name} - {new_id}")
                    time.sleep(1)
                    st.rerun()

    # === Tab 3: 修改與盤點 ===
    with tab3:
        st.markdown("##### 🛠️ 修正或盤點")
        if not st.session_state['inventory'].empty:
            edit_df = st.session_state['inventory'].copy()
            edit_df['label'] = edit_df.apply(make_inventory_label, axis=1)
            sel_label = st.selectbox("🔍 選擇要修改的商品", edit_df['label'].tolist())
            
            target_subset = edit_df[edit_df['label'] == sel_label]
            
            if not target_subset.empty:
                orig_row = target_subset.iloc[0]
                target_id = orig_row['編號']
                
                matching_inv = st.session_state['inventory'][st.session_state['inventory']['編號'] == target_id]
                
                if not matching_inv.empty:
                    orig_idx = matching_inv.index[0]

                    with st.form("edit_form"):
                        st.info(f"編輯中：{orig_row['編號']}")
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1: ename = st.text_input("名稱", value=orig_row['名稱'])
                        with ec2: ewidth = st.number_input("寬度mm", value=float(orig_row['寬度mm']), step=0.1)
                        with ec3: elength = st.number_input("長度mm", value=float(orig_row['長度mm']), step=0.1)

                        shp_opts = get_dynamic_options('形狀', DEFAULT_SHAPES)
                        elm_opts = get_dynamic_options('五行', DEFAULT_ELEMENTS)
                        sup_opts = get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS)
                        
                        def get_eidx(opts, val):
                            try: return opts.index(val)
                            except: return 0

                        ec4, ec5, ec6 = st.columns(3)
                        current_shape = orig_row['形狀'] if '形狀' in orig_row else ''
                        with ec4: eshp_sel = st.selectbox("形狀", shp_opts, index=get_eidx(shp_opts, current_shape))
                        with ec5: eelm_sel = st.selectbox("五行", elm_opts, index=get_eidx(elm_opts, orig_row['五行']))
                        with ec6: esup_sel = st.selectbox("廠商", sup_opts, index=get_eidx(sup_opts, orig_row['進貨廠商']))

                        em1, em2, em3 = st.columns(3)
                        eshape = em1.text_input("↳ 新形狀") if eshp_sel == "➕ 手動輸入/新增" else eshp_sel
                        eelem = em2.text_input("↳ 新五行") if eelm_sel == "➕ 手動輸入/新增" else eelm_sel
                        esup = em3.text_input("↳ 新廠商") if esup_sel == "➕ 手動輸入/新增" else esup_sel

                        st.divider()
                        ec7, ec8 = st.columns(2)
                        
                        try:
                            old_qty = int(float(orig_row['庫存(顆)']))
                        except: old_qty = 0

                        with ec7: 
                            estock = st.number_input(f"庫存數量 (盤點前: {old_qty})", value=old_qty, step=1)
                        with ec8: 
                            ecost = st.number_input("單顆成本", value=float(orig_row['單顆成本']), step=0.1, format="%.2f")

                        qty_diff = estock - old_qty
                        if qty_diff != 0:
                            st.caption(f"⚠️ 庫存將調整: {qty_diff:+d} 顆")

                        bt1, bt2 = st.columns([1, 1])
                        with bt1:
                            if st.form_submit_button("💾 儲存修改 / 確認盤點"):
                                st.session_state['inventory'].at[orig_idx, '名稱'] = ename
                                st.session_state['inventory'].at[orig_idx, '寬度mm'] = ewidth
                                st.session_state['inventory'].at[orig_idx, '長度mm'] = elength
                                st.session_state['inventory'].at[orig_idx, '形狀'] = eshape
                                st.session_state['inventory'].at[orig_idx, '五行'] = eelem
                                st.session_state['inventory'].at[orig_idx, '進貨廠商'] = esup
                                st.session_state['inventory'].at[orig_idx, '庫存(顆)'] = estock
                                st.session_state['inventory'].at[orig_idx, '單顆成本'] = ecost
                                
                                if qty_diff != 0:
                                    action_type = '盤點修正'
                                    action_note = f"盤點調整 {qty_diff:+d}"
                                else:
                                    action_type = '資料更新'
                                    action_note = "修改資料內容"

                                log = {
                                    '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), 
                                    '單號': 'AUDIT' if qty_diff != 0 else 'EDIT', 
                                    '動作': action_type,
                                    '編號': orig_row['編號'], '分類': orig_row['分類'], '名稱': ename,
                                    '規格': f"{ewidth}x{elength}mm ({action_note})", 
                                    '形狀': eshape,
                                    '廠商': esup, 
                                    '進貨數量': qty_diff, 
                                    '進貨總價': 0, 
                                    '單價': ecost
                                }
                                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                                save_inventory()
                                
                                st.success("✅ 更新成功")
                                time.sleep(1)
                                st.rerun()

                        with bt2:
                            if st.form_submit_button("🗑️ 刪除商品", type="primary"):
                                st.session_state['inventory'] = st.session_state['inventory'].drop(orig_idx).reset_index(drop=True)
                                save_inventory()
                                st.success("已刪除")
                                time.sleep(1)
                                st.rerun()
                else:
                    st.warning("⚠️ 查無此商品資料 (可能因資料還原導致索引變更)，請嘗試重新整理頁面。")
            else:
                st.info("請選擇要編輯的商品")
        else: st.info("無資料")

    st.divider()
    c_list1, c_list2 = st.columns([3, 1])
    with c_list1: st.markdown("### 📋 庫存總表")
    with c_list2:
        if st.button("🔄 合併重複項目"):
            mdf, cnt = merge_inventory_duplicates(st.session_state['inventory'])
            st.session_state['inventory'] = mdf
            save_inventory()
            st.success(f"已合併 {cnt} 筆")
            time.sleep(1)
            st.rerun()

    # 搜尋與顯示
    df_source = st.session_state.get('inventory', pd.DataFrame())
    if not df_source.empty:
        df_source = df_source.sort_values(
            by=['分類', '名稱', '寬度mm', '編號'],
            ascending=[True, True, True, True]
        ).reset_index(drop=True)

    search_options = sorted(list(set(df_source.astype(str).values.flatten())))
    search_options = [x for x in search_options if x not in ['nan', '', 'None']]
    
    selected_tags = st.multiselect("🔍 萬用搜尋", options=search_options)
    
    if selected_tags and not df_source.empty:
        mask = df_source.astype(str).apply(
            lambda row: all(tag in " ".join(row.values) for tag in selected_tags), axis=1
        )
        disp_df = df_source[mask]
    else:
        disp_df = df_source
    
    st.dataframe(disp_df, use_container_width=True, height=400,
                 column_config={
                     "進貨總價": st.column_config.NumberColumn(format="$%.2f"),
                     "單顆成本": st.column_config.NumberColumn(format="$%.2f"),
                     "寬度mm": st.column_config.NumberColumn(format="%.1f"),
                     "長度mm": st.column_config.NumberColumn(format="%.1f")
                 })

# ------------------------------------------
# 頁面 B: 紀錄
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 歷史紀錄中心")
    tab_log, tab_sales = st.tabs(["📦 庫存異動流水帳", "💎 訂單銷售紀錄"])
    
    with tab_log:
        df_log = st.session_state['history'].copy()
        cols = df_log.columns.tolist()
        if '單號' in cols:
            cols.remove('單號')
            cols.insert(1, '單號')
        df_log = df_log[cols]
        df_log.insert(0, "刪除", False)

        edited_df = st.data_editor(
            df_log,
            column_config={
                "刪除": st.column_config.CheckboxColumn("選取刪除", default=False)
            },
            disabled=cols, 
            use_container_width=True,
            key="history_editor"
        )

        if st.button("🗑️ 刪除選取的紀錄 (並還原庫存)", type="primary"):
            rows_to_delete = edited_df[edited_df['刪除']]
            if not rows_to_delete.empty:
                updated_items = []
                for index, row in rows_to_delete.iterrows():
                    target_id = row['編號']
                    qty_change = float(row['進貨數量'])
                    cost_change = float(row['進貨總價'])
                    
                    mask = st.session_state['inventory']['編號'] == target_id
                    if mask.any():
                        idx = st.session_state['inventory'][mask].index[0]
                        current_qty = float(st.session_state['inventory'].at[idx, '庫存(顆)'])
                        new_qty = current_qty - qty_change
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = new_qty if new_qty >= 0 else 0
                        updated_items.append(f"{row['名稱']}")

                rows_to_keep = edited_df[~edited_df['刪除']][cols]
                st.session_state['history'] = rows_to_keep
                save_inventory()
                st.success(f"✅ 已刪除並還原：{', '.join(updated_items)}")
                time.sleep(2)
                st.rerun()
        
    with tab_sales:
        st.dataframe(st.session_state['design_history'], use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計與成本
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 手鍊設計成本試算")
    all_items = st.session_state['inventory']

    if not all_items.empty:
        uniq_ele = sorted(all_items['五行'].astype(str).unique().tolist())
        sel_ele = st.multiselect("五行", uniq_ele, default=uniq_ele)
        if not sel_ele: sel_ele = uniq_ele
        
        filt_items = all_items[all_items['五行'].isin(sel_ele)].sort_values(by=['五行', '名稱', '編號'])

        st.divider()

        # ★★★ 修正語法：補上冒號 ★★★
        if not filt_items.empty:
            filt_items['disp_label'] = filt_items.apply(make_design_label, axis=1)
            
            c_sel, c_qty, c_btn = st.columns([3, 1, 1])
            with c_sel:
                sel_label = st.selectbox("👇 選擇珠子", filt_items['disp_label'].tolist())
            with c_qty:
                in_qty = st.number_input("數量", min_value=1, value=1)
            with c_btn:
                st.write("") 
                st.write("") 
                if st.button("⬇️ 加入", use_container_width=True, type="primary"):
                    row = filt_items[filt_items['disp_label'] == sel_label].iloc[0]
                    subtotal = row['單顆成本'] * in_qty
                    st.session_state['current_design'].append({
                        '編號': row['編號'], '分類': row['五行'], '名稱': row['名稱'],
                        '形狀': row['形狀'], '規格': format_size(row),
                        '單價': row['單顆成本'], '數量': in_qty, '小計': subtotal
                    })
                    st.success("已加入")

            st.divider()
            
            if st.session_state['current_design']:
                design_list = st.session_state['current_design']
                rows_to_del = []
                mat_cost = 0

                for i, item in enumerate(design_list):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1: st.write(f"{item['名稱']} ({item['規格']})")
                    with c2: st.write(f"${item['單價']:.2f} x {item['數量']}")
                    with c3: st.write(f"= ${item['小計']:.2f}")
                    with c4: 
                        if st.button("🗑️", key=f"del_{i}"): rows_to_del.append(i)
                    mat_cost += item['小計']

                if rows_to_del:
                    for i in sorted(rows_to_del, reverse=True):
                        del st.session_state['current_design'][i]
                    st.rerun()

                st.divider()
                lc, mc = st.columns(2)
                with lc: labor = st.number_input("工資 ($)", 0, step=10)
                with mc: misc = st.number_input("雜支 ($)", 0, step=5)

                total_cost = mat_cost + labor + misc
                st.info(f"總成本: ${total_cost:.2f}")
                
                if st.button("✅ 確定售出 (扣庫存)", type="primary"):
                    sales_order_id = f"S-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    detail_str = []
                    
                    for item in design_list:
                        mask = st.session_state['inventory']['編號'] == item['編號']
                        if mask.any():
                            idx = st.session_state['inventory'][mask].index[0]
                            current = st.session_state['inventory'].at[idx, '庫存(顆)']
                            st.session_state['inventory'].at[idx, '庫存(顆)'] = current - item['數量']
                            detail_str.append(f"{item['名稱']}x{item['數量']}")
                            
                            log = {
                                '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                                '單號': sales_order_id, '動作': '售出使用',
                                '編號': item['編號'], '分類': item['分類'], '名稱': item['名稱'],
                                '規格': item['規格'], '廠商': '售出', 
                                '進貨數量': -item['數量'], '進貨總價': 0, '單價': item['單價']
                            }
                            st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)

                    d_log = {
                        '單號': sales_order_id, '日期': date.today(), 
                        '總顆數': sum(x['數量'] for x in design_list),
                        '材料成本': mat_cost, '工資': labor, '雜支': misc,
                        '總成本': total_cost, '售價(x3)': 0, '售價(x5)': 0, 
                        '明細內容': " | ".join(detail_str)
                    }
                    st.session_state['design_history'] = pd.concat([st.session_state['design_history'], pd.DataFrame([d_log])], ignore_index=True)
                    
                    save_inventory()
                    save_design_history()
                    st.session_state['current_design'] = []
                    st.success("售出成功！")
                    time.sleep(1)
                    st.rerun()
            else:
                st.info("尚未加入任何配件。")
        else:
            st.warning("查無符合條件的庫存。")
    else:
        st.info("庫存為空。")
