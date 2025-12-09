import streamlit as st
import pandas as pd

# ==========================================
# 1. 核心邏輯區 (函式)
# ==========================================

def check_and_fill_ids(df):
    """
    自動編號邏輯
    """
    prefix_map = {
        '天然石': 'ST',  # Stone
        '配件': 'AC',    # Accessory
        '耗材': 'OT',    # Others
    }

    # 重置索引，確保新行有正確的順序
    df = df.reset_index(drop=True)

    for index, row in df.iterrows():
        # 檢查編號是否為空
        is_id_empty = pd.isna(row['編號']) or row['編號'] == '' or row['編號'] is None
        category = row.get('分類')
        
        # 只有當「編號是空的」且「分類已選擇」時，才進行補號
        if is_id_empty and category in prefix_map:
            prefix = prefix_map[category]
            
            # 找出該分類目前最大號碼
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

# ==========================================
# 2. 設定與資料庫初始化
# ==========================================

if 'inventory' not in st.session_state:
    data = {
        '編號': ['ST0001', 'ST0002', 'ST0003', 'AC0001', 'OT0001'],
        '名稱': ['紫水晶 8mm', '粉晶 8mm', '白水晶 6mm', '925純銀隔珠', '日本彈力線'],
        '分類': ['天然石', '天然石', '天然石', '配件', '耗材'],
        '進貨總價': [500, 450, 300, 1500, 200],
        '進貨數量(顆)': [40, 40, 60, 100, 1], 
        '庫存(顆)': [80, 120, 300, 100, 10], 
    }
    df = pd.DataFrame(data)
    df['單顆成本'] = df['進貨總價'] / df['進貨數量(顆)'].replace(0, 1)
    st.session_state['inventory'] = df

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 3. UI 介面設計
# ==========================================

st.set_page_config(page_title="GemCraft 成本計算機", layout="wide")
st.title("💎 GemCraft 成本計算機")

page = st.sidebar.radio("功能選單", ["📦 庫存管理", "🧮 設計與成本計算"])

# ------------------------------------------
# 頁面 A: 庫存管理 (Inventory)
# ------------------------------------------
if page == "📦 庫存管理":
    st.header("庫存資料庫")
    
    col_msg, col_btn = st.columns([3, 1])
    with col_msg:
        st.info("💡 操作提示：輸入名稱 -> 選擇分類 -> **按 Enter 或點擊空白處**，編號才會產生。")
    with col_btn:
        # ★★★ 新增：手動強制更新按鈕 ★★★
        if st.button("🔄 強制更新表格", type="primary"):
            st.rerun()

    # 1. 確保顯示前先排序，避免編輯器跳動
    current_df = st.session_state['inventory'].sort_values(by='編號').reset_index(drop=True)

    # 2. 顯示編輯器
    edited_df = st.data_editor(
        current_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=("編號", "名稱", "分類", "進貨總價", "進貨數量(顆)", "庫存(顆)", "單顆成本"),
        disabled=["編號", "單顆成本"],
        key="inventory_editor" # 加上 key 讓狀態更穩定
    )

    # 3. 偵測變動
    if not edited_df.equals(current_df):
        # 重置索引
        edited_df = edited_df.reset_index(drop=True)

        # 轉型與防呆計算
        p_price = pd.to_numeric(edited_df['進貨總價'], errors='coerce').fillna(0)
        p_qty = pd.to_numeric(edited_df['進貨數量(顆)'], errors='coerce').fillna(0)
        edited_df['單顆成本'] = p_price / p_qty.replace(0, 1)
        
        # 自動編號
        edited_df = check_and_fill_ids(edited_df)
        
        # 存檔
        st.session_state['inventory'] = edited_df
        st.rerun()

# ------------------------------------------
# 頁面 B: 設計與成本計算 (Design & Cost)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.header("手鍊成本計算")

    col1, col2 = st.columns([1, 1.5])

    # --- 左邊：選材區 ---
    with col1:
        st.subheader("1. 選擇材料")
        df = st.session_state['inventory']
        
        # 排除空資料
        valid_df = df[df['編號'].notna() & (df['編號'] != '')].copy()
        valid_df['顯示名稱'] = valid_df['編號'].astype(str) + " | " + valid_df['名稱']
        
        if not valid_df.empty:
            option_display = st.selectbox("搜尋/選擇材料", valid_df['顯示名稱'].sort_values())
            
            selected_item = valid_df[valid_df['顯示名稱'] == option_display].iloc[0]
            unit_cost = selected_item['單顆成本']
            real_name = selected_item['名稱']
            real_id = selected_item['編號']
            stock_qty = selected_item['庫存(顆)']
            
            st.caption(f"編號: {real_id} | 庫存: {stock_qty} 顆 | 單價: ${unit_cost:.2f}")
            
            qty = st.number_input("使用數量", min_value=1, value=1)
            
            if st.button("⬇️ 加入清單", type="primary"):
                st.session_state['current_design'].append({
                    '編號': real_id,
                    '名稱': real_name,
                    '數量': qty,
                    '單價': unit_cost,
                    '小計': unit_cost * qty
                })
                st.rerun()
        else:
            st.warning("庫存是空的，請先去「庫存管理」新增資料喔！")

    # --- 右邊：計算結果區 ---
    with col2:
        st.subheader("2. 成本明細表")
        
        if st.session_state['current_design']:
            design_df = pd.DataFrame(st.session_state['current_design'])
            
            st.dataframe(
                design_df, 
                use_container_width=True,
                hide_index=True,
                column_order=("編號", "名稱", "數量", "單價", "小計"),
                column_config={
                    "單價": st.column_config.NumberColumn(format="$%.2f"),
                    "小計": st.column_config.NumberColumn(format="$%.2f"),
                }
            )

            st.divider()

            material_cost = design_df['小計'].sum()
            
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                labor_cost = st.number_input("工資 (元)", value=0)
            with col_ex2:
                other_cost = st.number_input("雜支 (元)", value=0)

            total_cost = material_cost + labor_cost + other_cost

            st.markdown("### 💰 總成本合計")
            st.metric(label="Total Cost", value=f"NT$ {total_cost:.1f}")

            st.divider()
            
            if st.button("🗑️ 清空重新計算"):
                st.session_state['current_design'] = []
                st.rerun()
                
            st.caption("複製存檔：")
            export_text = f"【成本單】總計 ${total_cost:.1f}\n"
            for _, row in design_df.iterrows():
                export_text += f"- {row['編號']} {row['名稱']} x{row['數量']}\n"
            st.text_area("", export_text, height=150)

        else:
            st.info("👈 請從左側選擇材料加入")
