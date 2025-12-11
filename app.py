import streamlit as st
import pandas as pd
from datetime import date, datetime
import os

# ==========================================
# 1. 核心邏輯區
# ==========================================

# 指定的欄位順序標準
COLUMNS = [
    '編號', '分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本'
]

HISTORY_COLUMNS = [
    '紀錄時間', '動作', '編號', '分類', '名稱', '寬度mm', '長度mm', '形狀', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'

# 預設資料清單
DEFAULT_SUPPLIERS = [
    "小聰頭", "小聰頭-13", "小聰頭-千千", "小聰頭-子馨", "小聰頭-小宇", "小聰頭-尼克", "小聰頭-周三寶", "小聰頭-蒨",
    "永安", "石之靈", "多加市集", "決益X", "昇輝", "星辰Crystal", "珍珠包金", "格魯特", "御金坊",
    "TB-天使街", "TB-東吳天然石坊", "TB-物物居", "TB-軒閣珠寶", "TB-鈦鋼潮牌", "TB-義烏卡樂芙", 
    "TB-鼎喜", "TB-銀拍檔", "TB-廣州小銀子", "TB-慶和銀飾", "TB-賽維雅珠寶", "TB-ins網紅玻璃杯",
    "TB-Mary", "TB-Super Search",
    "祥玥", "雪霖", "晶格格", "愛你一生", "福祿壽銀飾", "億伙", "廠商", "寶城水晶", "Rich"
]

DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合"]

INITIAL_DATA = {
    '編號': ['ST0001', 'ST0002', 'ST0003', 'ST0004', 'ST0005', 'ST0006'],
    '分類': ['天然石', '天然石', '天然石', '天然石', '天然石', '天然石'],
    '名稱': ['冰翠玉', '東菱玉', '紫水晶', '東菱玉', '東菱玉', '綠碧璽'],
    '寬度mm': [3.0, 5.0, 8.0, 6.0, 8.0, 8.0],
    '長度mm': [3.0, 5.0, 8.0, 6.0, 8.0, 8.0],
    '形狀': ['切角', '切角', '圓珠', '切角', '切角', '圓珠'],
    '五行': ['木', '木', '火', '木', '木', '木'],
    '進貨總價': [100, 180, 450, 132, 100, 550],
    '進貨數量(顆)': [145, 45, 50, 120, 45, 20],
    '進貨日期': ['2024-11-07', '2024-08-14', '2024-08-09', '2024-12-30', '2024-12-30', '2025-12-09'],
    '進貨廠商': ['TB-東吳天然石坊', 'Rich', '永安', 'TB-Super Search', 'TB-Super Search', '永安'],
    '庫存(顆)': [145, 45, 110, 120, 45, 20],
    '單顆成本': [0.689655, 4.0, 9.0, 1.1, 2.222222, 27.5],
}

# ---------- 小工具 ----------

def save_inventory_to_csv():
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception:
        pass

def generate_new_id(category, df):
    prefix_map = {'天然石': 'ST', '配件': 'AC', '耗材': 'OT'}
    prefix = prefix_map.get(category)
    if not prefix: return "N/A"
    if df.empty or '編號' not in df.columns: return f"{prefix}0001"
    
    df_ids = df['編號'].astype(str)
    mask = df_ids.str.startswith(prefix, na=False)
    numeric_part = df_ids[mask].str[2:].str.extract(r'(\d+)', expand=False).dropna()
    
    if numeric_part.empty: next_num = 1
    else: next_num = numeric_part.astype(int).max() + 1
    
    return f"{prefix}{next_num:04d}"

def merge_inventory_duplicates(df):
    if df.empty: return df, 0
    group_cols = ['分類', '名稱', '寬度mm', '長度mm', '形狀', '五行']
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
    base_rows = base_rows.drop(columns=['庫存(顆)', '單顆成本', '總成本', '進貨日期_排序'], errors='ignore')
    
    merged = pd.merge(agg, base_rows, on=group_cols, how='left', suffixes=('', '_base'))
    
    if '進貨廠商_base' in merged.columns: merged['進貨廠商'] = merged['進貨廠商_base']
    if '編號_base' in merged.columns: merged['編號'] = merged['編號_base']
        
    merged = merged[[c for c in merged.columns if not c.endswith('_base')]]
    for col in COLUMNS:
        if col not in merged.columns:
            merged[col] = 0 if ('mm' in col or '數量' in col or '價' in col or '成本' in col) else ""
            
    merged = merged[COLUMNS]
    return merged, original_count - len(merged)

def normalize_columns(df):
    rename_map = {
        '尺寸': '寬度mm', '尺寸mm': '寬度mm', '尺寸(mm/cm)': '寬度mm', 'Size': '寬度mm', '寬度': '寬度mm', 'Width': '寬度mm',
        '長度': '長度mm', 'Length': '長度mm',
        '名称': '名稱', 'Name': '名稱',
        '分类': '分類', 'Category': '分類',
        '形状': '形狀', 'Shape': '形狀',
        '五行': '五行', 'Element': '五行',
        '库存(颗)': '庫存(顆)', 'Stock': '庫存(顆)', '库存': '庫存(顆)',
        '单颗成本': '單顆成本', 'Cost': '單顆成本', '成本': '單顆成本',
        '进货厂商': '進貨廠商', 'Supplier': '進貨廠商', '厂商': '進貨廠商',
        '进货日期': '進貨日期', 'Date': '進貨日期', '日期': '進貨日期',
        '进货總價': '進貨總價', 'Total Price': '進貨總價',
        '进货数量(颗)': '進貨數量(顆)', 'Qty': '進貨數量(顆)'
    }
    df = df.rename(columns=rename_map)
    if '長度mm' not in df.columns: df['長度mm'] = 0.0
    return df

def make_inventory_label(row):
    return f"{row['編號']} | {row['名稱']} ({row['寬度mm']}x{row['長度mm']}mm) | 存:{row['庫存(顆)']}"

def make_design_label(row):
    return f"【{row['五行']}】 {row['名稱']} | {row['形狀']} ({row['寬度mm']}x{row['長度mm']}mm) | ${row['單顆成本']:.1f}/顆 | 存:{row['庫存(顆)']}"

def get_dynamic_options(column_name, default_list):
    options = set(default_list)
    if not st.session_state['inventory'].empty:
        existing = st.session_state['inventory'][column_name].dropna().unique().tolist()
        options.update([str(x) for x in existing if str(x).strip() != ""])
    return ["➕ 手動輸入新資料"] + sorted(list(options))

# ==========================================
# 2. 設定與資料庫初始化
# ==========================================

if 'inventory' not in st.session_state:
    file_loaded = False
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df_init = pd.read_csv(DEFAULT_CSV_FILE)
            df_init = normalize_columns(df_init)
            df_init['編號'] = df_init['編號'].astype(str)
            df_init['單顆成本'] = pd.to_numeric(df_init['單顆成本'], errors='coerce').fillna(0)
            for col in COLUMNS:
                if col not in df_init.columns:
                    df_init[col] = 0 if ('mm' in col or '數量' in col or '價' in col or '成本' in col) else ""
            df_init = df_init[COLUMNS]
            st.session_state['inventory'] = df_init
            file_loaded = True
        except Exception:
            file_loaded = False
    
    if not file_loaded:
        st.session_state['inventory'] = pd.DataFrame(INITIAL_DATA)[COLUMNS]

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 3. UI 介面設計
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    st.header("💾 資料備份")
    
    if not st.session_state['inventory'].empty:
        csv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_summary_{date.today()}.csv', "text/csv")
    
    if not st.session_state['history'].empty:
        hist_csv = st.session_state['history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載進貨明細 (CSV)", hist_csv, f'purchase_history_{date.today()}.csv', "text/csv")
    
    uploaded_file = st.file_uploader("📤 上傳復原庫存 (CSV/Excel)", type=['csv', 'xlsx', 'xls'])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                try:
                    uploaded_df = pd.read_excel(uploaded_file)
                except ImportError:
                    st.error("🛑 缺少 openpyxl")
                    st.stop()
            
            uploaded_df = normalize_columns(uploaded_df)
            missing_cols = set(COLUMNS) - set(uploaded_df.columns)
            
            if not missing_cols:
                uploaded_df['編號'] = uploaded_df['編號'].astype(str)
                uploaded_df['單顆成本'] = pd.to_numeric(uploaded_df['單顆成本'], errors='coerce').fillna(0)
                uploaded_df['庫存(顆)'] = pd.to_numeric(uploaded_df['庫存(顆)'], errors='coerce').fillna(0)
                uploaded_df = uploaded_df[COLUMNS]
                
                if st.button("⚠️ 確認覆蓋庫存總表"):
                    st.session_state['inventory'] = uploaded_df
                    save_inventory_to_csv()
                    st.success("資料已還原！")
                    st.rerun()
            else:
                st.error(f"格式錯誤！缺少欄位：\n{', '.join(missing_cols)}")
        except Exception as e:
            st.error(f"讀取失敗: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理與進貨
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    
    tab_restock, tab_new, tab_edit = st.tabs(["🔄 已有商品補貨", "✨ 建立新商品", "🛠️ 修改/刪除商品"])

    # === Tab 1: 舊品補貨 ===
    with tab_restock:
        st.caption("針對已經存在的商品編號進行數量追加。")
        inventory_df = st.session_state['inventory']
        if not inventory_df.empty:
            restock_df = inventory_df.copy()
            restock_df['label'] = restock_df.apply(make_inventory_label, axis=1)
            
            c_re1, c_re2 = st.columns([2, 1])
            with c_re1:
                selected_restock_label = st.selectbox("選擇要補貨的商品", restock_df['label'].tolist())
            
            target_row = restock_df[restock_df['label'] == selected_restock_label].iloc[0]
            
            with st.form("restock_form"):
                c_re3, c_re4, c_re5 = st.columns(3)
                with c_re3: restock_qty = st.number_input("補貨數量 (顆)", min_value=1, value=10)
                with c_re4: restock_total_price = st.number_input("本次進貨總價 ($)", min_value=0, value=0)
                with c_re5: restock_date = st.date_input("進貨日期", value=date.today())
                
                supplier_opts = get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS)
                try: def_idx = supplier_opts.index(target_row['進貨廠商']) 
                except: def_idx = 0
                restock_supplier_sel = st.selectbox("廠商", supplier_opts, index=def_idx)
                
                final_restock_supplier = st.text_input("↳ 輸入新廠商名稱") if restock_supplier_sel == "➕ 手動輸入新資料" else restock_supplier_sel

                if st.form_submit_button("📦 確認補貨"):
                    if not final_restock_supplier:
                        st.error("請輸入廠商名稱")
                    else:
                        old_qty = target_row['庫存(顆)']
                        old_avg_cost = target_row['單顆成本']
                        old_total_val = old_qty * old_avg_cost
                        new_unit_cost = restock_total_price / restock_qty if restock_qty > 0 else 0
                        final_qty = old_qty + restock_qty
                        final_total_val = old_total_val + restock_total_price
                        final_avg_cost = final_total_val / final_qty if final_qty > 0 else 0
                        
                        idx = inventory_df[inventory_df['編號'] == target_row['編號']].index[0]
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = final_qty
                        st.session_state['inventory'].at[idx, '單顆成本'] = final_avg_cost
                        st.session_state['inventory'].at[idx, '進貨日期'] = restock_date
                        st.session_state['inventory'].at[idx, '進貨廠商'] = final_restock_supplier
                        
                        history_entry = {
                            '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                            '動作': '補貨',
                            '編號': target_row['編號'], '分類': target_row['分類'], '名稱': target_row['名稱'],
                            '寬度mm': target_row['寬度mm'], '長度mm': target_row['長度mm'], '形狀': target_row['形狀'],
                            '廠商': final_restock_supplier, '進貨數量': restock_qty, 
                            '進貨總價': restock_total_price, '單價': new_unit_cost
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([history_entry])], ignore_index=True)
                        save_inventory_to_csv()
                        st.success(f"已補貨！目前庫存 {final_qty} 顆")
                        st.rerun()
        else:
            st.info("目前無庫存。")

    # === Tab 2: 建立新商品 ===
    with tab_new:
        with st.container():
            st.markdown("##### 1. 基本資料")
            c1, c2 = st.columns([1, 1.5])
            with c1: new_cat = st.selectbox("分類", ["天然石", "配件", "耗材"])
            with c2:
                existing_names = []
                if not st.session_state['inventory'].empty:
                    cat_df = st.session_state['inventory'][st.session_state['inventory']['分類'] == new_cat]
                    existing_names = sorted(cat_df['名稱'].dropna().unique().astype(str).tolist())
                name_options = ["➕ 手動輸入新名稱"] + existing_names
                name_select = st.selectbox("名稱", name_options)
                final_name = st.text_input("↳ 輸入新名稱") if name_select == "➕ 手動輸入新名稱" else name_select

            st.markdown("##### 2. 規格尺寸 (mm)")
            c3a, c3b = st.columns(2)
            with c3a:
                existing_widths = []
                if not st.session_state['inventory'].empty:
                    widths_raw = st.session_state['inventory']['寬度mm'].dropna().unique()
                    try: existing_widths = sorted({float(x) for x in widths_raw})
                    except: existing_widths = []
                width_select = st.selectbox("寬度/直徑", ["➕ 手動輸入"] + existing_widths)
                final_width = st.number_input("↳ 輸入寬度", min_value=0.0, step=0.5, format="%.1f") if width_select == "➕ 手動輸入" else float(width_select)
            with c3b:
                final_length = st.number_input("長度 (圓珠可不填)", min_value=0.0, step=0.5, format="%.1f")
                if final_length == 0.0 and final_width > 0: st.caption(f"預設為 {final_width}")

        prev_row = None
        if final_name and not st.session_state['inventory'].empty:
            same_name_df = st.session_state['inventory'][(st.session_state['inventory']['分類'] == new_cat) & (st.session_state['inventory']['名稱'] == final_name)]
            if not same_name_df.empty:
                tmp = same_name_df.copy()
                tmp['進貨日期_排序'] = pd.to_datetime(tmp['進貨日期'], errors='coerce')
                tmp = tmp.sort_values('進貨日期_排序', ascending=False)
                prev_row = tmp.iloc[0]

        with st.form("add_new_details_form", clear_on_submit=True):
            st.markdown("##### 3. 詳細資訊")
            shape_opts = get_dynamic_options('形狀', DEFAULT_SHAPES)
            element_opts = get_dynamic_options('五行', DEFAULT_ELEMENTS)
            supplier_opts = get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS)
            
            def get_index(options, value):
                try: return options.index(value)
                except: return 1 if len(options) > 1 else 0

            shape_idx = get_index(shape_opts, prev_row['形狀']) if prev_row is not None else 1
            element_idx = get_index(element_opts, prev_row['五行']) if prev_row is not None else 1
            supplier_idx = get_index(supplier_opts, prev_row['進貨廠商']) if prev_row is not None else 1

            c4, c5, c6 = st.columns(3)
            with c4: shape_sel = st.selectbox("形狀", shape_opts, index=shape_idx)
            with c5: element_sel = st.selectbox("五行", element_opts, index=element_idx)
            with c6: supplier_sel = st.selectbox("廠商", supplier_opts, index=supplier_idx)
            
            manual_cols = st.columns(3)
            final_shape = st.text_input("↳ 輸入新形狀") if shape_sel == "➕ 手動輸入新資料" else shape_sel
            final_element = st.text_input("↳ 輸入新五行") if element_sel == "➕ 手動輸入新資料" else element_sel
            final_supplier = st.text_input("↳ 輸入新廠商") if supplier_sel == "➕ 手動輸入新資料" else supplier_sel

            c7, c8, c9 = st.columns(3)
            with c7: new_price = st.number_input("進貨總價", 0)
            with c8: new_qty = st.number_input("進貨數量", 1)
            with c9: new_date = st.date_input("進貨日期", value=date.today())
            
            if st.form_submit_button("➕ 確認新增入庫", type="primary"):
                errors = []
                if not final_name: errors.append("名稱")
                if not final_shape: errors.append("形狀")
                if not final_element: errors.append("五行")
                if not final_supplier: errors.append("廠商")
                
                if errors:
                    st.error(f"❌ 請填寫完整：{', '.join(errors)}")
                else:
                    save_length = final_length if final_length > 0 else (final_width if "圓" in final_shape or "珠" in final_shape else 0.0)
                    new_id = generate_new_id(new_cat, st.session_state['inventory'])
                    unit_cost = new_price / new_qty if new_qty > 0 else 0
                    
                    new_row = {
                        '編號': new_id, '分類': new_cat, '名稱': final_name, 
                        '寬度mm': final_width, '長度mm': save_length,
                        '形狀': final_shape, '五行': final_element, 
                        '進貨總價': new_price, '進貨數量(顆)': new_qty, 
                        '進貨日期': new_date, '進貨廠商': final_supplier,
                        '庫存(顆)': new_qty, '單顆成本': unit_cost
                    }
                    
                    st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_row])], ignore_index=True)
                    
                    history_entry = {
                        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '動作': '進貨',
                        '編號': new_id, '分類': new_cat, '名稱': final_name,
                        '寬度mm': final_width, '長度mm': save_length, '形狀': final_shape,
                        '廠商': final_supplier, '進貨數量': new_qty, 
                        '進貨總價': new_price, '單價': unit_cost
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([history_entry])], ignore_index=True)
                    save_inventory_to_csv()
                    st.success(f"✅ 已新增：{final_name} - {new_id}")
                    st.rerun()

    # === Tab 3: 修改/刪除商品 ===
    with tab_edit:
        st.markdown("##### 🛠️ 修正商品資料或刪除")
        if not st.session_state['inventory'].empty:
            edit_df = st.session_state['inventory'].copy()
            edit_df['label'] = edit_df.apply(make_inventory_label, axis=1)
            
            selected_edit_label = st.selectbox("🔍 選擇要修改/刪除的商品", edit_df['label'].tolist())
            original_row = edit_df[edit_df['label'] == selected_edit_label].iloc[0]
            original_idx = st.session_state['inventory'][st.session_state['inventory']['編號'] == original_row['編號']].index[0]

            with st.form("edit_item_form"):
                st.info(f"正在編輯：{original_row['編號']}")
                ec1, ec2, ec3 = st.columns(3)
                with ec1: edit_name = st.text_input("名稱", value=original_row['名稱'])
                with ec2: edit_width = st.number_input("寬度mm", value=float(original_row['寬度mm']), step=0.1)
                with ec3: edit_length = st.number_input("長度mm", value=float(original_row['長度mm']), step=0.1)

                shape_opts = get_dynamic_options('形狀', DEFAULT_SHAPES)
                element_opts = get_dynamic_options('五行', DEFAULT_ELEMENTS)
                supplier_opts = get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS)
                
                def get_edit_idx(opts, val):
                    try: return opts.index(val)
                    except: return 0

                ec4, ec5, ec6 = st.columns(3)
                with ec4: e_shape_sel = st.selectbox("形狀", shape_opts, index=get_edit_idx(shape_opts, original_row['形狀']))
                with ec5: e_element_sel = st.selectbox("五行", element_opts, index=get_edit_idx(element_opts, original_row['五行']))
                with ec6: e_supplier_sel = st.selectbox("廠商", supplier_opts, index=get_edit_idx(supplier_opts, original_row['進貨廠商']))

                em_cols = st.columns(3)
                edit_shape = em_cols[0].text_input("↳ 新形狀", value="") if e_shape_sel == "➕ 手動輸入新資料" else e_shape_sel
                edit_element = em_cols[1].text_input("↳ 新五行", value="") if e_element_sel == "➕ 手動輸入新資料" else e_element_sel
                edit_supplier = em_cols[2].text_input("↳ 新廠商", value="") if e_supplier_sel == "➕ 手動輸入新資料" else e_supplier_sel

                st.divider()
                st.caption("⚠️ 庫存數量與成本修正")
                ec7, ec8 = st.columns(2)
                with ec7: edit_stock = st.number_input("庫存數量", value=int(original_row['庫存(顆)']), step=1)
                with ec8: edit_cost = st.number_input("單顆成本", value=float(original_row['單顆成本']), step=0.1, format="%.2f")

                col_update, col_delete = st.columns([1, 1])
                with col_update:
                    if st.form_submit_button("💾 儲存修改"):
                        st.session_state['inventory'].at[original_idx, '名稱'] = edit_name
                        st.session_state['inventory'].at[original_idx, '寬度mm'] = edit_width
                        st.session_state['inventory'].at[original_idx, '長度mm'] = edit_length
                        st.session_state['inventory'].at[original_idx, '形狀'] = edit_shape
                        st.session_state['inventory'].at[original_idx, '五行'] = edit_element
                        st.session_state['inventory'].at[original_idx, '進貨廠商'] = edit_supplier
                        st.session_state['inventory'].at[original_idx, '庫存(顆)'] = edit_stock
                        st.session_state['inventory'].at[original_idx, '單顆成本'] = edit_cost
                        
                        history_entry = {
                            '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '動作': '修改資料',
                            '編號': original_row['編號'], '分類': original_row['分類'], '名稱': edit_name,
                            '寬度mm': edit_width, '長度mm': edit_length, '形狀': edit_shape,
                            '廠商': edit_supplier, '進貨數量': 0, '進貨總價': 0, '單價': edit_cost
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([history_entry])], ignore_index=True)
                        save_inventory_to_csv()
                        st.success("✅ 資料已更新！")
                        st.rerun()

                with col_delete:
                    if st.form_submit_button("🗑️ 刪除此商品", type="primary"):
                        st.session_state['inventory'] = st.session_state['inventory'].drop(original_idx).reset_index(drop=True)
                        save_inventory_to_csv()
                        st.success(f"已刪除 {original_row['名稱']}")
                        st.rerun()
        else:
            st.info("目前沒有資料可編輯。")

    st.divider()
    
    col_op1, col_op2 = st.columns([3, 1])
    with col_op1: st.markdown("### 📋 庫存總表")
    with col_op2:
        if st.button("🔄 合併重複項目"):
            merged_df, count = merge_inventory_duplicates(st.session_state['inventory'])
            st.session_state['inventory'] = merged_df
            save_inventory_to_csv()
            st.success(f"已合併 {count} 筆！")
            st.rerun()

    search_term = st.text_input("🔍 搜尋庫存", "")
    df_display = st.session_state['inventory']
    if search_term:
        df_display = df_display[
            df_display['名稱'].astype(str).str.contains(search_term, case=False) |
            df_display['編號'].astype(str).str.contains(search_term, case=False)
        ]
    st.dataframe(df_display, use_container_width=True, height=400, column_config={"進貨總價": st.column_config.NumberColumn(format="$%d"), "單顆成本": st.column_config.NumberColumn(format="$%.2f"), "寬度mm": st.column_config.NumberColumn(format="%.1f"), "長度mm": st.column_config.NumberColumn(format="%.1f")})

# ------------------------------------------
# 頁面 B: 進貨紀錄
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 進貨與異動紀錄")
    st.dataframe(st.session_state['history'], use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計與成本計算
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 手鍊設計成本試算")
    all_items = st.session_state['inventory']

    if not all_items.empty:
        unique_elements = sorted(all_items['五行'].astype(str).unique().tolist())
        st.write("👇 **第一步：選擇五行屬性（可複選）**")
        selected_elements = st.multiselect("五行屬性", options=unique_elements, default=unique_elements)
        if not selected_elements: selected_elements = unique_elements
        
        filtered_items = all_items[all_items['五行'].isin(selected_elements)]
        filtered_items = filtered_items.sort_values(by=['五行', '名稱', '編號'])

        st.divider()

        if not filtered_items.empty:
            temp_df = filtered_items.copy()
            temp_df['display_label'] = temp_df.apply(make_design_label, axis=1)
            
            selected_label_list = ", ".join(selected_elements)
            c_sel, c_qty, c_btn = st.columns([3, 1, 1])
            with c_sel:
                selected_item_label = st.selectbox(f"👇 選擇珠子（目前篩選：{selected_label_list}）", temp_df['display_label'].tolist())
            with c_qty:
                input_qty = st.number_input("數量", min_value=1, value=1)
            with c_btn:
                st.write("") 
                st.write("") 
                if st.button("⬇️ 加入清單", use_container_width=True, type="primary"):
                    selected_row = temp_df[temp_df['display_label'] == selected_item_label].iloc[0]
                    subtotal = selected_row['單顆成本'] * input_qty
                    st.session_state['current_design'].append({
                        '編號': selected_row['編號'],
                        '分類': selected_row['五行'], 
                        '名稱': selected_row['名稱'],
                        '形狀': selected_row['形狀'],
                        '規格': f"{selected_row['寬度mm']}x{selected_row['長度mm']}",
                        '單價': selected_row['單顆成本'],
                        '數量': input_qty,
                        '小計': subtotal
                    })
                    st.success(f"已加入 {input_qty} 顆 {selected_row['名稱']}")

            st.divider()
            st.markdown("##### 📝 目前設計清單")
            
            # ★★★ 修改重點：將 DataFrame 改為手動繪製的清單，並加入刪除按鈕 ★★★
            if st.session_state['current_design']:
                # 表頭
                h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 1.5, 1, 0.8])
                h1.markdown("**編號**")
                h2.markdown("**名稱**")
                h3.markdown("**規格**")
                h4.markdown("**單價**")
                h5.markdown("**數量**")
                h6.markdown("**移除**")
                st.divider()

                # 內容
                design_list = st.session_state['current_design']
                rows_to_delete = []
                
                total_material_cost = 0

                for i, item in enumerate(design_list):
                    c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 2, 1.5, 1, 0.8])
                    with c1: st.write(item['編號'])
                    with c2: st.write(f"{item['名稱']} ({item['分類']})")
                    with c3: st.write(f"{item['形狀']} {item['規格']}")
                    with c4: st.write(f"${item['單價']:.1f}")
                    with c5: st.write(f"{item['數量']}")
                    with c6:
                        if st.button("🗑️", key=f"del_design_{i}"):
                            rows_to_delete.append(i)
                    
                    total_material_cost += item['小計']

                # 執行刪除
                if rows_to_delete:
                    for i in sorted(rows_to_delete, reverse=True):
                        del st.session_state['current_design'][i]
                    st.rerun()

                st.divider()
                st.markdown("##### 💰 額外成本 (工資/雜支)")
                c_labor, c_misc = st.columns(2)
                with c_labor: labor_cost = st.number_input("工資 ($)", min_value=0, value=0, step=10)
                with c_misc: misc_cost = st.number_input("雜支/包材/運費 ($)", min_value=0, value=0, step=5)

                final_total_cost = total_material_cost + labor_cost + misc_cost
                total_qty = sum(item['數量'] for item in design_list)
                
                st.success(f"💎 材料費小計: ${total_material_cost:.1f}")
                
                st.divider()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("總顆數", f"{total_qty} 顆")
                m2.metric("總成本 (含工雜)", f"${final_total_cost:.1f}")
                m3.metric("建議售價 (x3)", f"${final_total_cost * 3:.0f}")
                m4.metric("建議售價 (x5)", f"${final_total_cost * 5:.0f}")
                
                if st.button("🗑️ 清空所有清單", type="secondary"):
                    st.session_state['current_design'] = []
                    st.rerun()
            else:
                st.info("尚未加入任何配件。")
        else:
            st.warning(f"⚠️ 找不到屬性為 {selected_elements} 的庫存項目。")
    else:
        st.info("庫存為空，請先至庫存管理頁面新增商品。")
