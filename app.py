import streamlit as st
import pandas as pd
from datetime import date, datetime
import os

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

def merge_inventory_duplicates(df):
    if df.empty: return df, 0

    group_cols = ['分類', '名稱', '尺寸mm', '形狀', '五行']
    
    df['庫存(顆)'] = pd.to_numeric(df['庫存(顆)'], errors='coerce').fillna(0)
    df['單顆成本'] = pd.to_numeric(df['單顆成本'], errors='coerce').fillna(0)
    
    original_count = len(df)
    new_rows = []
    
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
    '編號', '分類', '名稱', '尺寸mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本'
]

HISTORY_COLUMNS = [
    '紀錄時間', '動作', '編號', '分類', '名稱', '尺寸mm', '形狀', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_2025-12-09.csv'

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df_init = pd.read_csv(DEFAULT_CSV_FILE)
            df_init['編號'] = df_init['編號'].astype(str)
            df_init['單顆成本'] = pd.to_numeric(df_init['單顆成本'], errors='coerce').fillna(0)
            st.session_state['inventory'] = df_init
        except:
            st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else:
        st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

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
    
    uploaded_file = st.file_uploader("📤 上傳復原庫存總表", type=['csv', 'xlsx', 'xls'])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file)
            
            if set(COLUMNS).issubset(uploaded_df.columns):
                uploaded_df['編號'] = uploaded_df['編號'].astype(str)
                uploaded_df['單顆成本'] = pd.to_numeric(uploaded_df['單顆成本'], errors='coerce').fillna(0)
                uploaded_df['庫存(顆)'] = pd.to_numeric(uploaded_df['庫存(顆)'], errors='coerce').fillna(0)
                if st.button("⚠️ 確認覆蓋庫存總表"):
                    st.session_state['inventory'] = uploaded_df
                    st.success("資料已還原！")
                    st.rerun()
            else:
                st.error(f"格式錯誤！需包含：{', '.join(COLUMNS)}")
        except Exception as e:
            st.error(f"讀取失敗: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    
    # ★★★ 步驟 1: 先選分類與名稱 (這部分移出表單以支援動態更新) ★★★
    with st.container():
        st.markdown("##### 1. 選擇商品類型與名稱")
        c1, c2 = st.columns([1, 2])
        
        with c1:
            # 選擇分類
            new_cat = st.selectbox("分類", ["天然石", "配件", "耗材"], key="add_cat_select")
        
        with c2:
            # 依據分類篩選既有名稱
            existing_names = []
            if not st.session_state['inventory'].empty:
                # 只抓取該分類下的名稱
                cat_df = st.session_state['inventory'][st.session_state['inventory']['分類'] == new_cat]
                existing_names = sorted(cat_df['名稱'].dropna().unique().tolist())
            
            name_options = ["➕ 手動輸入新名稱"] + existing_names
            name_select = st.selectbox("名稱 (自動列出該分類舊稱)", name_options, key="add_name_select")
            
            final_name = ""
            if name_select == "➕ 手動輸入新名稱":
                final_name = st.text_input("請輸入新名稱", placeholder="例如：紫水晶", key="add_name_input")
            else:
                final_name = name_select

    # ★★★ 步驟 2: 詳細規格表單 (這部分用 Form 包起來，避免一直重整) ★★★
    with st.form("add_new_details_form", clear_on_submit=True):
        st.markdown("##### 2. 填寫詳細規格")
        
        c3, c4, c5 = st.columns(3)
        with c3: new_size = st.number_input("尺寸 (mm)", 0.0, step=0.5, format="%.1f")
        with c4: new_shape = st.selectbox("形狀", ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型"])
        with c5: new_element = st.selectbox("五行", ["金", "木", "水", "火", "土", "綜合"])
        
        c6, c7, c8 = st.columns(3)
        with c6: new_price = st.number_input("進貨總價", 0)
        with c7: new_qty = st.number_input("進貨數量", 1)
        with c8: new_supplier = st.selectbox("廠商", SUPPLIERS)
        
        new_date = st.date_input("進貨日期", value=date.today())
        
        submitted = st.form_submit_button("➕ 確認新增入庫", type="primary")

        if submitted:
            if not final_name:
                st.error("❌ 請確認名稱已填寫！")
            else:
                new_id = generate_new_id(new_cat, st.session_state['inventory'])
                unit_cost = new_price / new_qty if new_qty > 0 else 0
                
                # 1. 更新庫存總表
                new_row = {
                    '編號': new_id, '分類': new_cat, '名稱': final_name, '尺寸mm': new_size,
                    '形狀': new_shape, '五行': new_element, '進貨總價': new_price,
                    '進貨數量(顆)': new_qty, '進貨日期': new_date, '進貨廠商': new_supplier,
                    '庫存(顆)': new_qty, '單顆成本': unit_cost
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_row])], ignore_index=True)
                
                # 2. 寫入歷史明細
                hist_entry = {
                    '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    '動作': '新品新增', '編號': new_id, '分類': new_cat, '名稱': final_name,
                    '尺寸mm': new_size, '形狀': new_shape, '廠商': new_supplier,
                    '進貨數量': new_qty, '進貨總價': new_price, '單價': unit_cost
                }
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([hist_entry])], ignore_index=True)
                
                st.success(f"新增成功：{new_id} {final_name}")
                st.rerun()

    st.divider()

    # 自動合併按鈕
    col_msg, col_btn = st.columns([3, 1])
    with col_msg:
        st.caption("提示：若有相同分類、名稱、規格的商品，可使用自動合併整理庫存。")
    with col_btn:
        if st.button("🧹 自動合併重複商品"):
            merged_df, count = merge_inventory_duplicates(st.session_state['inventory'])
            if count > 0:
                st.session_state['inventory'] = merged_df
                st.success(f"成功合併 {count} 筆！")
                st.rerun()
            else:
                st.info("沒有重複項目")

    current_df = st.session_state['inventory']
    if not current_df.empty:
         current_df = current_df.sort_values(by=['分類', '五行', '名稱'])

    edited_df = st.data_editor(
        current_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_order=("編號", "分類", "名稱", "尺寸mm", "形狀", "庫存(顆)", "單顆成本", "進貨廠商"),
        disabled=["編號", "單顆成本"],
        column_config={
            "單顆成本": st.column_config.NumberColumn(format="$%.1f"),
            "尺寸mm": st.column_config.NumberColumn(format="%.1f"),
        }
    )
    if not edited_df.equals(current_df):
        st.session_state['inventory'] = edited_df
        st.rerun()

# ------------------------------------------
# 頁面 B: 進貨紀錄查詢
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.header("📜 進貨歷史明細")
    
    if not st.session_state['history'].empty:
        show_hist = st.session_state['history'].sort_values(by='紀錄時間', ascending=False)
        st.dataframe(
            show_hist, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "單價": st.column_config.NumberColumn(format="$%.1f"),
                "進貨總價": st.column_config.NumberColumn(format="$%d"),
            }
        )
    else:
        st.warning("目前還沒有進貨紀錄。")

# ------------------------------------------
# 頁面 C: 設計
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
        
        if selected_cat != "全部":
            valid_df = valid_df[valid_df['分類'] == selected_cat]

        if not valid_df.empty:
            valid_df['五行'] = valid_df['五行'].fillna('未分類')
            valid_df['名稱'] = valid_df['名稱'].fillna('')
            valid_df = valid_df.sort_values(by=['五行', '名稱'])
            
            valid_df['顯示名稱'] = (
                "[" + valid_df['五行'].astype(str) + "] " +
                valid_df['名稱'].astype(str) + 
                " (" + valid_df['尺寸mm'].astype(str) + "mm " + valid_df['形狀'].astype(str) + ")" +
                " | " + valid_df['編號'].astype(str)
            )
            
            option_display = st.selectbox("搜尋材料", valid_df['顯示名稱'])
            
            item = valid_df[valid_df['顯示名稱'] == option_display].iloc[0]
            
            st.info(f"**{item['名稱']}**\n\n分類: {item['分類']} | 五行: {item['五行']}\n規格: {item['尺寸mm']}mm {item['形狀']}\n\n庫存: {item['庫存(顆)']} | 成本: ${item['單顆成本']:.1f}")
            
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
                        '尺寸mm': item['尺寸mm'], '形狀': item['形狀'], '廠商': restock_supplier,
                        '進貨數量': qty, '進貨總價': restock_price, '單價': restock_price/qty if qty>0 else 0
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([hist_entry])], ignore_index=True)
                    
                    st.success("補貨完成！")
                    st.rerun()
            else:
                if st.button("⬇️ 加入設計圖", type="primary"):
                    new_entry = {
                        '編號': str(item['編號']),
                        '分類': str(item['分類']),
                        '名稱': str(item['名稱']),
                        '規格': f"{item['尺寸mm']}mm {item['形狀']}",
                        '使用數量': int(qty),
                        '單價': float(item['單顆成本']),
                        '小計': float(item['單顆成本']) * int(qty)
                    }
                    st.session_state['current_design'].append(new_entry)
                    st.success("已加入！")
                    st.rerun()
        else:
            if selected_cat == "全部":
                st.warning("庫存無資料，請先新增")
            else:
                st.warning(f"沒有「{selected_cat}」類別的材料")

    with col2:
        st.subheader("2. 設計清單")
        
        design_data = st.session_state['current_design']
        
        if len(design_data) > 0:
            design_df = pd.DataFrame(design_data)
            
            st.dataframe(
                design_df,
                use_container_width=True,
                hide_index=True,
                column_order=("分類", "名稱", "規格", "使用數量", "單價", "小計"),
                column_config={
                    "單價": st.column_config.NumberColumn(format="$%.1f"),
                    "小計": st.column_config.NumberColumn(format="$%.1f"),
                }
            )
            
            total = design_df['小計'].sum()
            
            st.divider()
            c_labor, c_other = st.columns(2)
            labor = c_labor.number_input("工資", 0)
            other = c_other.number_input("雜支", 0)
            
            final_total = total + labor + other
            st.metric("總成本", f"NT$ {final_total:.1f}")
            
            col_action1, col_action2 = st.columns(2)
            
            with col_action1:
                if st.button("✅ 確認售出 (扣除庫存)", type="primary", use_container_width=True):
                    inv_df = st.session_state['inventory']
                    all_success = True
                    
                    for row in design_data:
                        target_id = row['編號']
                        use_qty = row['使用數量']
                        
                        idx_list = inv_df.index[inv_df['編號'].astype(str) == target_id].tolist()
                        
                        if idx_list:
                            idx = idx_list[0]
                            current_stock = inv_df.at[idx, '庫存(顆)']
                            inv_df.at[idx, '庫存(顆)'] = current_stock - use_qty
                        else:
                            st.error(f"找不到編號 {target_id}，無法扣除")
                            all_success = False
                    
                    if all_success:
                        st.session_state['inventory'] = inv_df
                        st.session_state['current_design'] = []
                        st.toast("🎉 售出成功！庫存已更新", icon="✅")
                        st.rerun()

            with col_action2:
                if st.button("🗑️ 清空重算", type="secondary", use_container_width=True):
                    st.session_state['current_design'] = []
                    st.rerun()
                
            txt = f"【報價單】總計 ${final_total:.0f}\n"
            for _, row in design_df.iterrows():
                txt += f"- [{row['分類']}] {row['名稱']} ({row['規格']}) x{row['使用數量']}\n"
            st.text_area("複製文字", txt)
            
        else:
            st.info("👈 清單是空的，請先加入材料")
