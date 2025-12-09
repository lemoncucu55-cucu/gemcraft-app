import streamlit as st
import pandas as pd
from datetime import date
import io

# ==========================================
# 1. 核心邏輯區
# ==========================================

def generate_new_id(category, df):
    """產生單一新編號"""
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

# ==========================================
# 2. 設定與初始化
# ==========================================

SUPPLIERS = [
    "小聰頭", "小聰頭-13", "小聰頭-千千", "小聰頭-子馨", "小聰頭-小宇", "小聰頭-尼克", "小聰頭-周三寶", "小聰頭-蒨",
    "永安", "石之靈", "多加市集", "決益X", "昇輝", "星辰Crystal", "珍珠包金", "格魯特", "御金坊",
    "淘-天使街", "淘-東吳天然石坊", "淘-物物居", "淘-軒閣珠寶", "淘-鈦鋼潮牌", "淘-義烏卡樂芙", 
    "淘-鼎喜", "淘-銀拍檔", "淘-廣州小銀子", "淘-慶和銀飾", "淘-賽維雅珠寶", "淘-ins網紅玻璃杯",
    "淘-Mary", "淘-Super Search",
    "祥玥", "雪霖", "晶格格", "愛你一生", "福祿壽銀飾", "億伙", "廠商", "寶城水晶", "Rich"
]

COLUMNS = [
    '編號', '分類', '名稱', '尺寸mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本'
]

if 'inventory' not in st.session_state:
    st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 3. UI 介面設計
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

# --- 側邊欄 ---
with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "🧮 設計與成本計算"])
    
    st.divider()
    st.header("💾 資料備份與還原")
    
    df_to_download = st.session_state['inventory']
    if not df_to_download.empty:
        csv = df_to_download.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 下載庫存表 (CSV)",
            data=csv,
            file_name=f'inventory_backup_{date.today()}.csv',
            mime='text/csv',
            type="primary"
        )
    else:
        st.caption("目前無資料可下載")

    uploaded_file = st.file_uploader("📤 上傳復原庫存 (CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            if set(COLUMNS).issubset(uploaded_df.columns):
                uploaded_df['編號'] = uploaded_df['編號'].astype(str)
                if st.button("⚠️ 確認覆蓋目前資料"):
                    st.session_state['inventory'] = uploaded_df
                    st.success("資料已還原！")
                    st.rerun()
            else:
                st.error("格式錯誤！")
        except Exception as e:
            st.error(f"讀取失敗: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理與進貨
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    
    # 切換模式：新品 vs 補貨
    mode = st.radio("請選擇操作模式：", ["✨ 新增新品 (建立新編號)", "🔄 舊品補貨 (合併庫存/平均成本)"], horizontal=True)
    
    if mode == "✨ 新增新品 (建立新編號)":
        with st.form("add_new_form", clear_on_submit=True):
            st.caption("建立全新的商品資料，系統會產生新的編號。")
            c1, c2, c3 = st.columns(3)
            with c1: new_cat = st.selectbox("1. 分類", ["天然石", "配件", "耗材"])
            with c2: new_name = st.text_input("2. 名稱", placeholder="例如：紫水晶")
            with c3: new_size = st.number_input("3. 尺寸 (mm)", min_value=0.0, step=0.5, format="%.1f")

            c4, c5, c6 = st.columns(3)
            with c4: new_shape = st.selectbox("4. 形狀", ["圓珠", "切角", "鑽切", "圓筒", "不規則", "造型"])
            with c5: new_element = st.selectbox("5. 五行", ["金", "木", "水", "火", "土", "綜合"])
            with c6: new_supplier = st.selectbox("6. 進貨廠商", SUPPLIERS)

            c7, c8, c9 = st.columns(3)
            with c7: new_price = st.number_input("7. 進貨總價", min_value=0)
            with c8: new_qty = st.number_input("8. 進貨數量 (顆)", min_value=1)
            with c9: new_date = st.date_input("9. 進貨日期", value=date.today())

            if st.form_submit_button("➕ 確認新增入庫", type="primary"):
                if not new_name:
                    st.error("❌ 請填寫名稱！")
                else:
                    new_id = generate_new_id(new_cat, st.session_state['inventory'])
                    unit_cost = new_price / new_qty if new_qty > 0 else 0
                    new_data = {
                        '編號': new_id, '分類': new_cat, '名稱': new_name, '尺寸mm': new_size,
                        '形狀': new_shape, '五行': new_element, '進貨總價': new_price,
                        '進貨數量(顆)': new_qty, '進貨日期': new_date, '進貨廠商': new_supplier,
                        '庫存(顆)': new_qty, '單顆成本': unit_cost
                    }
                    new_df = pd.DataFrame([new_data])
                    st.session_state['inventory'] = pd.concat([st.session_state['inventory'], new_df], ignore_index=True)
                    st.success(f"已新增：{new_id} {new_name}")
                    st.rerun()

    else: # 舊品補貨模式
        st.info("💡 補貨模式會將「新進貨的金額」與「現有庫存」進行加權平均，算出新的成本。")
        
        df = st.session_state['inventory']
        if df.empty:
            st.warning("目前沒有任何庫存資料，請先新增新品。")
        else:
            # 建立選單
            valid_df = df[df['編號'].notna() & (df['編號'] != '')].copy()
            valid_df['顯示名稱'] = valid_df['編號'].astype(str) + " | " + valid_df['名稱'] + " (" + valid_df['尺寸mm'].astype(str) + "mm)"
            
            # 使用 form 避免一直重整
            with st.form("restock_form", clear_on_submit=True):
                target_item_str = st.selectbox("搜尋要補貨的商品", valid_df['顯示名稱'].sort_values())
                
                c_r1, c_r2, c_r3 = st.columns(3)
                with c_r1: restock_price = st.number_input("本次進貨總價", min_value=0)
                with c_r2: restock_qty = st.number_input("本次進貨數量 (顆)", min_value=1)
                with c_r3: restock_date = st.date_input("補貨日期", value=date.today())
                
                restock_supplier = st.selectbox("本次進貨廠商", SUPPLIERS)
                
                if st.form_submit_button("🔄 確認補貨並更新成本", type="primary"):
                    # 1. 找出原本的那一行資料
                    target_id = target_item_str.split(" | ")[0]
                    # 使用 index 來定位修改
                    idx = df.index[df['編號'] == target_id].tolist()[0]
                    
                    # 2. 取得舊數據
                    old_stock = df.at[idx, '庫存(顆)']
                    old_cost = df.at[idx, '單顆成本']
                    
                    # 3. 計算加權平均
                    # 舊庫存總值 = 舊數量 * 舊成本
                    old_total_value = old_stock * old_cost
                    # 新庫存總值 = 舊總值 + 本次花費
                    new_total_value = old_total_value + restock_price
                    # 新總數量
                    new_total_qty = old_stock + restock_qty
                    
                    # 新單顆成本
                    new_avg_cost = new_total_value / new_total_qty if new_total_qty > 0 else 0
                    
                    # 4. 更新資料庫
                    df.at[idx, '庫存(顆)'] = new_total_qty
                    df.at[idx, '單顆成本'] = new_avg_cost
                    df.at[idx, '進貨日期'] = restock_date # 更新為最新日期
                    df.at[idx, '進貨廠商'] = restock_supplier # 更新為最新廠商
                    
                    st.session_state['inventory'] = df
                    st.success(f"補貨成功！{target_id} 庫存變更為 {new_total_qty} 顆，新平均成本 ${new_avg_cost:.1f}")
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

    with col1:
        st.subheader("1. 選擇材料")
        df = st.session_state['inventory']
        
        if not df.empty and '編號' in df.columns:
            valid_df = df[df['編號'].notna() & (df['編號'] != '')].copy()
            if not valid_df.empty:
                valid_df['顯示名稱'] = (valid_df['編號'].astype(str) + " | " + valid_df['名稱'].astype(str) + " (" + valid_df['尺寸mm'].astype(str) + "mm)")
                option_display = st.selectbox("搜尋/選擇材料", valid_df['顯示名稱'].sort_values())
                selected_item = valid_df[valid_df['顯示名稱'] == option_display].iloc[0]
                
                info_content = f"""
                **{selected_item['名稱']}**
                - 編號: `{selected_item['編號']}`
                - 規格: {selected_item['尺寸mm']}mm / {selected_item['形狀']}
                - 庫存: **{selected_item['庫存(顆)']}** 顆
                - 廠商: {selected_item['進貨廠商']}
                """
                st.info(info_content)
                
                unit_cost = selected_item['單顆成本']
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
            else: st.warning("目前沒有可用的庫存資料。")
        else: st.warning("庫存是空的。")

    with col2:
        st.subheader("2. 設計清單與成本")
        if st.session_state['current_design']:
            design_df = pd.DataFrame(st.session_state['current_design'])
            st.dataframe(
                design_df, use_container_width=True, hide_index=True,
                column_order=("編號", "名稱", "規格", "數量", "單價", "小計"),
                column_config={"單價": st.column_config.NumberColumn(format="$%.1f"), "小計": st.column_config.NumberColumn(format="$%.1f")}
            )
            st.divider()
            material_cost = design_df['小計'].sum()
            c_labor, c_other = st.columns(2)
            with c_labor: labor_cost = st.number_input("工資 (元)", value=0)
            with c_other: other_cost = st.number_input("雜支 (元)", value=0)
            total_cost = material_cost + labor_cost + other_cost
            st.markdown("### 💰 總成本合計")
            st.metric(label="Total Cost", value=f"NT$ {total_cost:.1f}")
            st.divider()
            if st.button("🗑️ 清空重新計算"):
                st.session_state['current_design'] = []
                st.rerun()
            st.caption("📋 複製報價單：")
            export_text = f"【成本單】總計 ${total_cost:.1f}\n"
            for _, row in design_df.iterrows(): export_text += f"- {row['名稱']} ({row['規格']}) x{row['數量']}\n"
            st.text_area("", export_text, height=150)
        else: st.info("👈 請從左側選擇材料加入")
