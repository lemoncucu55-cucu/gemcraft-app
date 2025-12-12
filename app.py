import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心邏輯與設定區
# ==========================================

# 系統標準欄位順序
COLUMNS = [
    '編號', '分類', '系列', '名稱', '尺寸規格', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

# 庫存異動紀錄欄位
HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '編號', '分類', '名稱', '尺寸規格', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

# ★★★ 新增：設計/銷售紀錄欄位 ★★★
DESIGN_HISTORY_COLUMNS = [
    '單號', '日期', '總顆數', '材料成本', '工資', '雜支', 
    '總成本', '售價(x3)', '售價(x5)', '明細內容'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DESIGN_HISTORY_FILE = 'design_sales_history.csv' # 新增的檔案名稱
RULES_FILE = 'coding_rules.xlsx'

# 預設選單資料
DEFAULT_SUPPLIERS = ["廠商A", "廠商B", "自用", "蝦皮", "淘寶"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合"]

# 初始範例資料
INITIAL_DATA = {
    '編號': ['ST0001', 'ST0002', 'ST0003', 'ST0004', 'ST0005', 'ST0006'],
    '分類': ['天然石', '天然石', '天然石', '天然石', '天然石', '天然石'],
    '名稱': ['冰翠玉', '東菱玉', '紫水晶', '東菱玉', '東菱玉', '綠碧璽'],
    '寬度mm': [3.0, 5.0, 8.0, 6.0, 8.0, 8.0],
    '長度mm': [3.0, 5.0, 8.0, 6.0, 8.0, 8.0],
    '形狀': ['切角', '切角', '圓珠', '切角', '切角', '圓珠'],
    '五行': ['木', '木', '火', '木', '木', '木'],
    '進貨總價': [100, 180, 450, 132, 100, 550],
    '進貨數量(顆)': [145, 45, 50, 120, 45, 20],
    '進貨日期': ['2024-11-07', '2024-08-14', '2024-08-09', '2024-12-30', '2024-12-30', '2025-12-09'],
    '進貨廠商': ['TB-東吳天然石坊', 'Rich', '永安', 'TB-Super Search', 'TB-Super Search', '永安'],
    '庫存(顆)': [145, 45, 110, 120, 45, 20],
    '單顆成本': [0.689655, 4.0, 9.0, 1.1, 2.222222, 27.5],
}

# ==========================================
# 2. 核心邏輯函式
# ==========================================

def save_inventory():
    """儲存庫存到 CSV"""
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"庫存儲存失敗: {e}")

def save_design_history():
    """儲存設計紀錄到 CSV"""
    try:
        if 'design_history' in st.session_state:
            st.session_state['design_history'].to_csv(DESIGN_HISTORY_FILE, index=False, encoding='utf-8-sig')
    except Exception as e:
        st.error(f"銷售紀錄儲存失敗: {e}")

def load_coding_rules(uploaded_file=None):
    rules = {'cat': {}, 'series': {}, 'name': {}, 'size': {}}
    dfs = {}
    try:
        source = uploaded_file if uploaded_file else (RULES_FILE if os.path.exists(RULES_FILE) else None)
        if source:
            df = pd.read_excel(source, header=0)
            df.columns = [str(c).strip() for c in df.columns]
            if df.shape[1] >= 2:
                cat_df = df.iloc[:, [0, 1]].dropna().astype(str)
                rules['cat'] = dict(zip(cat_df.iloc[:, 0], cat_df.iloc[:, 1]))
                dfs['cat'] = cat_df
            if df.shape[1] >= 4:
                series_df = df.iloc[:, [2, 3]].dropna().astype(str)
                rules['series'] = dict(zip(series_df.iloc[:, 0], series_df.iloc[:, 1]))
                dfs['series'] = series_df
            if df.shape[1] >= 6:
                name_df = df.iloc[:, [4, 5]].dropna().astype(str)
                rules['name'] = dict(zip(name_df.iloc[:, 0], name_df.iloc[:, 1]))
                dfs['name'] = name_df
            if df.shape[1] >= 8:
                size_df = df.iloc[:, [6, 7]].dropna().astype(str)
                rules['size'] = dict(zip(size_df.iloc[:, 0], size_df.iloc[:, 1]))
                dfs['size'] = size_df
            return rules, dfs
    except Exception:
        pass
    return rules, dfs

def get_rule_options(rule_dict):
    options = [f"{k} ({v})" for k, v in rule_dict.items()]
    return ["➕ 手動輸入/新增"] + sorted(options)

def parse_selection(selection, rule_dict):
    if selection == "➕ 手動輸入/新增" or not selection: return None, None
    try:
        name = selection.rsplit(' (', 1)[0]
        code = selection.rsplit(' (', 1)[1][:-1]
        return name, code
    except: return selection, ""

def normalize_columns(df):
    rename_map = {
        '尺寸': '尺寸規格', '規格': '尺寸規格', 'Size': '尺寸規格',
        '寬度': '寬度mm', 'Width': '寬度mm', '名稱': '名稱', 'Name': '名稱',
        '分類': '分類', 'Category': '分類', '編號': '編號', 'ID': '編號',
        '單顆成本': '單顆成本', '庫存(顆)': '庫存(顆)'
    }
    df = df.rename(columns=rename_map)
    for col in COLUMNS:
        if col not in df.columns:
            if 'mm' in col or '價' in col or '數量' in col or '成本' in col: df[col] = 0
            else: df[col] = ""
    return df[COLUMNS]

def make_inventory_label(row):
    return f"{str(row['編號'])} | {str(row['名稱'])} {str(row['尺寸規格'])} | 存:{row['庫存(顆)']}"

def make_design_label(row):
    return f"【{row['五行']}】{row['名稱']} ({row['尺寸規格']}) | ${row['單顆成本']:.1f}/顆 | 存:{row['庫存(顆)']}"

def get_dynamic_options(column_name, default_list):
    options = set(default_list)
    if not st.session_state['inventory'].empty:
        existing = st.session_state['inventory'][column_name].dropna().unique().tolist()
        options.update([str(x) for x in existing if str(x).strip() != ""])
    return ["➕ 手動輸入新資料"] + sorted(list(options))

# ==========================================
# 3. 初始化 Session State
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            df = pd.read_csv(DEFAULT_CSV_FILE)
            st.session_state['inventory'] = normalize_columns(df)
        except: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
else:
    if '單號' not in st.session_state['history'].columns:
        st.session_state['history'].insert(1, '單號', '')

# ★★★ 初始化設計/銷售紀錄 ★★★
if 'design_history' not in st.session_state:
    if os.path.exists(DESIGN_HISTORY_FILE):
        try:
            st.session_state['design_history'] = pd.read_csv(DESIGN_HISTORY_FILE)
        except: st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)
    else:
        st.session_state['design_history'] = pd.DataFrame(columns=DESIGN_HISTORY_COLUMNS)

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

if 'coding_rules' not in st.session_state:
    st.session_state['coding_rules'], st.session_state['rule_dfs'] = load_coding_rules()

# ==========================================
# 4. UI 介面
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "⚙️ 編碼規則設定", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    
    # 下載區
    st.caption("💾 資料下載")
    if not st.session_state['inventory'].empty:
        csv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 庫存總表 (Inventory)", csv, f'inventory_{date.today()}.csv', "text/csv")
        
    if not st.session_state['design_history'].empty:
        d_csv = st.session_state['design_history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 銷售紀錄 (Sales)", d_csv, f'sales_history_{date.today()}.csv', "text/csv")

# ------------------------------------------
# 頁面: 編碼規則設定
# ------------------------------------------
if page == "⚙️ 編碼規則設定":
    st.subheader("⚙️ 商品編碼規則管理")
    uploaded_rules = st.file_uploader("上傳規則檔 (Excel)", type=['xlsx', 'xls'])
    if uploaded_rules:
        rules, dfs = load_coding_rules(uploaded_rules)
        if rules['cat']:
            st.session_state['coding_rules'] = rules
            st.session_state['rule_dfs'] = dfs
            try:
                with open(RULES_FILE, "wb") as f: f.write(uploaded_rules.getbuffer())
                st.success("✅ 規則檔已更新！")
            except: st.success("✅ 規則已暫時載入")
        else: st.error("❌ 讀取失敗")

    st.divider()
    st.markdown("##### 🔍 目前生效的編碼規則")
    if st.session_state.get('rule_dfs'):
        dfs = st.session_state['rule_dfs']
        c1, c2, c3, c4 = st.columns(4)
        with c1: 
            st.markdown("**1. 類別**")
            if 'cat' in dfs: st.dataframe(dfs['cat'], hide_index=True)
        with c2: 
            st.markdown("**2. 系列**")
            if 'series' in dfs: st.dataframe(dfs['series'], hide_index=True)
        with c3: 
            st.markdown("**3. 名稱**")
            if 'name' in dfs: st.dataframe(dfs['name'], hide_index=True)
        with c4: 
            st.markdown("**4. 尺寸**")
            if 'size' in dfs: st.dataframe(dfs['size'], hide_index=True)
    else: st.warning("尚未設定規則，請上傳 Excel 檔。")

# ------------------------------------------
# 頁面: 庫存管理
# ------------------------------------------
elif page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "🛠️ 修改與刪除"])
    
    # === Tab 1: 補貨 ===
    with tab1:
        st.caption("已有貨號商品補貨")
        inv_df = st.session_state['inventory']
        if not inv_df.empty:
            inv_df['label'] = inv_df.apply(lambda x: f"{str(x['編號'])} | {str(x['名稱'])} {str(x['尺寸規格'])}", axis=1)
            target_label = st.selectbox("選擇商品", inv_df['label'].tolist())
            target_row = inv_df[inv_df['label'] == target_label].iloc[0]
            target_idx = inv_df[inv_df['label'] == target_label].index[0]
            
            with st.form("restock"):
                st.write(f"目前庫存: **{target_row['庫存(顆)']}**")
                batch_no = st.text_input("進貨單號 (選填)", placeholder="例如：IN-20251212")
                c1, c2 = st.columns(2)
                qty = c1.number_input("進貨數量", 1)
                cost = c2.number_input("進貨總價", 0)
                
                if st.form_submit_button("📦 確認補貨"):
                    new_qty = target_row['庫存(顆)'] + qty
                    old_val = target_row['庫存(顆)'] * target_row['單顆成本']
                    new_avg = (old_val + cost) / new_qty if new_qty > 0 else 0
                    
                    st.session_state['inventory'].at[target_idx, '庫存(顆)'] = new_qty
                    st.session_state['inventory'].at[target_idx, '單顆成本'] = new_avg
                    st.session_state['inventory'].at[target_idx, '進貨日期'] = date.today()
                    
                    log = {
                        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '單號': batch_no if batch_no else f"AUTO-{int(time.time())}",
                        '動作': '補貨',
                        '編號': target_row['編號'], '分類': target_row['分類'], '名稱': target_row['名稱'],
                        '尺寸規格': target_row['尺寸規格'], '廠商': target_row['進貨廠商'],
                        '進貨數量': qty, '進貨總價': cost, '單價': cost/qty if qty>0 else 0
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    save_inventory()
                    st.success("補貨成功！")
                    st.rerun()
        else: st.info("無庫存")

    # === Tab 2: 建立新商品 ===
    with tab2:
        st.markdown("##### 🏗️ 產生長貨號")
        rules = st.session_state.get('coding_rules', {'cat':{}, 'series':{}, 'name':{}, 'size':{}})
        
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)
        
        with col1:
            cat_opts = get_rule_options(rules['cat'])
            sel_cat = st.selectbox("1. 類別", cat_opts)
            name_cat, code_cat = parse_selection(sel_cat, rules['cat'])
            if not code_cat: 
                c_m1, c_m2 = st.columns([2,1])
                name_cat = c_m1.text_input("輸入名稱", key="m_cat_n")
                code_cat = c_m2.text_input("代號", key="m_cat_c").upper()

        with col2:
            ser_opts = get_rule_options(rules['series'])
            sel_ser = st.selectbox("2. 系列", ser_opts)
            name_ser, code_ser = parse_selection(sel_ser, rules['series'])
            if not code_ser:
                c_m3, c_m4 = st.columns([2,1])
                name_ser = c_m3.text_input("輸入名稱", key="m_ser_n")
                code_ser = c_m4.text_input("代號", key="m_ser_c").upper()

        with col3:
            nm_opts = get_rule_options(rules['name'])
            sel_nm = st.selectbox("3. 名稱", nm_opts)
            name_nm, code_nm = parse_selection(sel_nm, rules['name'])
            if not code_nm:
                c_m5, c_m6 = st.columns([2,1])
                name_nm = c_m5.text_input("輸入名稱", key="m_nm_n")
                code_nm = c_m6.text_input("代號", key="m_nm_c").upper()

        with col4:
            sz_opts = get_rule_options(rules['size'])
            sel_sz = st.selectbox("4. 尺寸", sz_opts)
            name_sz, code_sz = parse_selection(sel_sz, rules['size'])
            if not code_sz:
                c_m7, c_m8 = st.columns([2,1])
                name_sz = c_m7.text_input("輸入規格", key="m_sz_n")
                code_sz = c_m8.text_input("代號", key="m_sz_c").upper()

        full_id = f"{code_cat}{code_ser}{code_nm}{code_sz}" if (code_cat and code_ser and code_nm and code_sz) else ""
        if full_id: st.success(f"預覽貨號：**{full_id}** ({name_cat} {name_ser} {name_nm} {name_sz})")
        
        st.divider()
        with st.form("new_item"):
            f1, f2, f3 = st.columns(3)
            with f1: batch_no = st.text_input("進貨單號", placeholder="Auto")
            with f2: qty = st.number_input("數量", 1)
            with f3: cost = st.number_input("總價", 0)
            
            f4, f5, f6 = st.columns(3)
            with f4: supplier = st.selectbox("廠商", DEFAULT_SUPPLIERS + ["其他"])
            with f5: shape = st.selectbox("形狀", DEFAULT_SHAPES)
            with f6: element = st.selectbox("五行", DEFAULT_ELEMENTS)
            
            width = st.number_input("寬度mm", 0.0)
            length = st.number_input("長度mm", 0.0)

            if st.form_submit_button("🚀 建立商品"):
                if not full_id: st.error("貨號不完整")
                elif full_id in st.session_state['inventory']['編號'].values:
                    st.error("貨號已存在")
                else:
                    unit = cost/qty if qty > 0 else 0
                    new_data = {
                        '編號': full_id, '分類': name_cat, '系列': name_ser,
                        '名稱': name_nm, '尺寸規格': name_sz,
                        '寬度mm': width, '長度mm': length, '形狀': shape, '五行': element,
                        '進貨總價': cost, '進貨數量(顆)': qty, '進貨日期': date.today(), 
                        '進貨廠商': supplier, '庫存(顆)': qty, '單顆成本': unit
                    }
                    st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_data])], ignore_index=True)
                    log = {
                        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '單號': batch_no if batch_no else "NEW", '動作': '新建立',
                        '編號': full_id, '分類': name_cat, '名稱': name_nm, '尺寸規格': name_sz,
                        '廠商': supplier, '進貨數量': qty, '進貨總價': cost, '單價': unit
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    save_inventory()
                    st.success("建立成功！")
                    st.rerun()

    # === Tab 3: 修改 ===
    with tab3:
        inv = st.session_state['inventory']
        if not inv.empty:
            edit_id = st.selectbox("選擇修改商品", inv['編號'].tolist())
            idx = inv[inv['編號'] == edit_id].index[0]
            row = inv.iloc[idx]
            
            with st.form("edit"):
                c1, c2 = st.columns(2)
                ns = c1.number_input("庫存", value=int(row['庫存(顆)']))
                nc = c2.number_input("成本", value=float(row['單顆成本']))
                if st.form_submit_button("更新"):
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = ns
                    st.session_state['inventory'].at[idx, '單顆成本'] = nc
                    save_inventory()
                    st.success("已更新")
                    st.rerun()
            if st.button("🗑️ 刪除商品"):
                st.session_state['inventory'] = inv.drop(idx).reset_index(drop=True)
                save_inventory()
                st.rerun()

    st.divider()
    st.subheader("📋 庫存總表")
    st.dataframe(st.session_state['inventory'], use_container_width=True)

# ------------------------------------------
# 頁面: 紀錄查詢 (新增分頁)
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 歷史紀錄中心")
    
    tab_log, tab_sales = st.tabs(["📦 庫存異動流水帳", "💎 訂單銷售紀錄"])
    
    with tab_log:
        st.dataframe(st.session_state['history'], use_container_width=True)
        
    with tab_sales:
        st.caption("這裡記錄了所有「確認售出」的設計單細節")
        if not st.session_state['design_history'].empty:
            # 讓使用者可以展開看明細
            st.dataframe(st.session_state['design_history'], use_container_width=True)
        else:
            st.info("尚無銷售紀錄")

# ------------------------------------------
# 頁面: 設計與成本
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 成本試算與報價")
    
    inv = st.session_state['inventory']
    if not inv.empty:
        inv['disp'] = inv.apply(lambda x: f"【{x['分類']}】{x['名稱']} ({x['尺寸規格']}) | ${x['單顆成本']:.1f}", axis=1)
        
        c1, c2, c3 = st.columns([3, 1, 1])
        item_sel = c1.selectbox("選擇材料", inv['disp'].tolist())
        qty_sel = c2.number_input("數量", 1)
        
        if c3.button("⬇️ 加入", use_container_width=True):
            row = inv[inv['disp'] == item_sel].iloc[0]
            st.session_state['current_design'].append({
                '編號': row['編號'], '名稱': row['名稱'], '規格': row['尺寸規格'],
                '單價': row['單顆成本'], '數量': qty_sel, 
                '小計': row['單顆成本'] * qty_sel
            })
            
        st.divider()
        
        if st.session_state['current_design']:
            df_design = pd.DataFrame(st.session_state['current_design'])
            st.table(df_design)
            
            if st.button("🗑️ 清除最後一項"):
                st.session_state['current_design'].pop()
                st.rerun()
            
            mat_cost = df_design['小計'].sum()
            st.markdown("#### 💰 成本結構")
            c_labor, c_misc = st.columns(2)
            labor = c_labor.number_input("工資 ($)", 0, step=10)
            misc = c_misc.number_input("雜支/運費 ($)", 0, step=5)
            
            total_base = mat_cost + labor + misc
            price_x3 = (mat_cost * 3) + labor + misc
            price_x5 = (mat_cost * 5) + labor + misc
            
            st.info(f"基礎材料費: ${mat_cost:.1f}")
            m1, m2, m3 = st.columns(3)
            m1.metric("總成本", f"${total_base:.0f}")
            m2.metric("建議售價 (x3)", f"${price_x3:.0f}")
            m3.metric("建議售價 (x5)", f"${price_x5:.0f}")
            
            st.divider()
            sale_id = st.text_input("訂單編號", placeholder="例如: 蝦皮241212...")
            
            if st.button("✅ 確認售出 (扣除庫存並記錄)", type="primary"):
                if not sale_id: sale_id = f"S-{int(time.time())}"
                
                # 1. 產生明細字串
                detail_str = []
                total_qty = 0
                for item in st.session_state['current_design']:
                    # 扣庫存
                    idx = inv[inv['編號'] == item['編號']].index[0]
                    inv.at[idx, '庫存(顆)'] -= item['數量']
                    
                    # 紀錄流水帳
                    log = {
                        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '單號': sale_id, '動作': '售出',
                        '編號': item['編號'], '名稱': item['名稱'], 
                        '尺寸規格': item['規格'], '進貨數量': -item['數量'],
                        '進貨總價': 0, '單價': item['單價']
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    
                    # 收集明細
                    detail_str.append(f"{item['名稱']}({item['編號']})x{item['數量']}")
                    total_qty += item['數量']
                
                # 2. 寫入設計銷售紀錄 (Design History)
                design_log = {
                    '單號': sale_id,
                    '日期': date.today(),
                    '總顆數': total_qty,
                    '材料成本': mat_cost,
                    '工資': labor,
                    '雜支': misc,
                    '總成本': total_base,
                    '售價(x3)': price_x3,
                    '售價(x5)': price_x5,
                    '明細內容': " | ".join(detail_str)
                }
                st.session_state['design_history'] = pd.concat(
                    [st.session_state['design_history'], pd.DataFrame([design_log])], 
                    ignore_index=True
                )
                
                save_inventory()
                save_design_history() # 儲存新紀錄檔
                st.session_state['current_design'] = []
                st.success(f"已完成售出扣帳！單號：{sale_id}")
                time.sleep(1)
                st.rerun()
