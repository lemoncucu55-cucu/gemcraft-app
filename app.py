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

def generate_new_id(category, df):
    prefix_map = {'天然石': 'ST', '配件': 'AC', '耗材': 'OT'}
    if category not in prefix_map: return "N/A"
    
    prefix = prefix_map[category]
    if df.empty: return f"{prefix}0001"
    
    df_str = df.copy()
    df_str['編號'] = df_str['編號'].astype(str)
    existing_ids = df_str[df_str['編號'].str.startswith(prefix, na=False)]['編號']
    
    if existing_ids.empty: return f"{prefix}0001"
    
    max_num = 0
    for eid in existing_ids:
        try:
            num = int(eid[2:]) 
            if num > max_num: max_num = num
        except: pass
    
    return f"{prefix}{str(max_num + 1).zfill(4)}"

def merge_inventory_duplicates(df):
    if df.empty: return df, 0

    # 合併判斷基準：包含寬度與長度
    group_cols = ['分類', '名稱', '寬度mm', '長度mm', '形狀', '五行']
    
    # 確保數值型態正確
    df['庫存(顆)'] = pd.to_numeric(df['庫存(顆)'], errors='coerce').fillna(0)
    df['單顆成本'] = pd.to_numeric(df['單顆成本'], errors='coerce').fillna(0)
    
    original_count = len(df)
    new_rows = []
    
    # 依照關鍵屬性分組
    if set(group_cols).issubset(df.columns):
        grouped = df.groupby(group_cols, sort=False, as_index=False)
        
        for _, group in grouped:
            if len(group) == 1:
                new_rows.append(group.iloc[0])
            else:
                total_qty = group['庫存(顆)'].sum()
                total_value = (group['庫存(顆)'] * group['單顆成本']).sum()
                avg_cost = total_value / total_qty if total_qty > 0 else 0
                
                # 保留最新的那筆資料作為基礎 (例如編號、日期等)
                base_row = group.sort_values('編號', ascending=False).iloc[0].copy()
                base_row['庫存(顆)'] = total_qty
                base_row['單顆成本'] = avg_cost
                base_row['進貨日期'] = group['進貨日期'].max()
                new_rows.append(base_row)
        
        new_df = pd.DataFrame(new_rows)
    else:
        new_df = df # 若欄位不齊全則不合併

    # 最後確保欄位順序一致
    new_df = new_df.reindex(columns=COLUMNS)
    
    merged_count = original_count - len(new_df)
    return new_df, merged_count

# 自動修正欄位名稱
def normalize_columns(df):
    rename_map = {
        # 尺寸相關 -> 對應到 寬度mm
        '尺寸': '寬度mm', '尺寸mm': '寬度mm', '尺寸(mm/cm)': '寬度mm',
        'Size': '寬度mm', '寬度': '寬度mm', 'Width': '寬度mm',
        
        # 長度相關
        '長度': '長度mm', 'Length': '長度mm',
        
        # 其他欄位
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
    
    # 若缺少長度欄位，自動補 0
    if '長度mm' not in df.columns:
        df['長度mm'] = 0.0
        
    return df

# ==========================================
# 2. 設定與資料庫初始化
# ==========================================

SUPPLIERS = [
    "小聰頭", "小聰頭-13", "小聰頭-千千", "小聰頭-子馨", "小聰頭-小宇", "小聰頭-尼克", "小聰頭-周三寶", "小聰頭-蒨",
    "永安", "石之靈", "多加市集", "決益X", "昇輝", "星辰Crystal", "珍珠包金", "格魯特", "御金坊",
    "TB-天使街", "TB-東吳天然石坊", "TB-物物居", "TB-軒閣珠寶", "TB-鈦鋼潮牌", "TB-義烏卡樂芙", 
    "TB-鼎喜", "TB-銀拍檔", "TB-廣州小銀子", "TB-慶和銀飾", "TB-賽維雅珠寶", "TB-ins網紅玻璃杯",
    "TB-Mary", "TB-Super Search",
    "祥玥", "雪霖", "晶格格", "愛你一生", "福祿壽銀飾", "億伙", "廠商", "寶城水晶", "Rich"
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'

# 內建初始資料
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

if 'inventory' not in st.session_state:
    file_loaded = False
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df_init = pd.read_csv(DEFAULT_CSV_FILE)
            df_init = normalize_columns(df_init)
            
            df_init['編號'] = df_init['編號'].astype(str)
            df_init['單顆成本'] = pd.to_numeric(df_init['單顆成本'], errors='coerce').fillna(0)
            
            # 補齊可能缺少的欄位
            for col in COLUMNS:
                if col not in df_init.columns:
                    df_init[col] = 0 if 'mm' in col or '數量' in col or '價' in col or '成本' in col else ""
            
            # 依照指定順序重排
            df_init = df_init[COLUMNS]
            
            st.session_state['inventory'] = df_init
            file_loaded = True
        except: pass
    
    if not file_loaded:
        st.session_state['inventory'] = pd.DataFrame(INITIAL_DATA)
        st.session_state['inventory'] = st.session_state['inventory'][COLUMNS]

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
    
    df_to_download = st.session_state['inventory']
    if not df_to_download.empty:
        csv = df_to_download.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_summary_{date.today()}.csv', "text/csv")
    
    hist_to_download = st.session_state['history']
    if not hist_to_download.empty:
        hist_csv = hist_to_download.to_csv(index=False).encode('utf-8-sig')
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
                    st.error("🛑 缺少 openpyxl，請檢查 requirements.txt")
                    st.stop()
            
            uploaded_df = normalize_columns(uploaded_df)
            missing_cols = set(COLUMNS) - set(uploaded_df.columns)
            
            if not missing_cols:
                uploaded_df['編號'] = uploaded_df['編號'].astype(str)
                uploaded_df['單顆成本'] = pd.to_numeric(uploaded_df['單顆成本'], errors='coerce').fillna(0)
                uploaded_df['庫存(顆)'] = pd.to_numeric(uploaded_df['庫存(顆)'], errors='coerce').fillna(0)
                
                # 強制重排順序
                uploaded_df = uploaded_df[COLUMNS]
                
                if st.button("⚠️ 確認覆蓋庫存總表"):
                    st.session_state['inventory'] = uploaded_df
                    st.success("資料已還原！")
                    st.rerun()
            else:
                st.error(f"格式錯誤！缺少欄位：\n{', '.join(missing_cols)}")
                
        except Exception as e:
            st.error(f"讀取失敗: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    
    with st.container():
        st.markdown("##### 1. 選擇商品基本資料")
        c1, c2 = st.columns([1, 1.5])
        
        with c1:
            new_cat = st.selectbox("分類", ["天然石", "配件", "耗材"], key="add_cat_select")
        
        with c2:
            existing_names = []
            if not st.session_state['inventory'].empty:
                cat_df = st.session_state['inventory'][st.session_state['inventory']['分類'] == new_cat]
                existing_names = sorted(cat_df['名稱'].dropna().unique().astype(str).tolist())
            
            name_options = ["➕ 手動輸入新名稱"] + existing_names
            name_select = st.selectbox("名稱 (選既有或手動)", name_options, key="add_name_select")
            
            final_name = ""
            if name_select == "➕ 手動輸入新名稱":
                final_name = st.text_input("↳ 輸入新名稱", placeholder="例如：紫水晶", key="add_name_input")
            else:
                final_name = name_select

        st.markdown("##### 2. 規格尺寸 (mm)")
        c3a, c3b = st.columns(2)
        with c3a:
            existing_widths = []
            if not st.session_state['inventory'].empty:
                widths_raw = st.session_state['inventory']['寬度mm'].dropna().unique()
                try: existing_widths = sorted([float(x) for x in widths_raw])
                except: pass
            
            width_select = st.selectbox("寬度/直徑 (mm)", ["➕ 手動輸入"] + existing_widths, key="add_width_select")
            final_width = 0.0
            if width_select == "➕ 手動輸入":
                final_width = st.number_input("↳ 輸入寬度", min_value=0.0, step=0.5, format="%.1f", key="add_width_input")
            else:
                final_width = float(width_select)
                
        with c3b:
            final_length = st.number_input("長度 (mm, 圓珠可不填或填相同)", min_value=0.0, step=0.5, format="%.1f", key="add_length_input")
            if final_length == 0.0 and final_width > 0:
                st.caption(f"提示：若為圓珠，長度預設為 {final_width}")

    with st.form("add_new_details_form", clear_on_submit=True):
        st.markdown("##### 3. 詳細規格與進貨資訊")
        
        c4, c5, c6 = st.columns(3)
        with c4: new_shape = st.selectbox("形狀", ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型"])
        with c5: new_element = st.selectbox("五行", ["金", "木", "水", "火", "土", "綜合"])
        with c6: new_supplier = st.selectbox("廠商", SUPPLIERS)
        
        c7, c8, c9 = st.columns(3)
        with c7: new_price = st.number_input("進貨總價", 0)
        with c8: new_qty = st.number_input("進貨數量", 1)
        with c9: new_date = st.date_input("進貨日期", value=date.today())
        
        submitted = st.form_submit_button("➕ 確認新增入庫", type="primary")

        if submitted:
            if not final_name:
                st.error("❌ 請確認名稱已填寫！")
            else:
                save_length = final_length if final_length > 0 else (final_width if new_shape in ['圓珠', '鑽切'] else 0.0)
                new_id = generate_new_id(new_cat, st.session_state['inventory'])
                unit_cost = new_price / new_qty if new_qty > 0 else 0
                
                new_row = {
                    '編號': new_id, '分類': new_cat, '名稱': final_name, 
                    '寬度mm': final_width, '長度mm': save_length,
                    '形狀': new_shape, '五行': new_element, 
                    '進貨總價': new_price, '進貨數量(顆)': new_qty, 
                    '進貨日期': new_date, '進貨廠商': new_supplier,
                    '庫存(顆)': new_qty, '單顆成本': unit_cost
                }
                
                new_row_df = pd.DataFrame([new_row])
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], new_row_df], ignore_index=True)
                
                # 記錄到歷史
                history_entry = {
                    '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    '動作': '進貨',
                    '編號': new_id, '分類': new_cat, '名稱': final_name,
                    '寬度mm': final_width, '長度mm': save_length, '形狀': new_shape,
                    '廠商': new_supplier, '進貨數量': new_qty, 
                    '進貨總價': new_price, '單價': unit_cost
                }
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([history_entry])], ignore_index=True)
                
                st.success(f"✅ 已新增：{final_name} ({final_width}x{save_length}mm)")
                st.rerun()

    st.divider()
    
    # 庫存列表
    col_op1, col_op2 = st.columns([3, 1])
    with col_op1:
        st.markdown("### 📋 庫存總表")
    with col_op2:
        if st.button("🔄 合併重複項目"):
            merged_df, count = merge_inventory_duplicates(st.session_state['inventory'])
            st.session_state['inventory'] = merged_df
            st.success(f"已合併 {count} 筆重複資料！")
            st.rerun()

    search_term = st.text_input("🔍 搜尋庫存 (名稱/編號/廠商)", "")
    df_display = st.session_state['inventory'].copy()
    if search_term:
        df_display = df_display[
            df_display['名稱'].astype(str).str.contains(search_term, case=False) |
            df_display['編號'].astype(str).str.contains(search_term, case=False) |
            df_display['進貨廠商'].astype(str).str.contains(search_term, case=False)
        ]
    
    st.dataframe(
        df_display,
        use_container_width=True,
        column_config={
            "進貨總價": st.column_config.NumberColumn(format="$%d"),
            "單顆成本": st.column_config.NumberColumn(format="$%.2f"),
            "寬度mm": st.column_config.NumberColumn(format="%.1f"),
            "長度mm": st.column_config.NumberColumn(format="%.1f"),
        },
        height=400
    )
    
    with st.expander("🗑️ 刪除特定庫存"):
        del_id = st.text_input("輸入要刪除的編號 (例如 ST0001)")
        if st.button("確認刪除"):
            if del_id in st.session_state['inventory']['編號'].values:
                st.session_state['inventory'] = st.session_state['inventory'][st.session_state['inventory']['編號'] != del_id]
                st.success(f"已刪除 {del_id}")
                st.rerun()
            else:
                st.error("找不到此編號")

# ------------------------------------------
# 頁面 B: 進貨紀錄
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 進貨與異動紀錄")
    st.dataframe(st.session_state['history'], use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計與成本 (含五行篩選與數量輸入)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 手鍊設計成本試算")

    all_items = st.session_state['inventory'].copy()

    if not all_items.empty:
        # --- 1. 五行篩選 ---
        unique_elements = sorted(all_items['五行'].astype(str).unique().tolist())
        filter_options = ["全部"] + unique_elements

        st.write("👇 **第一步：選擇五行屬性**")
        selected_element = st.radio(
            "五行篩選", 
            filter_options, 
            horizontal=True,
            label_visibility="collapsed"
        )

        # --- 2. 排序與過濾 (五行優先) ---
        if selected_element == "全部":
            # 先照五行排，再照名稱排
            filtered_items = all_items.sort_values(by=['五行', '名稱', '編號'])
        else:
            filtered_items = all_items[all_items['五行'] == selected_element].sort_values(by=['名稱', '編號'])

        st.divider()

        # --- 3. 選擇珠子與數量 ---
        if not filtered_items.empty:
            filtered_items['display_label'] = filtered_items.apply(
                lambda x: f"【{x['五行']}】 {x['名稱']} ({x['寬度mm']}x{x['長度mm']}mm) | ${x['單顆成本']:.1f}/顆 | 存:{x['庫存(顆)']}", 
                axis=1
            )
            
            # 使用 3:1:1 的比例分配版面
            c_sel, c_qty, c_btn = st.columns([3, 1, 1])
            
            with c_sel:
                selected_item_label = st.selectbox(
                    f"👇 選擇珠子 (目前顯示：{selected_element})", 
                    filtered_items['display_label'].tolist()
                )
            
            with c_qty:
                input_qty = st.number_input("數量", min_value=1, value=1, step=1)
            
            with c_btn:
                st.write("") 
                st.write("") 
                if st.button("⬇️ 加入清單", use_container_width=True, type="primary"):
                    selected_row = filtered_items[filtered_items['display_label'] == selected_item_label].iloc[0]
                    
                    subtotal = selected_row['單顆成本'] * input_qty
                    
                    st.session_state['current_design'].append({
                        '編號': selected_row['編號'],
                        '分類': selected_row['五行'], 
                        '名稱': selected_row['名稱'],
                        '規格': f"{selected_row['寬度mm']}x{selected_row['長度mm']}",
                        '單價': selected_row['單顆成本'],
                        '數量': input_qty,
                        '小計': subtotal
                    })
                    st.success(f"已加入 {input_qty} 顆 {selected_row['名稱']}")
        else:
            st.warning(f"⚠️ 找不到屬性為「{selected_element}」的庫存項目。")

    st.divider()
    
    # --- 4. 設計清單 ---
    st.markdown("##### 📝 目前設計清單")
    if st.session_state['current_design']:
        design_df = pd.DataFrame(st.session_state['current_design'])
        
        st.dataframe(
            design_df, 
            use_container_width=True, 
            column_config={
                "單價": st.column_config.NumberColumn(format="$%.1f"),
                "小計": st.column_config.NumberColumn(format="$%.1f"),
                "數量": st.column_config.NumberColumn(format="%d 顆"),
            }
        )
        
        total_cost = design_df['小計'].sum()
        total_qty = design_df['數量'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("總顆數", f"{total_qty} 顆")
        m2.metric("總成本", f"${total_cost:.1f}")
        m3.metric("建議售價 (x3)", f"${total_cost * 3:.0f}")
        m4.metric("建議售價 (x5)", f"${total_cost * 5:.0f}")
        
        if st.button("🗑️ 清空設計清單", type="secondary"):
            st.session_state['current_design'] = []
            st.rerun()
    else:
        st.info("尚未加入任何配件。")
