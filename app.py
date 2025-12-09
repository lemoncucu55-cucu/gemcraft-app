import streamlit as st
import pandas as pd

# --- 1. 設定與資料庫模擬 ---
# 初始化 Session State (模擬資料庫)
if 'inventory' not in st.session_state:
    # 預設資料
    data = {
        '名稱': ['紫水晶 8mm', '粉晶 8mm', '白水晶 6mm', '925純銀隔珠', '日本彈力線'],
        '分類': ['天然石', '天然石', '天然石', '配件', '耗材'],
        '進貨價(整串)': [500, 450, 300, 1500, 200],
        '數量(顆/串)': [40, 40, 60, 100, 1], 
        '庫存(串/份)': [2, 3, 5, 1, 10],
    }
    df = pd.DataFrame(data)
    # 自動計算單顆成本
    df['單顆成本'] = df['進貨價(整串)'] / df['數量(顆/串)']
    st.session_state['inventory'] = df

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# --- 2. UI 介面設計 ---

st.set_page_config(page_title="GemCraft 成本計算機", layout="wide")
st.title("💎 GemCraft 成本計算機")

# 側邊欄導航 (只剩兩個選項)
page = st.sidebar.radio("功能選單", ["📦 庫存管理", "🧮 設計與成本計算"])

# ==========================================
# 頁面 A: 庫存管理 (Inventory)
# ==========================================
if page == "📦 庫存管理":
    st.header("庫存資料庫")
    st.info("💡 修改進貨價或數量後，系統會自動重新計算單顆成本。")

    # 顯示並編輯表格
    edited_df = st.data_editor(
        st.session_state['inventory'],
        num_rows="dynamic", 
        use_container_width=True,
        # 設定單顆成本欄位為唯讀，避免手誤修改
        disabled=["單顆成本"]
    )

    # 如果表格有變動，更新 Session State
    if not edited_df.equals(st.session_state['inventory']):
        # 重新計算單顆成本公式
        edited_df['單顆成本'] = edited_df['進貨價(整串)'] / edited_df['數量(顆/串)']
        st.session_state['inventory'] = edited_df
        st.success("庫存數據已更新！")

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
        
        # 下拉選單
        option_name = st.selectbox("搜尋/選擇材料", df['名稱'])
        
        # 抓取選定材料的資訊
        selected_item = df[df['名稱'] == option_name].iloc[0]
        unit_cost = selected_item['單顆成本']
        
        st.caption(f"目前庫存: {selected_item['庫存(串/份)']} 串 | 單顆成本: ${unit_cost:.2f}")
        
        # 輸入數量
        qty = st.number_input("使用數量", min_value=1, value=1)
        
        # 加入按鈕
        if st.button("⬇️ 加入清單", type="primary"):
            st.session_state['current_design'].append({
                '名稱': option_name,
                '數量': qty,
                '單價': unit_cost,
                '小計': unit_cost * qty
            })
            st.rerun()

    # 右邊：計算結果區
    with col2:
        st.subheader("2. 成本明細表")
        
        if st.session_state['current_design']:
            # 轉成 DataFrame 顯示
            design_df = pd.DataFrame(st.session_state['current_design'])
            
            # 顯示簡單表格
            st.dataframe(
                design_df, 
                use_container_width=True,
                column_config={
                    "單價": st.column_config.NumberColumn(format="$%.2f"),
                    "小計": st.column_config.NumberColumn(format="$%.2f"),
                }
            )

            st.divider()

            # --- 成本計算核心 ---
            # 1. 純材料費
            material_cost = design_df['小計'].sum()
            
            # 2. 額外成本輸入 (選填)
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                labor_cost = st.number_input("工時/工資 (元)", value=0, help="如果不計算工資可填 0")
            with col_ex2:
                other_cost = st.number_input("包裝/雜支 (元)", value=0, help="如夾鏈袋、禮盒費用")

            # 3. 總成本
            total_cost = material_cost + labor_cost + other_cost

            # 顯示大數字
            st.markdown("### 💰 總成本合計")
            st.write(f"材料 ${material_cost:.1f} + 工資 ${labor_cost} + 雜支 ${other_cost}")
            st.metric(label="Total Cost", value=f"NT$ {total_cost:.1f}")

            # 清空按鈕
            st.divider()
            if st.button("🗑️ 清空重新計算"):
                st.session_state['current_design'] = []
                st.rerun()
                
            # 簡易匯出文字 (方便紀錄)
            st.caption("複製下方文字可存檔：")
            export_text = f"【成本紀錄】\n總成本: ${total_cost:.1f}\n(材料 ${material_cost:.1f} / 工資 ${labor_cost})\n明細:\n"
            for _, row in design_df.iterrows():
                export_text += f"- {row['名稱']} x{row['數量']}\n"
            st.text_area("", export_text, height=150)

        else:
            st.info("👈 請從左側選擇材料加入，開始計算成本。")
