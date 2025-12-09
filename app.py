import streamlit as st
import pandas as pd

# --- 1. 核心邏輯區 ---

def check_and_fill_ids(df):
    """
    核心功能：自動檢查表格，如果有「已選分類」但「沒編號」的項目，
    自動依照分類給予流水號 (例如: ST0001, AC0002)
    """
    # 設定分類對應的代號 (你可以自己修改這裡)
    prefix_map = {
        '天然石': 'ST',  # Stone
        '配件': 'AC',    # Accessory
        '耗材': 'OT',    # Others (原本是OT，可改為CS等)
    }

    # 逐行檢查
    for index, row in df.iterrows():
        # 如果「編號」是空的 且 「分類」有選
        is_id_empty = pd.isna(row['編號']) or row['編號'] == '' or row['編號'] is None
        category = row.get('分類')
        
        if is_id_empty and category in prefix_map:
            prefix = prefix_map[category]
            
            # 找出目前該分類最大的號碼
            # 1. 篩選出同分類所有的編號 (例如所有 ST 開頭的)
            existing_ids = df[df['編號'].astype(str).str.startswith(prefix, na=False)]['編號']
            
            max_num = 0
            for eid in existing_ids:
                try:
                    # 取出後面的數字部分 (ST0001 -> 1)
                    num = int(eid[2:]) 
                    if num > max_num:
                        max_num = num
                except:
                    pass
            
            # 生成新號碼 (最大號 + 1)，並補零至4位數
            new_id = f"{prefix}{str(max_num + 1).zfill(4)}"
            
            # 寫回表格
            df.at[index, '編號'] = new_id
            
    return df

# --- 2. 設定與資料庫初始化 ---

if 'inventory' not in st.session_state:
    # 預設資料 (這裡我幫你把編號先填好了)
    data = {
        '編號': ['ST0001', 'ST0002', 'ST0003', 'AC0001', 'OT0001'],
        '名稱': ['紫水晶 8mm', '粉晶 8mm', '白水晶 6mm', '925純銀隔珠', '日本彈力線'],
        '分類': ['天然石', '天然石', '天然石', '配件', '耗材'],
        '進貨價(整串)': [500, 450, 300, 1500, 200],
        '數量(顆/串)': [40, 40, 60, 100, 1], 
        '庫存(串/份)': [2, 3, 5, 1, 10],
    }
    df = pd.DataFrame(data)
    # 計算單顆成本
    df['單顆成本'] = df['進貨價(整串)'] / df['數量(顆/串)']
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
    st.info("💡 新增商品時，只要選擇「分類」，系統會自動產生編號 (例如 ST0004)。")

    # 1. 取得目前資料
    current_df = st.session_state['inventory']

    # 2. 顯示編輯器
    edited_df = st.data_editor(
        current_df.sort_values(by='編號'), # 依照編號排序
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,  # <--- 關鍵：隱藏原本醜醜的 0,1,2 索引
        column_order=("編號", "名稱", "分類", "進貨價(整串)", "數量(顆/串)", "庫存(串/份)", "單顆成本"),
        disabled=["編號", "單顆成本"] # 設定編號為唯讀，由系統自動產生
    )

    # 3. 處理資料變動
    if not edited_df.equals(current_df):
        # A. 先重新計算單顆成本
        edited_df['單顆成本'] = edited_df['進貨價(整串)'] / edited_df['數量(顆/串)']
        
        # B. 呼叫自動編號功能 (填補新的一行)
        edited_df = check_and_fill_ids(edited_df)
        
        # C. 存檔
        st.session_state['inventory'] = edited_df
        st.rerun() # 重新整理畫面以顯示新編號

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
        
        # 下拉選單：顯示 編號+名稱 比較好找
        # 建立一個暫時的欄位用來顯示
        df['顯示名稱'] = df['編號'].astype(str) + " | " + df['名稱']
        
        option_display = st.selectbox("搜尋/選擇材料", df['顯示名稱'].sort_values())
        
        # 找出對應的那一行
        selected_item = df[df['顯示名稱'] == option_display].iloc[0]
        unit_cost = selected_item['單顆成本']
        real_name = selected_item['名稱']
        real_id = selected_item['編號']
        
        st.caption(f"編號: {real_id} | 庫存: {selected_item['庫存(串/份)']} 串 | 單價: ${unit_cost:.2f}")
        
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

    # 右邊：計算結果區
    with col2:
        st.subheader("2. 成本明細表")
        
        if st.session_state['current_design']:
            design_df = pd.DataFrame(st.session_state['current_design'])
            
            st.dataframe(
                design_df, 
                use_container_width=True,
                hide_index=True, # 這裡也隱藏索引
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
