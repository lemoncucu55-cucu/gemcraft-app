import streamlit as st
import pandas as pd
import os
import time
from datetime import date, datetime

# ==========================================
# 1. 核心規格設定 (包含新加入的工資欄位)
# ==========================================
COLUMNS = ['編號', '倉庫', '分類', '名稱', '寬度mm', '長度mm', '形狀', '五行', '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', '庫存(顆)', '單顆成本']
DESIGN_COLUMNS = ['售出時間', '作品名稱', '材料明細', '材料小計', '工資', '雜支', '運費', '總成本', '建議售價x3', '建議售價x5', '備註']

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv'

# ==========================================
# 2. 安全載入函式 (防止畫面全白)
# ==========================================
def safe_load_csv(file_path, default_columns):
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            # 檢查是否有缺失欄位，有的話補 0
            for col in default_columns:
                if col not in df.columns:
                    df[col] = 0
            return df[default_columns]
        else:
            return pd.DataFrame(columns=default_columns)
    except Exception as e:
        # 如果檔案損壞導致讀取失敗，直接回傳空表格，不讓程式崩潰
        return pd.DataFrame(columns=default_columns)

# ==========================================
# 3. 初始化數據
# ==========================================
if 'inventory' not in st.session_state:
    st.session_state['inventory'] = safe_load_csv(DEFAULT_CSV_FILE, COLUMNS)
if 'design_sales' not in st.session_state:
    st.session_state['design_sales'] = safe_load_csv(DESIGN_SALES_FILE, DESIGN_COLUMNS)
if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 系統恢復", layout="wide")

# ==========================================
# 4. 側邊欄與頁面導航
# ==========================================
with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    admin_mode = (pwd == "admin123")
    
    st.divider()
    page = st.radio("前往", ["📦 庫存清單", "🧮 設計與成本計算"])

# --- 頁面 A: 庫存清單 ---
if page == "📦 庫存清單":
    st.header("📦 目前庫存總表")
    if st.session_state['inventory'].empty:
        st.warning("目前庫存為空。請確認 inventory_backup_v2.csv 是否已上傳至 GitHub。")
    else:
        st.dataframe(st.session_state['inventory'], use_container_width=True)

# --- 頁面 B: 設計與成本計算 (新增工資雜支) ---
elif page == "🧮 設計與成本計算":
    st.header("🧮 作品設計與成本計算")
    
    inv = st.session_state['inventory']
    if inv.empty:
        st.error("無庫存資料，無法進行設計。")
    else:
        # 材料選擇
        inv['label'] = inv.apply(lambda r: f"[{r['倉庫']}] {r['名稱']} ({r['寬度mm']}mm) | 存:{int(r['庫存(顆)'])}", axis=1)
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv['label'].tolist())
        qty = c2.number_input("數量", min_value=1, value=1)
        
        if st.button("📥 加入清單"):
            item = inv[inv['label'] == pick].iloc[0]
            st.session_state['current_design'].append({
                '名稱': item['名稱'], '數量': qty, '單價': float(item['單顆成本']), '小計': float(item['單顆成本']) * qty
            })
            st.rerun()

    # 顯示目前清單與輸入工資
    if st.session_state['current_design']:
        df_curr = pd.DataFrame(st.session_state['current_design'])
        st.table(df_curr[['名稱', '數量']])
        
        mat_subtotal = df_curr['小計'].sum()
        
        st.divider()
        st.subheader("💰 額外成本 (工資/雜支/運費)")
        # 無論是否為主管都顯示輸入框，方便作業
        cx, cy, cz = st.columns(3)
        labor = cx.number_input("🛠️ 工資 (元)", min_value=0, value=0)
        misc = cy.number_input("📦 雜支 (元)", min_value=0, value=0)
        ship = cz.number_input("🚚 運費 (元)", min_value=0, value=0)
        
        total_cost = mat_subtotal + labor + misc + ship
        
        if admin_mode:
            st.metric("🔥 總成本", f"${total_cost:.1f}")
            st.write(f"材料: ${mat_subtotal} | 額外: ${labor+misc+ship}")
            st.success(f"建議售價: x3=${round(total_cost*3)} | x5=${round(total_cost*5)}")

        with st.form("sale_form"):
            work_name = st.text_input("作品名稱", "未命名作品")
            if st.form_submit_button("✅ 儲存並售出"):
                # 儲存邏輯 (簡化以確保恢復)
                new_sale = {
                    '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    '作品名稱': work_name, '材料小計': mat_subtotal,
                    '工資': labor, '雜支': misc, '運費': ship, '總成本': total_cost,
                    '建議售價x3': round(total_cost*3), '建議售價x5': round(total_cost*5)
                }
                # 這裡僅示範，實際需補齊所有 DESIGN_COLUMNS 欄位
                st.session_state['design_sales'] = pd.concat([st.session_state['design_sales'], pd.DataFrame([new_sale])], ignore_index=True)
                st.session_state['design_sales'].to_csv(DESIGN_SALES_FILE, index=False, encoding='utf-8-sig')
                st.session_state['current_design'] = []
                st.success("紀錄成功！")
                time.sleep(1)
                st.rerun()

        if st.button("🗑️ 清空清單"):
            st.session_state['current_design'] = []
            st.rerun()
