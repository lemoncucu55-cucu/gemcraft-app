import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================

COLUMNS = [
    '編號', '倉庫', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

# 確保這裡包含了所有新欄位
DESIGN_SALES_COLUMNS = [
    '售出時間', '作品名稱', '材料明細', '材料小計', '工資', '雜支', '運費', '總成本', '建議售價x3', '建議售價x5', '備註'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', 
    '廠商', '數量變動', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv'

# ==========================================
# 2. 核心函式
# ==========================================

def save_inventory():
    try: st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except: pass

def save_design_sales():
    try: st.session_state['design_sales'].to_csv(DESIGN_SALES_FILE, index=False, encoding='utf-8-sig')
    except: pass

def make_inventory_label(row):
    sz = f"{row['寬度mm']}mm" if row['長度mm']==0 else f"{row['寬度mm']}x{row['長度mm']}mm"
    elem = f"({row['五行']})" if row['五行'] else ""
    return f"[{row['倉庫']}] {elem} {row['編號']} | {row['名稱']} | {row['形狀']} ({sz}) | 存:{int(row['庫存(顆)'])}"

# ==========================================
# 3. 初始化 (含自動補足舊檔功能)
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        st.session_state['inventory'] = pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig')
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'design_sales' not in st.session_state:
    if os.path.exists(DESIGN_SALES_FILE):
        df_ds = pd.read_csv(DESIGN_SALES_FILE, encoding='utf-8-sig')
        # 【關鍵】自動補足舊檔案缺少的欄位，防止程式當機
        for col in DESIGN_SALES_COLUMNS:
            if col not in df_ds.columns:
                df_ds[col] = 0
        st.session_state['design_sales'] = df_ds[DESIGN_SALES_COLUMNS]
    else:
        st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)

if 'current_design' not in st.session_state: st.session_state['current_design'] = []
if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False

# ==========================================
# 4. 主介面
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理", layout="wide")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    page = st.radio("前往", ["📦 庫存管理與進貨", "🧮 設計與成本計算"])
    
    if not st.session_state['design_sales'].empty:
        st.download_button("💍 下載作品銷售紀錄", st.session_state['design_sales'].to_csv(index=False).encode('utf-8-sig'), f'sales_{date.today()}.csv', "text/csv")

if page == "🧮 設計與成本計算":
    st.header("🧮 設計與成本計算")
    
    # A. 選擇材料區
    inv = st.session_state['inventory']
    if not inv.empty:
        inv_l = inv.copy()
        inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv_l['label'].tolist())
        qty_pick = c2.number_input("數量", min_value=1, value=1)
        if st.button("📥 加入清單"):
            idx = inv_l[inv_l['label'] == pick].index[0]
            item = inv.loc[idx]
            st.session_state['current_design'].append({
                '編號': item['編號'], '名稱': item['名稱'], '數量': qty_pick,
                '單價': float(item['單顆成本']), '小計': float(item['單顆成本']) * qty_pick
            })
            st.rerun()

    # B. 核心顯示與工資計算 (確保在這裡顯示)
    if st.session_state['current_design']:
        df_design = pd.DataFrame(st.session_state['current_design'])
        st.subheader("📋 目前設計清單")
        st.table(df_design[['名稱', '數量']]) # 非主管只看名稱數量
        
        mat_subtotal = df_design['小計'].sum()
        
        # --- 強制顯示：工資/雜支/運費 ---
        st.divider()
        st.subheader("💰 額外成本輸入")
        col_a, col_b, col_c = st.columns(3)
        labor = col_a.number_input("🛠️ 工資 (元)", min_value=0, value=0, step=10)
        misc = col_b.number_input("📦 雜支 (元)", min_value=0, value=0, step=5)
        ship = col_c.number_input("🚚 運費 (元)", min_value=0, value=0, step=1)
        
        total_cost = mat_subtotal + labor + misc + ship

        # 僅主管可看詳細金額
        if st.session_state['admin_mode']:
            st.write(f"材料成本: ${mat_subtotal:.1f}")
            st.metric("作品總成本", f"${total_cost:.1f}")
            st.success(f"建議售價: x3=${round(total_cost*3)} | x5=${round(total_cost*5)}")

        # C. 售出表單
        with st.form("sale_final"):
            work_name = st.text_input("作品名稱", "未命名作品")
            note = st.text_area("備註")
            if st.form_submit_button("✅ 售出並存檔紀錄"):
                details = ", ".join([f"{d['名稱']}x{d['數量']}" for d in st.session_state['current_design']])
                new_row = {
                    '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    '作品名稱': work_name, '材料明細': details, '材料小計': mat_subtotal,
                    '工資': labor, '雜支': misc, '運費': ship, '總成本': total_cost,
                    '建議售價x3': round(total_cost*3), '建議售價x5': round(total_cost*5), '備註': note
                }
                st.session_state['design_sales'] = pd.concat([st.session_state['design_sales'], pd.DataFrame([new_row])], ignore_index=True)
                
                # 扣庫存
                for d in st.session_state['current_design']:
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == d['編號'], '庫存(顆)'] -= d['數量']
                
                save_inventory(); save_design_sales()
                st.session_state['current_design'] = []
                st.success("紀錄已成功售出！")
                time.sleep(1); st.rerun()

        if st.button("🗑️ 清空設計"):
            st.session_state['current_design'] = []
            st.rerun()
