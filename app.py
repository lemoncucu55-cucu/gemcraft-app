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
        
    if df.empty:
        return f"{prefix}0001"
    
    df_str = df.copy()
    df_str['編號'] = df_str['編號'].astype(str)
    
    existing_ids = df_str[df_str['編號'].str.startswith(prefix, na=False)]['編號']
    
    if existing_ids.empty:
        return f"{prefix}0001"
    
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

SUPPLIERS = [
    "小聰頭", "小聰頭-13", "小聰頭-千千", "小聰頭-子馨", "小聰頭-小宇", "小聰頭-尼克", "小聰頭-周三寶", "小聰頭-蒨",
    "永安", "石之靈", "多加市集", "決益X", "昇輝", "星辰Crystal", "珍珠包金", "格魯特", "御金坊",
    "淘-天使街", "淘-東吳天然石坊", "淘-物物居", "淘-軒閣珠寶", "淘-鈦鋼潮牌", "淘-義烏卡樂芙", 
    "淘-鼎喜", "淘-銀拍檔", "淘-廣州小銀子", "淘-慶和銀飾", "淘-賽維雅珠寶", "淘-ins網紅玻璃杯",
    "淘-Mary", "淘-Super Search",
    "祥玥", "雪霖", "晶格格", "愛你一生", "福祿壽銀飾", "億伙", "廠商", "寶城水晶", "Rich"
]

if 'inventory' not in st.session_state:
    df = pd.DataFrame(columns=[
        '編號', '分類', '名稱', '尺寸mm', '形狀', '五行', 
        '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本'
    ])
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
    
    # --- Part 1: 新增進貨表單 ---
    st.markdown("### 📝 新增進貨資料")
    
    with st.form("add_item_form", clear_on_submit=True):
        st.caption("請依照順序填寫，送出後系統會自動產生編號並加入下方表格。")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            new_cat = st.selectbox("1. 分類", ["天然石", "配件", "耗材"])
        with c2:
            new_name = st.text_input("2. 名稱", placeholder="例如：紫水晶")
        with c3:
            new_size = st.number_input("3. 尺寸 (mm)", min_value=0.0, step=0.5, format="%.1f")

        c4, c5, c6 = st.columns(3)
        with c4:
            new_shape = st.selectbox("4. 形狀", ["圓珠", "切角", "鑽切", "圓筒", "不規則", "造型"])
        with c5:
            new_element = st.selectbox("5. 五行", ["金", "木", "水", "火", "土", "綜合"])
        with c6:
            new_supplier = st.selectbox("6. 進貨廠商", SUPPLIERS)

        c7, c8, c9 = st.columns(3)
        with c7:
            new_price = st.number_input("7. 進貨總價", min_value=0)
        with c8:
            new_qty = st.number_input("8. 進貨數量 (顆)", min_value=1)
        with c9:
            new_date = st.date_input("9. 進貨日期", value=date.today())

        submitted = st.form_submit_button("➕ 確認新增入庫", type="primary")

        if submitted:
            if not new_name:
                st.error("❌ 請填寫「名稱」！")
            else:
                new_id = generate_new_id(new_cat, st.session_state['inventory'])
                
                # 計算單顆成本 (保持原始精度，顯示時再格式化)
                unit_cost = new_price / new_qty if new_qty > 0 else 0
                
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
                    '庫存(顆)': new_qty,
                    '單顆成本': unit_cost
                }
                
                new_df = pd.DataFrame([new_data])
                if st.session_state['inventory'].empty:
                     st.session_state['inventory'] = new_df
                else:
                     st.session_state['inventory'] = pd.concat([st.session_state['inventory'], new_df], ignore_index=True)
                
                st.success(f"✅ 已新增：{new_id} {new_name}")
                st.rerun()

    st.divider()

    # --- Part 2: 庫存總表 ---
    st.markdown("### 📊 目前庫存清單")
    
    current_df = st.session_state['inventory']
    
    edited_df = st.data_editor(
        current_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=("編號", "分類", "名稱", "尺寸mm", "形狀", "五行", "庫存(顆)", "單顆成本", "進貨廠商", "進貨日期"),
        disabled=["編號", "單顆成本"],
        key="inventory_table",
        # ★★★ 設定顯示格式：保留 1 位小數 ★★★
        column_config={
            "單顆成本": st.column_config.NumberColumn(format="$%.1f"),
            "尺寸mm": st.column_config.NumberColumn(format="%.1f"),
        }
    )
    
    if not edited_df.equals(current_df):
        p_price = pd.to_numeric(edited_df['進貨總價'], errors='coerce').fillna(0)
        p_qty = pd.to_numeric(edited_df['進貨數量(顆)'], errors='coerce').fillna(0)
        edited_df['單顆成本'] = p_price / p_qty.replace(0, 1)
        
        st.session_state['inventory'] = edited_df
        st.rerun()


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
        
        if not df.empty and '編號' in df.columns:
            valid_df = df[df['編號'].notna() & (df['編號'] != '')].copy()
            
            if not valid_df.empty:
                valid_df['顯示名稱'] = (
                    valid_df['編號'].astype(str) + " | " + 
                    valid_df['名稱'].astype(str) + 
                    " (" + valid_df['尺寸mm'].astype(str) + "mm)"
                )
                
                option_display = st.selectbox("搜尋/選擇材料", valid_df['顯示名稱'].sort_values())
                
                selected_item = valid_df[valid_df['顯示名稱'] == option_display].iloc[0]
                
                info_content = f"""
                **{selected_item['名稱']}**
                
                - 編號: `{selected_item['編號']}`
                - 規格: {selected_item['尺寸mm']}mm / {selected_item['形狀']}
                - 五行: {selected_item['五行']}
                - 庫存: **{selected_item['庫存(顆)']}** 顆
                - 廠商: {selected_item['進貨廠商']}
                """
                st.info(info_content)
                
                unit_cost = selected_item['單顆成本']
                # ★★★ 設定顯示格式：保留 1 位小數 ★★★
                st.metric("單顆成本", f"${unit_cost:.1f}")
                
                qty = st.number_input("使用數量", min_value=1, value=1)
                
                if st.button("⬇️ 加入設計圖", type="primary"):
                    st.session_state['current_design'].append({
                        '編號': selected_item['編號'],
                        '名稱': selected_item['名稱'],
                        '規格': f"{selected_item['尺寸mm']}mm {selected_item['形狀']}",
                        '數量': qty,
                        '單價': unit_cost,
                        '小計': unit_cost * qty
                    })
                    st.rerun()
            else:
                 st.warning("目前沒有可用的庫存資料，請先新增。")
        else:
            st.warning("庫存是空的，請先去「庫存管理」新增資料。")

    # --- 右邊：計算結果區 ---
    with col2:
        st.subheader("2. 設計清單與成本")
        
        if st.session_state['current_design']:
            design_df = pd.DataFrame(st.session_state['current_design'])
            
            st.dataframe(
                design_df, 
                use_container_width=True,
                hide_index=True,
                column_order=("編號", "名稱", "規格", "數量", "單價", "小計"),
                # ★★★ 設定顯示格式：保留 1 位小數 ★★★
                column_config={
                    "單價": st.column_config.NumberColumn(format="$%.1f"),
                    "小計": st.column_config.NumberColumn(format="$%.1f"),
                }
            )

            st.divider()

            material_cost = design_df['小計'].sum()
            
            c_labor, c_other = st.columns(2)
            with c_labor:
                labor_cost = st.number_input("工資 (元)", value=0)
            with c_other:
                other_cost = st.number_input("雜支 (元)", value=0)

            total_cost = material_cost + labor_cost + other_cost

            st.markdown("### 💰 總成本合計")
            # ★★★ 設定顯示格式：保留 1 位小數 ★★★
            st.metric(label="Total Cost", value=f"NT$ {total_cost:.1f}")

            st.divider()
            
            if st.button("🗑️ 清空重新計算"):
                st.session_state['current_design'] = []
                st.rerun()
                
            st.caption("📋 複製報價單：")
            # ★★★ 設定顯示格式：保留 1 位小數 ★★★
            export_text = f"【成本單】總計 ${total_cost:.1f}\n"
            for _, row in design_df.iterrows():
                export_text += f"- {row['名稱']} ({row['規格']}) x{row['數量']}\n"
            st.text_area("", export_text, height=150)

        else:
            st.info("👈 請從左側選擇材料加入")
