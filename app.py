import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================

# 系統標準欄位 (順序非常重要，對應 CSV 的欄位順序)
COLUMNS = [
    '編號', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '編號', '分類', '名稱', '規格', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

DESIGN_HISTORY_COLUMNS = [
    '單號', '日期', '總顆數', '材料成本', '工資', '雜支', 
    '總成本', '售價(x3)', '售價(x5)', '明細內容'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DESIGN_HISTORY_FILE = 'design_sales_history.csv'

# 選單預設值
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

# ==========================================
# 2. 核心函式
# ==========================================

def save_inventory():
    """儲存庫存到 CSV"""
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"存檔失敗: {e}")

def save_design_history():
    """儲存銷售紀錄到 CSV"""
    try:
        if 'design_history' in st.session_state:
            st.session_state['design_history'].to_csv(DESIGN_HISTORY_FILE, index=False, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"存檔失敗: {e}")

def clean_data(df):
    """
    資料清理核心：
    1. 確保欄位名稱正確
    2. 確保數值欄位真的是數字 (空白轉0)
    3. 確保文字欄位真的是文字 (空白轉空字串)
    """
    # 1. 確保欄位數量與名稱一致
    # 如果欄位少於標準，補空白
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
            
    # 只取標準欄位，並依照順序排列
    df = df[COLUMNS]

    # 2. 數值強制轉型 (防呆：把 'nan', '', 'abc' 都變成 0)
    numeric_cols = ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. 文字強制轉型 (防呆：把 NaN 變成空字串)
    text_cols = ['編號', '分類', '名稱', '形狀', '五行', '進貨廠商', '進貨日期']
    for col in text_cols:
        df[col] = df[col].astype(str).replace('nan', '').replace('None', '').apply(lambda x: x.strip())

    return df

def generate_new_id(category, df):
    prefix_map = {'天然石': 'ST', '配件': 'AC', '耗材': 'OT'}
    prefix = prefix_map.get(category, "OT")
    
    if df.empty: return f"{prefix}0001"
    
    # 找出所有同類型的編號
    df_ids = df['編號'].astype(str)
    # 篩選出以該前綴開頭的
    mask = df_ids.str.startswith(prefix, na=False)
    # 取出數字部分
    nums = df_ids[mask].str.replace(prefix, '', regex=False)
    # 轉成數字並找最大值
    numeric_part = pd.to_numeric(nums, errors='coerce').dropna()
    
    if numeric_part.empty:
        next_num = 1
    else:
        next_num = int(numeric_part.max()) + 1
    
    return f"{prefix}{next_num:04d}"

def make_inventory_label(row):
    try:
        w = float(row['寬度mm'])
        l = float(row['長度mm'])
        size_str = f"{w}mm" if (l == 0 or l == w) else f"{w}x{l}mm"
    except:
        size_str = ""
        
    return f"【{row['五行']}】 {row['編號']} | {row['名稱']} | {row['形狀']} ({size_str}) | {row['進貨廠商']} | 存:{row['庫存(顆)']}"

def make_design_label(row):
    try:
        w = float(row['寬度mm'])
        l = float(row['長度mm'])
        size_str = f"{w}mm" if (l == 0 or l == w) else f"{w}x{l}mm"
    except:
        size_str = ""
        
    return f"【{row['五行']}】{row['名稱']} | {row['形狀']} ({size_str}) | {row['進貨廠商']} | ${float(row['單顆成本']):.2f}/顆 | 存:{row['庫存(顆)']}"

def get_dynamic_options(col_name, defaults):
    options = set(defaults)
    if not st.session_state['inventory'].empty:
        if col_name in st.session_state['inventory'].columns:
            existing = st.session_state['inventory'][col_name].astype(str).unique().tolist()
            # 過濾掉空白
            valid_existing = [x for x in existing if x.strip() != '' and x != 'nan']
            options.update(valid_existing)
    return ["➕ 手動輸入/新增"] + sorted(list(options))

# ==========================================
# 3. 初始化 Session State
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df = pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig')
            st.session_state['inventory'] = clean_data(df)
        except:
            st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else:
        st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'design_history' not in st.session_state:
    if os.path.exists(DESIGN_HISTORY_FILE):
        try:
            df = pd.read_csv(DESIGN_HISTORY_FILE, encoding='utf-8-sig')
            st.session_state['design_history'] = df
        except:
            st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)
    else:
        st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 4. UI 介面
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    
    # 資料備份下載
    if not st.session_state['inventory'].empty:
        csv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載庫存總表 (CSV)", csv, f'inventory_{date.today()}.csv', "text/csv")
        
    if not st.session_state['design_history'].empty:
        csv_sales = st.session_state['design_history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載訂單售出紀錄 (CSV)", csv_sales, f'sales_{date.today()}.csv', "text/csv")
        
    st.divider()
    
    # ---------------------------------------------------------
    # ★★★ 核心修復：救援模式上傳區 ★★★
    # ---------------------------------------------------------
    st.markdown("### 📤 資料還原")
    uploaded_file = st.file_uploader("上傳庫存備份 (CSV)", type=['csv'])
    
    # 救援開關
    force_mode = st.checkbox("⚠️ 啟動強制對齊模式 (若上傳後空白請勾選此項)", value=False)
    
    if uploaded_file is not None:
        try:
            # 嘗試讀取
            try:
                df_upload = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            except:
                uploaded_file.seek(0)
                df_upload = pd.read_csv(uploaded_file, encoding='big5')
            
            # 顯示預覽，讓使用者安心
            with st.expander("預覽讀取到的原始資料 (前3筆)", expanded=True):
                st.dataframe(df_upload.head(3))
            
            if st.button("確認覆蓋目前庫存"):
                if force_mode:
                    # 強制模式：忽略標題，直接把欄位改名
                    # 確保欄位數量一致 (取前13欄)
                    if len(df_upload.columns) >= len(COLUMNS):
                        df_upload = df_upload.iloc[:, :len(COLUMNS)]
                        df_upload.columns = COLUMNS
                        st.session_state['inventory'] = clean_data(df_upload)
                        save_inventory()
                        st.success("✅ 已強制對齊並還原資料！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"欄位數量不足！檔案有 {len(df_upload.columns)} 欄，系統需要 {len(COLUMNS)} 欄。")
                else:
                    # 標準模式：嘗試依標題對應
                    # 先做標題標準化 (去除空白)
                    df_upload.columns = df_upload.columns.astype(str).str.strip()
                    
                    # 執行標準清洗
                    st.session_state['inventory'] = clean_data(df_upload)
                    save_inventory()
                    st.success("✅ 資料還原成功！")
                    time.sleep(1)
                    st.rerun()
                    
        except Exception as e:
            st.error(f"檔案讀取發生錯誤: {e}")

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "🛠️ 修改與盤點"])
    
    # Tab 1: 補貨
    with tab1:
        inv_df = st.session_state['inventory']
        if not inv_df.empty:
            inv_df['label'] = inv_df.apply(make_inventory_label, axis=1)
            target_label = st.selectbox("選擇商品", inv_df['label'].tolist())
            
            # 安全獲取資料
            target_data = inv_df[inv_df['label'] == target_label]
            
            if not target_data.empty:
                row = target_data.iloc[0]
                idx = target_data.index[0]
                
                with st.form("restock_form"):
                    st.info(f"目前庫存: {row['庫存(顆)']} 顆 | 成本: ${row['單顆成本']:.2f}")
                    
                    c1, c2 = st.columns(2)
                    add_qty = c1.number_input("進貨數量", min_value=1, value=1)
                    add_cost = c2.number_input("進貨總價", min_value=0.0, value=0.0, step=10.0)
                    batch_no = st.text_input("進貨單號 (選填)", placeholder="Auto")
                    
                    if st.form_submit_button("📦 確認補貨"):
                        old_qty = float(row['庫存(顆)'])
                        old_cost = float(row['單顆成本'])
                        
                        new_qty = old_qty + add_qty
                        # 計算平均成本
                        new_avg_cost = ((old_qty * old_cost) + add_cost) / new_qty if new_qty > 0 else 0
                        
                        # 更新 Session
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = new_qty
                        st.session_state['inventory'].at[idx, '單顆成本'] = new_avg_cost
                        st.session_state['inventory'].at[idx, '進貨日期'] = date.today()
                        
                        # 紀錄
                        log = {
                            '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                            '單號': batch_no if batch_no else f"AUTO-{int(time.time())}",
                            '動作': '補貨',
                            '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'],
                            '規格': f"{row['寬度mm']}mm", '廠商': row['進貨廠商'],
                            '進貨數量': add_qty, '進貨總價': add_cost, '單價': (add_cost/add_qty if add_qty>0 else 0)
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                        save_inventory()
                        st.success("補貨完成！")
                        time.sleep(1)
                        st.rerun()
            else:
                st.warning("找不到此商品資料")
        else:
            st.info("目前沒有庫存資料，請先建立新商品或上傳備份。")

    # Tab 2: 建立新商品
    with tab2:
        with st.form("create_new"):
            st.markdown("##### 1. 基本資料")
            c1, c2 = st.columns(2)
            cat = c1.selectbox("分類", ["天然石", "配件", "耗材"])
            
            # 動態名稱選單
            exist_names = []
            if not st.session_state['inventory'].empty:
                exist_names = sorted(st.session_state['inventory'][st.session_state['inventory']['分類']==cat]['名稱'].unique().tolist())
            
            name_mode = c2.selectbox("名稱選擇", ["➕ 手動輸入"] + exist_names)
            name = st.text_input("輸入名稱") if name_mode == "➕ 手動輸入" else name_mode
            
            st.markdown("##### 2. 規格")
            c3, c4 = st.columns(2)
            width = c3.number_input("寬度(mm)", min_value=0.0, step=0.5)
            length = c4.number_input("長度(mm)", min_value=0.0, step=0.5)
            
            st.markdown("##### 3. 詳細屬性")
            c5, c6, c7 = st.columns(3)
            shape = c5.text_input("形狀 (如:圓珠, 切角)")
            element = c6.selectbox("五行", DEFAULT_ELEMENTS)
            supplier = c7.text_input("廠商名稱")
            
            st.markdown("##### 4. 首次進貨")
            c8, c9 = st.columns(2)
            first_qty = c8.number_input("數量", 1)
            first_price = c9.number_input("總價", 0.0)
            
            if st.form_submit_button("➕ 新增商品"):
                if not name:
                    st.error("名稱不能為空")
                else:
                    new_id = generate_new_id(cat, st.session_state['inventory'])
                    unit_cost = first_price / first_qty if first_qty > 0 else 0
                    
                    new_item = {
                        '編號': new_id, '分類': cat, '名稱': name,
                        '寬度mm': width, '長度mm': length, '形狀': shape, '五行': element,
                        '進貨總價': first_price, '進貨數量(顆)': first_qty,
                        '進貨日期': date.today(), '進貨廠商': supplier,
                        '庫存(顆)': first_qty, '單顆成本': unit_cost
                    }
                    
                    st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_item])], ignore_index=True)
                    save_inventory()
                    st.success(f"已新增 {name} ({new_id})")
                    time.sleep(1)
                    st.rerun()

    # Tab 3: 修改
    with tab3:
        if not st.session_state['inventory'].empty:
            edit_df = st.session_state['inventory'].copy()
            edit_df['label'] = edit_df.apply(make_inventory_label, axis=1)
            
            target = st.selectbox("搜尋要修改的商品", edit_df['label'])
            
            # 找出對應的原始 index
            target_code = target.split('|')[0].split('】')[1].strip() # 抓出編號
            
            # 在原始資料中找這個編號
            mask = st.session_state['inventory']['編號'] == target_code
            if mask.any():
                real_idx = st.session_state['inventory'][mask].index[0]
                row = st.session_state['inventory'].iloc[real_idx]
                
                with st.form("edit_form"):
                    c1, c2, c3 = st.columns(3)
                    e_name = c1.text_input("名稱", row['名稱'])
                    e_w = c2.number_input("寬度", value=float(row['寬度mm']))
                    e_l = c3.number_input("長度", value=float(row['長度mm']))
                    
                    c4, c5, c6 = st.columns(3)
                    e_shape = c4.text_input("形狀", row['形狀'])
                    # 處理五行選單預設值
                    try:
                        e_elem_idx = DEFAULT_ELEMENTS.index(row['五行'])
                    except:
                        e_elem_idx = 0
                    e_elem = c5.selectbox("五行", DEFAULT_ELEMENTS, index=e_elem_idx)
                    e_sup = c6.text_input("廠商", row['進貨廠商'])
                    
                    st.divider()
                    c7, c8 = st.columns(2)
                    e_qty = c7.number_input("庫存數量", value=int(float(row['庫存(顆)'])))
                    e_cost = c8.number_input("單顆成本", value=float(row['單顆成本']))
                    
                    if st.form_submit_button("💾 儲存修改"):
                        # 更新資料
                        st.session_state['inventory'].at[real_idx, '名稱'] = e_name
                        st.session_state['inventory'].at[real_idx, '寬度mm'] = e_w
                        st.session_state['inventory'].at[real_idx, '長度mm'] = e_l
                        st.session_state['inventory'].at[real_idx, '形狀'] = e_shape
                        st.session_state['inventory'].at[real_idx, '五行'] = e_elem
                        st.session_state['inventory'].at[real_idx, '進貨廠商'] = e_sup
                        st.session_state['inventory'].at[real_idx, '庫存(顆)'] = e_qty
                        st.session_state['inventory'].at[real_idx, '單顆成本'] = e_cost
                        
                        save_inventory()
                        st.success("修改成功！")
                        time.sleep(1)
                        st.rerun()
                        
                if st.button("🗑️ 刪除此商品"):
                    st.session_state['inventory'] = st.session_state['inventory'].drop(real_idx).reset_index(drop=True)
                    save_inventory()
                    st.warning("商品已刪除")
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("找不到原始資料，請重新整理")
        else:
            st.info("無資料")

    st.divider()
    st.subheader("📋 庫存總表")
    
    # 搜尋功能
    df_show = st.session_state['inventory'].copy()
    if not df_show.empty:
        search_txt = st.text_input("🔍 搜尋 (輸入名稱、編號或廠商)")
        if search_txt:
            mask = df_show.astype(str).apply(lambda x: x.str.contains(search_txt, case=False)).any(axis=1)
            df_show = df_show[mask]
            
        st.dataframe(df_show, use_container_width=True, height=500)

# ------------------------------------------
# 頁面 B: 紀錄
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 紀錄中心")
    tab1, tab2 = st.tabs(["📦 流水帳", "💎 訂單紀錄"])
    
    with tab1:
        st.dataframe(st.session_state['history'], use_container_width=True)
    with tab2:
        st.dataframe(st.session_state['design_history'], use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 設計手鍊")
    
    inv = st.session_state['inventory']
    if not inv.empty:
        # 篩選區
        col_filter = st.columns(3)
        ele_filter = col_filter[0].multiselect("篩選五行", inv['五行'].unique())
        
        df_filt = inv.copy()
        if ele_filter:
            df_filt = df_filt[df_filt['五行'].isin(ele_filter)]
            
        # 選商品
        df_filt['label'] = df_filt.apply(make_design_label, axis=1)
        select_item = st.selectbox("選擇珠子", df_filt['label'])
        
        c1, c2 = st.columns(2)
        qty = c1.number_input("使用數量", 1)
        
        if c2.button("⬇️ 加入清單"):
            target_row = df_filt[df_filt['label'] == select_item].iloc[0]
            st.session_state['current_design'].append({
                '編號': target_row['編號'],
                '名稱': target_row['名稱'],
                '規格': f"{target_row['寬度mm']}mm",
                '單價': float(target_row['單顆成本']),
                '數量': qty,
                '小計': float(target_row['單顆成本']) * qty
            })
            st.success("已加入")
            
        st.divider()
        
        # 顯示清單
        if st.session_state['current_design']:
            design_df = pd.DataFrame(st.session_state['current_design'])
            st.dataframe(design_df, use_container_width=True)
            
            total_mat = design_df['小計'].sum()
            st.write(f"**材料總成本: ${total_mat:.2f}**")
            
            c3, c4 = st.columns(2)
            labor = c3.number_input("工資", 0)
            misc = c4.number_input("雜支", 0)
            
            final_cost = total_mat + labor + misc
            st.info(f"💰 總成本: ${final_cost:.2f} | 建議售價(x3): ${final_cost*3:.0f}")
            
            if st.button("✅ 確認售出 (扣除庫存)"):
                # 執行扣庫存
                order_id = f"S-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                details = []
                
                for item in st.session_state['current_design']:
                    mask = st.session_state['inventory']['編號'] == item['編號']
                    if mask.any():
                        real_idx = st.session_state['inventory'][mask].index[0]
                        current = float(st.session_state['inventory'].at[real_idx, '庫存(顆)'])
                        st.session_state['inventory'].at[real_idx, '庫存(顆)'] = current - item['數量']
                        details.append(f"{item['名稱']}x{item['數量']}")
                
                # 寫入歷史
                design_log = {
                    '單號': order_id, '日期': date.today(),
                    '總顆數': design_df['數量'].sum(),
                    '材料成本': total_mat, '工資': labor, '雜支': misc,
                    '總成本': final_cost, '售價(x3)': final_cost*3, '售價(x5)': final_cost*5,
                    '明細內容': " | ".join(details)
                }
                st.session_state['design_history'] = pd.concat([st.session_state['design_history'], pd.DataFrame([design_log])], ignore_index=True)
                
                save_inventory()
                save_design_history()
                st.session_state['current_design'] = []
                st.success(f"售出成功！單號：{order_id}")
                time.sleep(2)
                st.rerun()
                
            if st.button("🗑️ 清空清單"):
                st.session_state['current_design'] = []
                st.rerun()
    else:
        st.info("尚無庫存資料")
