import streamlit as st
import pandas as pd
from datetime import date
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

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 3. UI 介面設計
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "🧮 設計與成本計算"])
    st.divider()
    st.header("💾 資料備份")
    df_to_download = st.session_state['inventory']
    if not df_to_download.empty:
        csv = df_to_download.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存表 (CSV)", csv, f'inventory_backup_{date.today()}.csv', "text/csv")
    
    uploaded_file = st.file_uploader("📤 上傳復原庫存 (CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file)
            uploaded_df['編號'] = uploaded_df['編號'].astype(str)
            if st.button("⚠️ 確認覆蓋目前資料"):
                st.session_state['inventory'] = uploaded_df
                st.success("資料已還原！")
                st.rerun()
        except: st.error("讀取失敗")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    
    with st.expander("📝 點擊展開：新增進貨資料", expanded=False):
        with st.form("add_new_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: new_cat = st.selectbox("分類", ["天然石", "配件", "耗材"])
            with c2: new_name = st.text_input("名稱", placeholder="例如：紫水晶")
            with c3: new_size = st.number_input("尺寸 (mm)", 0.0, step=0.5, format="%.1f")
            
            c4, c5, c6 = st.columns(3)
            with c4: new_shape = st.selectbox("形狀", ["圓珠", "切角", "鑽切", "圓筒", "不規則", "造型"])
            with c5: new_element = st.selectbox("五行", ["金", "木", "水", "火", "土", "綜合"])
            with c6: new_supplier = st.selectbox("廠商", SUPPLIERS)
            
            c7, c8, c9 = st.columns(3)
            with c7: new_price = st.number_input("進貨總價", 0)
            with c8: new_qty = st.number_input("進貨數量", 1)
            with c9: new_date = st.date_input("進貨日期", value=date.today())
            
            if st.form_submit_button("➕ 確認新增"):
                if not new_name: st.error("需填寫名稱")
                else:
                    new_id = generate_new_id(new_cat, st.session_state['inventory'])
                    unit_cost = new_price / new_qty if new_qty > 0 else 0
                    new_row = {
                        '編號': new_id, '分類': new_cat, '名稱': new_name, '尺寸mm': new_size,
                        '形狀': new_shape, '五行': new_element, '進貨總價': new_price,
                        '進貨數量(顆)': new_qty, '進貨日期': new_date, '進貨廠商': new_supplier,
                        '庫存(顆)': new_qty, '單顆成本': unit_cost
                    }
                    st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"新增成功：{new_id}")
                    st.rerun()

    current_df = st.session_state['inventory']
    # 這裡顯示時，依照五行排序，方便管理查看
    if not current_df.empty:
         current_df = current_df.sort_values(by=['分類', '五行', '名稱'])

    edited_df = st.data_editor(
        current_df, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_order=("編號", "分類", "名稱", "尺寸mm", "形狀", "五行", "庫存(顆)", "單顆成本", "進貨廠商"),
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
# 頁面 B: 設計 (重點修改區)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.header("📿 手鍊設計工作檯")

    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.subheader("1. 選擇材料")
        df = st.session_state['inventory']
        
        # 分類篩選器
        cat_options = ["全部"] + ["天然石", "配件", "耗材"]
        selected_cat = st.radio("🔍 依分類篩選", cat_options, horizontal=True)

        valid_df = df[df['編號'].notna()].copy()
        
        if selected_cat != "全部":
            valid_df = valid_df[valid_df['分類'] == selected_cat]

        if not valid_df.empty:
            # ★★★ 核心修改：排序邏輯 (五行 -> 名稱) ★★★
            # 填補空值以免排序報錯
            valid_df['五行'] = valid_df['五行'].fillna('未分類')
            valid_df['名稱'] = valid_df['名稱'].fillna('')
            
            # 執行排序
            valid_df = valid_df.sort_values(by=['五行', '名稱'])
            
            # 建立顯示名稱：[五行] 名稱 (規格) | 編號
            valid_df['顯示名稱'] = (
                "[" + valid_df['五行'].astype(str) + "] " +
                valid_df['名稱'].astype(str) + 
                " (" + valid_df['尺寸mm'].astype(str) + "mm " + valid_df['形狀'].astype(str) + ")" +
                " | " + valid_df['編號'].astype(str)
            )
            
            # 這裡直接使用已經排好序的 '顯示名稱'，不要再 sort_values()
            option_display = st.selectbox("搜尋材料", valid_df['顯示名稱'])
            
            # 抓取資料
            item = valid_df[valid_df['顯示名稱'] == option_display].iloc[0]
            
            st.info(f"**{item['名稱']}**\n\n分類: {item['分類']} | 五行: {item['五行']}\n規格: {item['尺寸mm']}mm {item['形狀']}\n\n庫存: {item['庫存(顆)']} | 成本: ${item['單顆成本']:.1f}")
            
            qty = st.number_input("使用數量", 1)
            
            if st.button("⬇️ 加入設計圖", type="primary"):
                # 直接寫死文字
                new_entry = {
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
            
            if st.button("🗑️ 清空重算", type="secondary"):
                st.session_state['current_design'] = []
                st.rerun()
                
            txt = f"【報價單】總計 ${final_total:.0f}\n"
            for _, row in design_df.iterrows():
                txt += f"- [{row['分類']}] {row['名稱']} ({row['規格']}) x{row['使用數量']}\n"
            st.text_area("複製文字", txt)
            
        else:
            st.info("👈 清單是空的，請先加入材料")
