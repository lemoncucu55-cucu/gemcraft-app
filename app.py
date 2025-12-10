import streamlit as st
import pandas as pd
from datetime import date, datetime
import os

# ==========================================
# 0. 強制資料結構升級與修復
# ==========================================
if 'inventory' in st.session_state:
    df_check = st.session_state['inventory']
    if '尺寸mm' in df_check.columns and '寬度mm' not in df_check.columns:
        st.toast("⚠️ 偵測到舊版資料，正在自動升級...", icon="🔄")
        df_check.rename(columns={'尺寸mm': '寬度mm'}, inplace=True)
        df_check['長度mm'] = 0.0
        st.session_state['inventory'] = df_check
        st.rerun()

# ==========================================
# 1. 核心邏輯區
# ==========================================

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

# ★★★ 新增：產生訂單編號 ★★★
def generate_order_id(df_sales):
    today_str = datetime.now().strftime("%Y%m%d")
    prefix = f"ORD-{today_str}-"
    
    if df_sales.empty:
        return f"{prefix}001"
    
    # 找出當天已存在的最大序號
    # 這裡簡單過濾出包含今天日期的訂單號
    relevant_ids = [x for x in df_sales['訂單編號'].unique() if isinstance(x, str) and x.startswith(prefix)]
    
    if not relevant_ids:
        return f"{prefix}001"
    
    max_seq = 0
    for oid in relevant_ids:
        try:
            seq = int(oid.split("-")[-1])
            if seq > max_seq: max_seq = seq
        except: pass
        
    return f"{prefix}{str(max_seq + 1).zfill(3)}"

def merge_inventory_duplicates(df):
    if df.empty: return df, 0
    if '長度mm' not in df.columns: df['長度mm'] = 0.0
    if '寬度mm' not in df.columns and '尺寸mm' in df.columns: 
        df.rename(columns={'尺寸mm': '寬度mm'}, inplace=True)

    group_cols = ['分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨廠商']
    
    df['庫存(顆)'] = pd.to_numeric(df['庫存(顆)'], errors='coerce').fillna(0)
    df['單顆成本'] = pd.to_numeric(df['單顆成本'], errors='coerce').fillna(0)
    
    original_count = len(df)
    new_rows = []
    
    df[group_cols] = df[group_cols].fillna('')
    grouped = df.groupby(group_cols, sort=False, as_index=False)
    
    for _, group in grouped:
        if len(group) == 1:
            new_rows.append(group.iloc[0])
        else:
            total_qty = group['庫存(顆)'].sum()
            total_value = (group['庫存(顆)'] * group['單顆成本']).sum()
            avg_cost = total_value / total_qty if total_qty > 0 else 0
            
            base_row = group.sort_values('編號').iloc[0].copy()
            base_row['庫存(顆)'] = total_qty
            base_row['單顆成本'] = avg_cost
            base_row['進貨日期'] = group['進貨日期'].max()
            new_rows.append(base_row)
            
    new_df = pd.DataFrame(new_rows)
    merged_count = original_count - len(new_df)
    return new_df, merged_count

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

COLUMNS = [
    '編號', '分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本'
]

HISTORY_COLUMNS = [
    '紀錄時間', '動作', '編號', '分類', '名稱', '寬度mm', '長度mm', '形狀', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

# ★★★ 修改：銷售紀錄欄位 (加入訂單號與總金額) ★★★
SALES_COLUMNS = [
    '訂單編號', '銷售時間', '編號', '分類', '名稱', '規格', '售出數量', 
    '成本單價', '售出小計', '工資', '雜支', '訂單總金額'
]

DEFAULT_CSV_FILE = 'inventory_backup.csv'
INITIAL_DATA = {
    '編號': ['ST0001', 'ST0002'], '分類': ['天然石', '天然石'], '名稱': ['冰翠玉', '東菱玉'],
    '寬度mm': [3.0, 5.0], '長度mm': [0.0, 0.0], '形狀': ['切角', '切角'], '五行': ['木', '木'],
    '進貨總價': [100, 180], '進貨數量(顆)': [145, 45], '進貨日期': ['2024-11-07', '2024-08-14'],
    '進貨廠商': ['TB-東吳天然石坊', 'Rich'], '庫存(顆)': [145, 45], '單顆成本': [0.68, 4.0],
}

if 'inventory' not in st.session_state:
    file_loaded = False
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df_init = pd.read_csv(DEFAULT_CSV_FILE)
            if '尺寸mm' in df_init.columns and '寬度mm' not in df_init.columns:
                df_init.rename(columns={'尺寸mm': '寬度mm'}, inplace=True)
            for col in COLUMNS:
                if col not in df_init.columns:
                    df_init[col] = 0 if 'mm' in col or '數量' in col or '價' in col else ''
            st.session_state['inventory'] = df_init
            file_loaded = True
        except: pass
    if not file_loaded:
        st.session_state['inventory'] = pd.DataFrame(INITIAL_DATA)

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'sales_history' not in st.session_state:
    st.session_state['sales_history'] = pd.DataFrame(columns=SALES_COLUMNS)

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 3. UI 介面設計
# ==========================================

st.set_page_config(page_title="GemCraft 庫存系統 V2.7", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 歷史紀錄查詢 (進貨/售出)", "🧮 設計與成本計算"])
    st.divider()
    st.header("💾 資料備份")
    
    df_to_download = st.session_state['inventory']
    if not df_to_download.empty:
        csv = df_to_download.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_{date.today()}.csv', "text/csv")
    
    sales_to_download = st.session_state['sales_history']
    if not sales_to_download.empty:
        sales_csv = sales_to_download.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載售出紀錄 (CSV)", sales_csv, f'sales_history_{date.today()}.csv', "text/csv")

    uploaded_file = st.file_uploader("📤 上傳復原 (支援舊版)", type=['csv', 'xlsx'])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): uploaded_df = pd.read_csv(uploaded_file)
            else: uploaded_df = pd.read_excel(uploaded_file)
            
            if '尺寸mm' in uploaded_df.columns and '寬度mm' not in uploaded_df.columns:
                uploaded_df.rename(columns={'尺寸mm': '寬度mm'}, inplace=True)
            if '長度mm' not in uploaded_df.columns: uploaded_df['長度mm'] = 0.0

            is_valid = True
            for col in COLUMNS:
                if col not in uploaded_df.columns: is_valid = False
            
            if is_valid:
                uploaded_df['編號'] = uploaded_df['編號'].astype(str)
                uploaded_df['單顆成本'] = pd.to_numeric(uploaded_df['單顆成本'], errors='coerce').fillna(0)
                uploaded_df['庫存(顆)'] = pd.to_numeric(uploaded_df['庫存(顆)'], errors='coerce').fillna(0)
                uploaded_df['寬度mm'] = pd.to_numeric(uploaded_df['寬度mm'], errors='coerce').fillna(0)
                uploaded_df['長度mm'] = pd.to_numeric(uploaded_df['長度mm'], errors='coerce').fillna(0)
                
                if st.button("⚠️ 確認覆蓋庫存總表"):
                    st.session_state['inventory'] = uploaded_df[COLUMNS]
                    st.success("✅ 資料還原成功！")
                    st.rerun()
            else:
                st.error("❌ 格式錯誤，請檢查欄位。")
        except Exception as e:
            st.error(f"讀取失敗: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    
    with st.expander("➕ 新增商品入庫", expanded=True):
        c1, c2, c3, c3_5 = st.columns([1, 1.5, 1, 1])
        with c1: new_cat = st.selectbox("分類", ["天然石", "配件", "耗材"])
        with c2: 
            existing_names = sorted(st.session_state['inventory'][st.session_state['inventory']['分類']==new_cat]['名稱'].unique().tolist())
            name_select = st.selectbox("名稱", ["➕ 手動輸入"] + existing_names)
            final_name = st.text_input("輸入名稱") if name_select == "➕ 手動輸入" else name_select
        with c3:
            final_width = st.number_input("寬度 (mm)", min_value=0.0, step=0.5, format="%.1f")
        with c3_5:
            final_length = st.number_input("長度 (mm)", min_value=0.0, step=0.5, format="%.1f", help="圓珠填0")

        c4, c5, c6 = st.columns(3)
        with c4: new_shape = st.selectbox("形狀", ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型"])
        with c5: new_element = st.selectbox("五行", ["金", "木", "水", "火", "土", "綜合"])
        with c6: new_supplier = st.selectbox("廠商", SUPPLIERS)
        
        c7, c8, c9 = st.columns(3)
        with c7: new_price = st.number_input("進貨總價", 0)
        with c8: new_qty = st.number_input("進貨數量", 1)
        with c9: new_date = st.date_input("進貨日期", value=date.today())
        
        if st.button("確認新增", type="primary"):
            if not final_name: st.error("請輸入名稱")
            else:
                new_id = generate_new_id(new_cat, st.session_state['inventory'])
                unit_cost = new_price / new_qty if new_qty > 0 else 0
                new_row = {
                    '編號': new_id, '分類': new_cat, '名稱': final_name, 
                    '寬度mm': final_width, '長度mm': final_length,
                    '形狀': new_shape, '五行': new_element, '進貨總價': new_price,
                    '進貨數量(顆)': new_qty, '進貨日期': new_date, '進貨廠商': new_supplier,
                    '庫存(顆)': new_qty, '單顆成本': unit_cost
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_row])], ignore_index=True)
                
                hist_entry = new_row.copy()
                hist_entry['紀錄時間'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                hist_entry['動作'] = '新品新增'
                hist_entry['廠商'] = new_supplier
                hist_entry['進貨數量'] = new_qty
                hist_entry['單價'] = unit_cost
                clean_hist = {k: v for k, v in hist_entry.items() if k in HISTORY_COLUMNS}
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([clean_hist])], ignore_index=True)
                
                st.success(f"已新增: {new_id} {final_name}")
                st.rerun()

    with st.expander("🗑️ 庫存清單管理 (刪除指定商品)", expanded=False):
        if not st.session_state['inventory'].empty:
            df = st.session_state['inventory']
            df['label'] = df['編號'] + " | " + df['名稱'] + " " + df['寬度mm'].astype(str) + "mm (" + df['進貨廠商'] + ")"
            delete_target = st.selectbox("選擇要刪除的商品", df['label'].unique())
            
            if st.button("🗑️ 確認刪除此商品 (不復原金額)"):
                target_id = delete_target.split(" | ")[0]
                st.session_state['inventory'] = df[df['編號'] != target_id].drop(columns=['label'])
                st.success(f"商品 {target_id} 已刪除！")
                st.rerun()

    st.markdown("##### 目前庫存清單")
    current_df = st.session_state['inventory']
    if not current_df.empty: current_df = current_df.sort_values(by=['分類', '編號'])
    
    edited_df = st.data_editor(
        current_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_order=("編號", "分類", "名稱", "寬度mm", "長度mm", "形狀", "庫存(顆)", "單顆成本", "進貨廠商"),
        disabled=["編號", "單顆成本"],
        column_config={
            "單顆成本": st.column_config.NumberColumn(format="$%.1f"),
            "寬度mm": st.column_config.NumberColumn(label="寬", format="%.1f"),
            "長度mm": st.column_config.NumberColumn(label="長", format="%.1f"),
        }
    )
    if not edited_df.equals(current_df):
        st.session_state['inventory'] = edited_df
        st.rerun()

    if st.button("🧹 合併重複商品"):
        merged_df, count = merge_inventory_duplicates(st.session_state['inventory'])
        st.session_state['inventory'] = merged_df
        st.success(f"已合併 {count} 筆") if count > 0 else st.info("無重複")
        st.rerun()

# ------------------------------------------
# 頁面 B: 歷史紀錄
# ------------------------------------------
elif page == "📜 歷史紀錄查詢 (進貨/售出)":
    st.header("📜 歷史紀錄中心")
    tab1, tab2 = st.tabs(["📥 進貨紀錄", "📤 售出紀錄 (含訂單)"])

    # Tab 1: 進貨
    with tab1:
        st.info("說明：勾選撤銷可還原庫存與成本。")
        if not st.session_state['history'].empty:
            hist_df = st.session_state['history'].sort_values('紀錄時間', ascending=False).copy()
            if '撤銷選取' not in hist_df.columns: hist_df.insert(0, "撤銷選取", False)

            edited_hist = st.data_editor(
                hist_df, use_container_width=True, hide_index=True,
                column_config={
                    "撤銷選取": st.column_config.CheckboxColumn("勾選撤銷"),
                    "單價": st.column_config.NumberColumn(format="$%.1f"),
                    "進貨總價": st.column_config.NumberColumn(format="$%d"),
                },
                disabled=["紀錄時間", "動作", "編號", "分類", "名稱", "寬度mm", "長度mm", "形狀", "廠商", "進貨數量", "進貨總價", "單價"]
            )
            if st.button("↩️ 確認撤銷進貨", type="primary"):
                to_revert = edited_hist[edited_hist['撤銷選取'] == True]
                if to_revert.empty: st.warning("請先勾選項目")
                else:
                    inv_df = st.session_state['inventory']
                    revert_count = 0
                    for idx, row in to_revert.iterrows():
                        target_id = row['編號']
                        qty_to_remove = float(row['進貨數量'])
                        val_to_remove = float(row['進貨總價'])
                        mask = (inv_df['編號'] == target_id) & (inv_df['進貨廠商'] == row['廠商'])
                        target_rows = inv_df[mask]
                        if not target_rows.empty:
                            target_idx = target_rows.index[0]
                            current_stock = float(inv_df.at[target_idx, '庫存(顆)'])
                            current_total_val = current_stock * float(inv_df.at[target_idx, '單顆成本'])
                            new_stock = current_stock - qty_to_remove
                            new_total_val = current_total_val - val_to_remove
                            if new_stock <= 0: new_stock, new_cost = 0, 0
                            else: 
                                new_total_val = max(0, new_total_val)
                                new_cost = new_total_val / new_stock
                            inv_df.at[target_idx, '庫存(顆)'] = new_stock
                            inv_df.at[target_idx, '單顆成本'] = new_cost
                            revert_count += 1
                        else: st.toast(f"找不到對應庫存：{target_id}", icon="⚠️")
                    st.session_state['inventory'] = inv_df
                    st.session_state['history'] = edited_hist[edited_hist['撤銷選取'] == False].drop(columns=['撤銷選取'])
                    st.success(f"成功撤銷 {revert_count} 筆")
                    st.rerun()
        else: st.warning("無進貨紀錄")

    # Tab 2: 售出 (★ 顯示訂單資訊)
    with tab2:
        st.info("說明：每筆訂單包含工資與雜支。勾選撤銷可將商品加回庫存。")
        
        if not st.session_state['sales_history'].empty:
            sales_df = st.session_state['sales_history'].sort_values(['訂單編號', '銷售時間'], ascending=[False, False]).copy()
            
            # 確保新欄位存在 (防呆：針對舊版 sales log)
            for col in ['工資', '雜支', '訂單總金額', '訂單編號']:
                if col not in sales_df.columns: sales_df[col] = 0 if col != '訂單編號' else '-'
            
            if '撤銷選取' not in sales_df.columns: sales_df.insert(0, "撤銷選取", False)

            edited_sales = st.data_editor(
                sales_df, use_container_width=True, hide_index=True,
                column_config={
                    "撤銷選取": st.column_config.CheckboxColumn("勾選撤銷"),
                    "成本單價": st.column_config.NumberColumn(format="$%.1f"),
                    "售出小計": st.column_config.NumberColumn(format="$%.1f"),
                    "工資": st.column_config.NumberColumn(format="$%d"),
                    "雜支": st.column_config.NumberColumn(format="$%d"),
                    "訂單總金額": st.column_config.NumberColumn(format="$%d", help="含工資與雜支的總價"),
                },
                disabled=["訂單編號", "銷售時間", "編號", "分類", "名稱", "規格", "售出數量", "成本單價", "售出小計", "工資", "雜支", "訂單總金額"]
            )

            if st.button("↩️ 確認撤銷售出 (退貨/加回庫存)", type="primary"):
                to_revert_sales = edited_sales[edited_sales['撤銷選取'] == True]
                if to_revert_sales.empty:
                    st.warning("請先勾選項目！")
                else:
                    inv_df = st.session_state['inventory']
                    restore_count = 0
                    
                    for idx, row in to_revert_sales.iterrows():
                        target_id = row['編號']
                        qty_to_restore = float(row['售出數量'])
                        idx_list = inv_df.index[inv_df['編號'].astype(str) == target_id].tolist()
                        
                        if idx_list:
                            target_idx = idx_list[0]
                            current_stock = float(inv_df.at[target_idx, '庫存(顆)'])
                            inv_df.at[target_idx, '庫存(顆)'] = current_stock + qty_to_restore
                            restore_count += 1
                        else:
                            st.toast(f"找不到庫存編號 {target_id}，僅刪除紀錄。", icon="⚠️")

                    st.session_state['inventory'] = inv_df
                    final_sales = edited_sales[edited_sales['撤銷選取'] == False].drop(columns=['撤銷選取'])
                    st.session_state['sales_history'] = final_sales
                    st.success(f"已撤銷 {restore_count} 筆售出紀錄，庫存已補回！")
                    st.rerun()
        else:
            st.warning("尚無售出紀錄")

# ------------------------------------------
# 頁面 C: 設計 (★ 產生訂單)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.header("📿 手鍊設計工作檯")
    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.subheader("1. 選擇材料")
        df = st.session_state['inventory']
        cat_options = ["全部"] + ["天然石", "配件", "耗材"]
        selected_cat = st.radio("🔍 依分類篩選", cat_options, horizontal=True)
        valid_df = df[df['編號'].notna()].copy()
        if selected_cat != "全部": valid_df = valid_df[valid_df['分類'] == selected_cat]

        if not valid_df.empty:
            valid_df['五行'] = valid_df['五行'].fillna('未分類')
            valid_df['名稱'] = valid_df['名稱'].fillna('')
            if '長度mm' not in valid_df.columns: valid_df['長度mm'] = 0
            valid_df = valid_df.sort_values(by=['五行', '名稱'])
            
            def format_size(row):
                w = row['寬度mm']; l = row['長度mm']
                return f"{w}" if l == 0 else f"{w}x{l}"
            valid_df['尺寸顯示'] = valid_df.apply(format_size, axis=1)
            valid_df['顯示名稱'] = "[" + valid_df['五行'].astype(str) + "] " + valid_df['名稱'].astype(str) + " (" + valid_df['尺寸顯示'] + "mm " + valid_df['形狀'].astype(str) + ")" + " | " + valid_df['編號'].astype(str)
            
            option_display = st.selectbox("搜尋材料", valid_df['顯示名稱'])
            item = valid_df[valid_df['顯示名稱'] == option_display].iloc[0]
            st.info(f"**{item['名稱']}** | 庫存: {item['庫存(顆)']} | 成本: ${item['單顆成本']:.1f}")
            
            is_restock = st.checkbox("我要對此商品進行「補貨」")
            qty = st.number_input("數量", 1)
            
            if is_restock:
                restock_price = st.number_input("補貨總價", 0)
                restock_supplier = st.selectbox("補貨廠商", SUPPLIERS)
                if st.button("🔄 確認補貨", type="secondary"):
                    idx = df.index[df['編號'] == item['編號']].tolist()[0]
                    old_stock = df.at[idx, '庫存(顆)']
                    old_cost = df.at[idx, '單顆成本']
                    new_total_val = (old_stock * old_cost) + restock_price
                    new_total_qty = old_stock + qty
                    new_avg_cost = new_total_val / new_total_qty if new_total_qty > 0 else 0
                    df.at[idx, '庫存(顆)'] = new_total_qty
                    df.at[idx, '單顆成本'] = new_avg_cost
                    df.at[idx, '進貨廠商'] = restock_supplier
                    st.session_state['inventory'] = df
                    hist_entry = {
                        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '動作': '舊品補貨', '編號': item['編號'], '分類': item['分類'], '名稱': item['名稱'],
                        '寬度mm': item['寬度mm'], '長度mm': item['長度mm'],
                        '形狀': item['形狀'], '廠商': restock_supplier,
                        '進貨數量': qty, '進貨總價': restock_price, '單價': restock_price/qty if qty>0 else 0
                    }
                    clean_hist = {k: v for k, v in hist_entry.items() if k in HISTORY_COLUMNS}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([clean_hist])], ignore_index=True)
                    st.success("補貨完成！"); st.rerun()
            else:
                if st.button("⬇️ 加入設計圖", type="primary"):
                    new_entry = {
                        '編號': str(item['編號']), '分類': str(item['分類']), '名稱': str(item['名稱']),
                        '規格': f"{item['尺寸顯示']}mm {item['形狀']}",
                        '使用數量': int(qty), '單價': float(item['單顆成本']),
                        '小計': float(item['單顆成本']) * int(qty)
                    }
                    st.session_state['current_design'].append(new_entry)
                    st.success("已加入！"); st.rerun()
        else: st.warning("無資料")

    with col2:
        st.subheader("2. 設計清單")
        design_data = st.session_state['current_design']
        if len(design_data) > 0:
            design_df = pd.DataFrame(design_data)
            st.dataframe(design_df, use_container_width=True, hide_index=True, column_order=("分類", "名稱", "規格", "使用數量", "單價", "小計"))
            
            total = design_df['小計'].sum()
            st.divider()
            c_labor, c_other = st.columns(2)
            labor = c_labor.number_input("工資", 0)
            other = c_other.number_input("雜支", 0)
            final_total = total + labor + other
            st.metric("總成本 (含工資雜支)", f"NT$ {final_total:.1f}")
            
            col_action1, col_action2 = st.columns(2)
            with col_action1:
                # ★★★ 確認售出並產生訂單 ★★★
                if st.button("✅ 確認售出 (扣除庫存並記帳)", type="primary", use_container_width=True):
                    inv_df = st.session_state['inventory']
                    all_success = True
                    sales_logs = []
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    # 產生訂單編號
                    new_order_id = generate_order_id(st.session_state['sales_history'])

                    for row in design_data:
                        target_id = row['編號']
                        use_qty = row['使用數量']
                        idx_list = inv_df.index[inv_df['編號'].astype(str) == target_id].tolist()
                        if idx_list:
                            idx = idx_list[0]
                            if inv_df.at[idx, '庫存(顆)'] < use_qty:
                                st.error(f"庫存不足：{row['名稱']}"); all_success = False
                        else: st.error(f"找不到編號 {target_id}"); all_success = False
                    
                    if all_success:
                        for row in design_data:
                            target_id = row['編號']
                            use_qty = row['使用數量']
                            idx = inv_df.index[inv_df['編號'].astype(str) == target_id].tolist()[0]
                            inv_df.at[idx, '庫存(顆)'] -= use_qty
                            
                            sales_logs.append({
                                '訂單編號': new_order_id, # 加入訂單號
                                '銷售時間': now_str,
                                '編號': target_id,
                                '分類': row['分類'],
                                '名稱': row['名稱'],
                                '規格': row['規格'],
                                '售出數量': use_qty,
                                '成本單價': row['單價'],
                                '售出小計': row['小計'],
                                '工資': labor,        # 紀錄工資
                                '雜支': other,        # 紀錄雜支
                                '訂單總金額': final_total # 紀錄這筆單的總價
                            })
                        
                        st.session_state['inventory'] = inv_df
                        st.session_state['sales_history'] = pd.concat([st.session_state['sales_history'], pd.DataFrame(sales_logs)], ignore_index=True)
                        st.session_state['current_design'] = []
                        st.toast(f"售出成功！訂單號：{new_order_id}", icon="✅")
                        st.rerun()

            with col2:
                if st.button("🗑️ 清空重算", type="secondary", use_container_width=True):
                    st.session_state['current_design'] = []; st.rerun()
            
            txt = f"【訂單 {datetime.now().strftime('%Y%m%d')}】\n"
            for _, row in design_df.iterrows(): txt += f"- {row['名称']} x{row['使用数量']}\n"
            txt += f"總計: {final_total}"
            # st.text_area("複製", txt)
        else: st.info("👈 清單是空的")
