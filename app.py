import streamlit as st
import pandas as pd
from datetime import date

# ==========================================
# 1. 核心邏輯區 (函式)
# ==========================================

def generate_new_id(category, df):
    """
    產生單一新編號 (用於表單送出時)
    """
    prefix_map = {
        '天然石': 'ST',
        '配件': 'AC',
        '耗材': 'OT',
    }
    
    if category not in prefix_map:
        return "N/A"
        
    prefix = prefix_map[category]
    
    # 找出目前該分類最大號碼
    existing_ids = df[df['編號'].astype(str).str.startswith(prefix, na=False)]['編號']
    
    max_num = 0
    for eid in existing_ids:
        try:
            num = int(eid[2:]) 
            if num > max_num:
                max_num = num
        except:
            pass
    
    return f"{prefix}{str(max_num + 1).zfill(4)}"

# ==========================================
# 2. 設定與資料庫初始化
# ==========================================

# 定義廠商清單 (依據你的要求)
SUPPLIERS = [
    "小聰頭", "小聰頭-13", "小聰頭-千千", "小聰頭-子馨", "小聰頭-小宇", "小聰頭-尼克", "小聰頭-周三寶", "小聰頭-蒨",
    "永安", "石之靈", "多加市集", "決益X", "昇輝", "星辰Crystal", "珍珠包金", "格魯特", "御金坊",
    "淘-天使街", "淘-東吳天然石坊", "淘-物物居", "淘-軒閣珠寶", "淘-鈦鋼潮牌", "淘-義烏卡樂芙", 
    "淘-鼎喜", "淘-銀拍檔", "淘-廣州小銀子", "淘-慶和銀飾", "淘-賽維雅珠寶", "淘-ins網紅玻璃杯",
    "淘-Mary", "淘-Super Search",
    "祥玥", "雪霖", "晶格格", "愛你一生", "福祿壽銀飾", "億伙", "廠商", "寶城水晶", "Rich"
]

if 'inventory' not in st.session_state:
    # 初始化資料庫 (欄位擴充)
    # 預設一筆範例資料
    data = {
        '編號': ['ST0001'],
        '分類': ['天然石'],
        '名稱': ['紫水晶'],
        '尺寸mm': [8.0],
        '形狀': ['圓珠'],
        '五行': ['火'],
        '進貨總價': [500],
        '進貨數量(顆)': [40],
        '進貨日期': [date.today()],
        '進貨廠商': ['小聰頭'],
        '庫存(顆)': [40], # 預設庫存等於進貨數量
    }
    df = pd.DataFrame(data)
    df['單顆成本'] = df['進貨總價'] / df['進貨數量(顆)'].replace(0, 1)
    st.session_state['inventory'] = df

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 3. UI 介面設計
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

page = st.sidebar.radio("功能選單", ["📦 庫存管理與進貨", "🧮 設計與成本計算"])

# ------------------------------------------
# 頁面 A: 庫存管理與進貨
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    
    # --- Part 1: 新增進貨表單 (Form) ---
    st.markdown("### 📝 新增進貨資料")
    
    with st.form("add_item_form", clear_on_submit=True):
        st.caption("請依照順序填寫，送出後系統會自動產生編號並加入下方表格。")
        
        # 第一排
        c1, c2, c3 = st.columns(3)
        with c1:
            new_cat = st.selectbox("1. 分類", ["天然石", "配件", "耗材"])
        with c2:
            new_name = st.text_input("2. 名稱", placeholder="例如：紫水晶")
        with c3:
            new_size = st.number_input("3. 尺寸 (mm)", min_value=0.0, step=0.5, format="%.1f")

        # 第二排
        c4, c5, c6 = st.columns(3)
        with c4:
            new_shape = st.selectbox("4. 形狀", ["圓珠", "切角", "鑽切", "圓筒", "不規則", "造型"])
        with c5:
            new_element = st.selectbox("5. 五行", ["金", "木", "水", "火", "土", "綜合"])
        with c6:
            new_supplier = st.selectbox("6. 進貨廠商", SUPPLIERS)

        # 第三排
        c7, c8, c9 = st.columns(3)
        with c7:
            new_price = st.number_input("7. 進貨總價", min_value=0)
        with c8:
            new_qty = st.number_input("8. 進貨數量 (顆)", min_value=1)
        with c9:
            new_date = st.date_input("9. 進貨日期", value=date.today())

        # 送出按鈕
        submitted = st.form_submit_button("➕ 確認新增入庫", type="primary")

        if submitted:
            if not new_name:
                st.error("❌ 請填寫「名稱」！")
            else:
                # 1. 產生新編號
                new_id = generate_new_id(new_cat, st.session_state['inventory'])
                
                # 2. 建立新資料 Row
                new_data = {
                    '編號': new_id,
                    '分類': new_cat,
                    '名稱': new_name,
                    '尺寸mm': new_size,
                    '形狀': new_shape,
                    '五行': new_element,
                    '進貨總價': new_price,
                    '進貨數量(顆)': new_qty,
                    '進貨日期': new_date,
                    '進貨廠商': new_supplier,
                    '庫存(顆)': new_qty, # 新進貨時，庫存預設等於進貨量
                    '單顆成本': new_price / new_qty if new_qty > 0 else 0
                }
                
                # 3. 加入 DataFrame
                new_df = pd.DataFrame([new_data])
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], new_df], ignore_index=True)
                st.success(f"✅ 已新增：{new_id} {new_name}")
                st.rerun()

    st.divider()

    # --- Part 2: 庫存總表 (Data Editor) ---
    st.markdown("### 📊 目前庫存清單")
    
    # 確保資料庫有內容
    if not st.session_state['inventory'].empty:
        # 顯示編輯器 (只允許修改庫存、價格等非關鍵欄位，避免編號錯亂)
        current_df = st.session_state['inventory']
        
        edited_df = st.data_editor(
            current_df,
            num_rows="dynamic", # 這裡還是允許下方直接新增，以備不時之需
            use_container_width=True,
            hide_index=True,
            column_order=("編號", "分類", "名稱", "尺寸mm", "形狀", "五行", "庫存(顆)", "單顆成本", "進貨廠商", "進貨日期"),
            disabled=["編號", "單顆成本"], # 鎖定編號和成本
            key="inventory_table"
        )
        
        # 處理表格內的修改 (例如手動改庫存)
        if not edited_df.equals(current_df):
            # 重新計算成本 (防止有人改了進貨價)
            p_price = pd.to_numeric(edited_df['進貨總價'], errors='coerce').fillna(0)
            p_qty = pd.to_numeric(edited_df['進貨數量(顆)'], errors='coerce').fillna(0)
            edited_df['單顆成本'] = p_price / p_qty.replace(0, 1)
            
            st.session_state['inventory'] = edited_df
            st.rerun()
    else:
        st.info("目前沒有資料，請使用上方表單新增。")


# ------------------------------------------
# 頁面 B: 設計與成本計算
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.header("手鍊設計工作檯")

    col1, col2 = st.columns([1, 1.5])

    # --- 左邊：選材區 ---
    with col1:
        st.subheader("1. 選擇材料")
        df = st.session_state['inventory']
        
        # 建立搜尋顯示名稱：編號 | 名稱 (尺寸mm-形狀)
        valid_df = df[df['編號'].notna() & (df['編號'] != '')].copy()
        
        # 處理顯示格式，避免 None 出錯
        valid_df['顯示名稱'] = (
            valid_df['編號'].astype(str) + " | " + 
            valid_df['名稱'].astype(str) + 
            " (" + valid_df['尺寸mm'].astype(str) + "mm)"
        )
        
        if not valid_df.empty:
            option_display = st.selectbox("搜尋/選擇材料", valid_df['顯示名稱'].sort_values())
            
            # 找出對應項目
            selected_item = valid_df[valid_df['顯示名稱'] == option_display].iloc[0]
            
            # 顯示詳細資訊卡片
            st.info(
                f"**{selected_item['名稱']}**\n\n"
                f"- 編號: `{selected_item['編號']}`\n"
                f"- 規格: {selected_item['尺寸mm']}mm / {selected_item['形狀']}\n"
                f"- 五行: {selected_item['五行']}\n
