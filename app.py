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

def merge_inventory_duplicates(df):
    if df.empty: return df, 0
    if '長度mm' not in df.columns: df['長度mm'] = 0.0
    if '寬度mm' not in df.columns and '尺寸mm' in df.columns: 
        df.rename(columns={'尺寸mm': '寬度mm'}, inplace=True)

    # 嚴格檢查：包含廠商
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

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 3. UI 介面設計
# ==========================================

st.set_page_config(page_title="GemCraft 庫存系統 V2.4", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    st.header("💾 資料備份")
    
    df_to_download = st.session_state['inventory']
    if not df_to_download.empty:
        csv = df_to_download.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_{date.today()}.csv', "text/csv")
    
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
    
    # 1. 新增區塊
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
                
                # 寫入歷史 (增加 _id 以便識別)
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

    # 2. 刪除工具 (庫存整筆刪除)
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

    # 3. 庫存表格
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
# 頁面 B: 進貨紀錄查詢 (★ 新增復原功能)
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.header("📜 進貨歷史明細")
    st.info("💡 說明：若進貨資料有誤，請勾選「撤銷」並按下確認按鈕。系統將會**自動扣除庫存**並**還原成本**到進貨前的狀態。")
    
    if not st.session_state['history'].empty:
        # 建立顯示用的 DataFrame，增加「撤銷」勾選欄位
        hist_df = st.session_state['history'].sort_values('紀錄時間', ascending=False).copy()
        if '撤銷選取' not in hist_df.columns:
            hist_df.insert(0, "撤銷選取", False)

        # 顯示 Data Editor
        edited_hist = st.data_editor(
            hist_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "撤銷選取": st.column_config.CheckboxColumn("勾選撤銷", help="勾選後按下方按鈕以復原庫存"),
                "單價": st.column_config.NumberColumn(format="$%.1f"),
                "進貨總價": st.column_config.NumberColumn(format="$%d"),
            },
            disabled=["紀錄時間", "動作", "編號", "分類", "名稱", "寬度mm", "長度mm", "形狀", "廠商", "進貨數量", "進貨總價", "單價"]
        )

        # 執行撤銷邏輯
        if st.button("↩️ 確認撤銷勾選項目 (刪除紀錄+還原庫存)", type="primary"):
            # 找出被勾選的行
            to_revert = edited_hist[edited_hist['撤銷選取'] == True]
            
            if to_revert.empty:
                st.warning("請先勾選上方表格中的項目！")
            else:
                inv_df = st.session_state['inventory']
                revert_count = 0
                
                for idx, row in to_revert.iterrows():
                    target_id = row['編號']
                    qty_to_remove = float(row['進貨數量'])
                    val_to_remove = float(row['進貨總價'])
                    
                    # 在庫存表中找到對應商品
                    # 注意：這裡會比對 編號+廠商+規格 以確保扣對人 (如果沒合併過，編號通常唯一)
                    # 這裡簡化邏輯：直接找編號。若編號對應多筆(因為沒合併)，則需進一步比對。
                    # 為了安全，我們比對 編號
                    mask = (inv_df['編號'] == target_id) & (inv_df['進貨廠商'] == row['廠商'])
                    target_rows = inv_df[mask]

                    if not target_rows.empty:
                        target_idx = target_rows.index[0]
                        current_stock = float(inv_df.at[target_idx, '庫存(顆)'])
                        current_cost = float(inv_df.at[target_idx, '單顆成本'])
                        current_total_val = current_stock * current_cost
                        
                        # 計算還原後的數值
                        new_stock = current_stock - qty_to_remove
                        new_total_val = current_total_val - val_to_remove
                        
                        # 防呆：庫存不能負
                        if new_stock <= 0:
                            new_stock = 0
                            new_cost = 0
                        else:
                            # 防呆：價值不能負 (除非原本就是負的，這在成本計算很少見)
                            if new_total_val < 0: new_total_val = 0
                            new_cost = new_total_val / new_stock

                        # 更新庫存表
                        inv_df.at[target_idx, '庫存(顆)'] = new_stock
                        inv_df.at[target_idx, '單顆成本'] = new_cost
                        revert_count += 1
                    else:
                        st.toast(f"找不到對應庫存：{target_id}，僅刪除紀錄。", icon="⚠️")

                # 更新 session state
                st.session_state['inventory'] = inv_df
                
                # 從歷史紀錄中刪除 (保留未勾選的)
                # 這裡使用原始 session 內的 history 來過濾，避免 data_editor 的暫存影響
                # 我們利用 row 的內容特徵來刪除 (因為沒有唯一 ID，我們假設 時間+編號+數量 相同即為同一筆)
                # 簡單作法：直接用 edited_hist 裡沒勾選的覆蓋回去
                
                # 剔除已勾選的行，並移除「撤銷選取」欄位後存回
                final_hist = edited_hist[edited_hist['撤銷選取'] == False].drop(columns=['撤銷選取'])
                st.session_state['history'] = final_hist
                
                st.success(f"成功撤銷 {revert_count} 筆進貨紀錄，庫存成本已還原！")
                st.rerun()

    else:
        st.warning("無紀錄")

# ------------------------------------------
# 頁面 C: 設計
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.header("📿 手鍊設計工作檯")
    st.info("此頁面功能維持不變。")
    # ... (功能與前版相同)
