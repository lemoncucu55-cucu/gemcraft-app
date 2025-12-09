import streamlit as st
import pandas as pd

# --- 1. 核心邏輯區 ---

def check_and_fill_ids(df):
    """
    自動編號邏輯
    """
    prefix_map = {
        '天然石': 'ST',  # Stone
        '配件': 'AC',    # Accessory
        '耗材': 'OT',    # Others
    }

    for index, row in df.iterrows():
        is_id_empty = pd.isna(row['編號']) or row['編號'] == '' or row['編號'] is None
        category = row.get('分類')
        
        if is_id_empty and category in prefix_map:
            prefix = prefix_map[category]
            
            # 找出目前該分類最大的號碼
            existing_ids = df[df['編號'].astype(str).str.startswith(prefix, na=False)]['編號']
            
            max_num = 0
            for eid in existing_ids:
                try:
                    num = int(eid[2:]) 
                    if num > max_num:
                        max_num = num
                except:
                    pass
            
            new_id = f"{prefix}{str(max_num + 1).zfill(4)}"
            df.at[index, '編號'] = new_id
            
    return df

# --- 2. 設定與資料庫初始化 ---

if 'inventory' not in st.session_state:
    # 預設資料 (已改為「顆數」邏輯)
    data = {
        '編號': ['ST0001', 'ST0002', 'ST0003', 'AC0001', 'OT0001'],
        '名稱': ['紫水晶 8mm', '粉晶 8mm', '白水晶 6mm', '925純銀隔珠', '日本彈力線'],
        '分類': ['天然石', '天然石', '天然石', '配件', '耗材'],
        # 這裡改成單純的「進貨總價」與「總顆數」
        '進貨總價': [500, 450, 300, 1500, 200],
        '進貨數量(顆)': [40, 40, 60, 100, 1], 
        # 庫存改成「顆」 (例如原本2串就是80顆)
        '庫存(顆)': [80, 120, 300, 100, 10], 
    }
    df = pd.DataFrame(data)
    # 計算單顆成本
    df['單顆成本'] = df['進貨總價'] / df['進貨數量(顆)']
    st.session_state['inventory'] = df

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# --- 3. UI 介面設計 ---

st.set_page_config(page_title="GemCraft 成本計算機", layout="wide")
st.title("💎 GemCraft 成本計算機")

page = st.sidebar.radio("功能選單", ["📦 庫存管理", "🧮 設計與成本計算"])

# ==========================================
# 頁面 A: 庫存管理 (Inventory)
# ==========================================
if page == "📦 庫存管理":
    st.header("庫存資料庫")
    st.info("💡 庫存單位已改為「顆」，方便精確盤點。")

    current_df = st.session_state['inventory']

    # 顯示編輯器
    edited_df = st.data_editor(
        current_df.sort_values(by='編號'),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        # 欄位順序調整
        column_order=("編號", "名稱", "分類", "進貨總價", "進貨數量(顆)", "庫存(顆)", "單顆成本"),
        disabled=["編號", "單顆成本"] 
    )

    if not edited_df.equals(current_df):
        # A. 重新計算單顆成本 (總價 / 總數量)
        edited_df['單顆成本'] = edited_df['進貨總價'] / edited_df['進貨數量(顆)']
        
        # B. 自動編號
        edited_df = check_and_fill_ids(edited_df)
        
        # C. 存檔
        st.session_state['inventory'] = edited_df
        st.rerun()

# ==========================================
# 頁面 B: 設計與成本計算 (Design & Cost)
# ==========================================
elif page == "🧮 設計與成本計算":
    st.header("手鍊成本計算")

    col1, col2 = st.columns([1, 1.5])

    # 左邊：選材區
    with col1:
        st.subheader("1. 選擇材料")
        df = st.session_state['inventory']
        
        # 建立顯示名稱
        df['顯示名稱'] = df['編號'].astype(str) + " | " + df['名稱']
        
        option_display = st.selectbox("搜尋/選擇材料", df['顯示名稱'].sort_values())
        
        # 找出對應項目
        selected_item = df[df['顯示名稱'] == option_display].iloc[0]
        unit_cost = selected_item['單顆成本']
        real_name = selected_item['名稱']
        real_id = selected_item['編號']
        
        # 這裡改為顯示「庫存(顆)」
        st.caption(f"編號: {real_id} | 庫存: {selected_item['庫存(顆)']} 顆 | 單價: ${unit_cost:.2f}")
