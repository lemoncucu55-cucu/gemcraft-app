import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
import time

# ==========================================
# 1. 核心設定
# ==========================================

# 核心欄位定義 (14欄)
COLUMNS = [
    '編號', '倉庫', '分類', '名稱', 
    '寬度mm', '長度mm', '形狀', '五行', 
    '進貨總價', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

# 財務與敏感資訊過濾清單
SENSITIVE_COLUMNS = [
    '進貨總價', '單顆成本', '材料成本', '總成本', '單價', '小計', 
    '售價(x3)', '售價(x5)', '進貨數量(顆)', '進貨數量', '進貨日期', '進貨廠商', '廠商'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', 
    '廠商', '進貨數量', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
DEFAULT_WAREHOUSES = ["Imeng", "千畇"]
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]

# ==========================================
# 2. 核心函式
# ==========================================

def save_inventory():
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def robust_import_inventory(df, force_position=True):
    """強力匯入與格式校正，防止欄位錯位"""
    # 1. 自動移除檔案中多餘的 label 欄位 (這是造成錯位的主因)
    if 'label' in df.columns:
        df = df.drop(columns=['label'])
    
    # 2. 如果是強制位置對齊 (通常用於備份還原)
    if force_position:
        if df.shape[1] > len(COLUMNS):
            df = df.iloc[:, :len(COLUMNS)]
        elif df.shape[1] < len(COLUMNS):
            for i in range(len(COLUMNS) - df.shape[1]):
                df[f'temp_{i}'] = ""
        df.columns = COLUMNS
    else:
        # 非強制對齊則嘗試名稱匹配
        df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
        if '倉庫' not in df.columns: df['倉庫'] = "Imeng"
        for col in COLUMNS:
            if col not in df.columns: df[col] = ""

    df = df[COLUMNS].copy()
    
    # 3. 數據消毒
    df['倉庫'] = df['倉庫'].replace(['', 'nan', 'None'], 'Imeng').fillna('Imeng')
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    for col in ['編號', '倉庫', '分類', '名稱', '形狀', '五行', '進貨廠商']:
        df[col] = df[col].astype(str).replace('nan', '').replace('None', '').apply(lambda x: x.strip())
    
    return df

def format_size(row):
    try: return f"{float(row.get('寬度mm',0))}mm"
    except: return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    # 非主管不顯示廠商
    sup_info = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    label = f"[{row.get('倉庫','Imeng')}] {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup_info} | 存:{int(float(row.get('庫存(顆)',0)))}"
    if st.session_state.get('admin_mode', False):
        label += f" | 成本:${row.get('單顆成本',0):.2f}"
    return label

def generate_new_id(category, df):
    prefix = {'天然石': 'ST', '配件': 'AC', '耗材': 'OT'}.get(category, "OT")
    if df.empty: return f"{prefix}0001"
    df_ids = df['編號'].astype(str)
    mask = df_ids.str.startswith(prefix, na=False)
    nums = df_ids[mask].str[2:].str.extract(r'(\d+)', expand=False).dropna().astype(int)
    next_num = 1 if nums.empty else nums.max() + 1
    return f"{prefix}{next_num:04d}"

# ==========================================
# 3. 初始化 Session
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            raw = pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig')
            st.session_state['inventory'] = robust_import_inventory(raw)
        except: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else:
        st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

# 確保基礎結構
if '倉庫' not in st.session_state['inventory'].columns:
    st.session_state['inventory']['倉庫'] = "Imeng"

if 'history' not in st.session_state: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
if 'current_design' not in st.session_state: st.session_state['current_design'] = []
if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False

# ==========================================
# 4. UI 介面
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    if st.session_state['admin_mode']: st.success("🔓 主管模式已開啟")
    
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 進貨紀錄查詢", "🧮 設計與成本計算"])
    st.divider()
    
    # 資料還原功能
    uploaded_inv = st.file_uploader("📤 上傳資料修復錯位", type=['csv'])
    if uploaded_inv and st.button("🚨 執行資料修復匯入"):
        try:
            raw_df = pd.read_csv(uploaded_inv, encoding='utf-8-sig')
            st.session_state['inventory'] = robust_import_inventory(raw_df, force_position=True)
            save_inventory()
            st.success("修復完成！")
            time.sleep(1); st.rerun()
        except Exception as e: st.error(f"錯誤: {e}")

    if st.button("🔴 重置系統", type="secondary"):
        st.session_state.clear(); st.rerun()

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    st.subheader("📦 庫存管理")
    tab1, tab2, tab4, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用與出庫", "🛠️ 修改與盤點"])
    
    with tab1: # 補貨
        inv_df = st.session_state['inventory'].copy()
        if not inv_df.empty:
            inv_df['label'] = inv_df.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_df['label'].tolist(), key="restock_sel")
            row_match = inv_df[inv_df['label'] == target]
            if not row_match.empty:
                row = row_match.iloc[0]
                idx = st.session_state['inventory'][st.session_state['inventory']['編號'] == row['編號']].index[0]
                with st.form("restock"):
                    st.write(f"倉庫: **{row['倉庫']}** | 目前庫存: **{int(row['庫存(顆)'])}**")
                    c1, c2 = st.columns(2)
                    qty = c1.number_input("進貨數量", 1)
                    cost = c2.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
                    if st.form_submit_button("📦 確認補貨"):
                        old_q, old_c = float(row['庫存(顆)']), float(row['單顆成本'])
                        new_q = old_q + qty
                        new_avg = ((old_q * old_c) + cost) / new_q if new_q > 0 else 0
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                        if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = new_avg
                        save_inventory(); st.success("補貨成功"); st.rerun()

    with tab2: # 新增
        with st.form("add"):
            c_wh, c1, c2 = st.columns([1,1,2])
            wh = c_wh.selectbox("存入倉庫", DEFAULT_WAREHOUSES)
            cat = c1.selectbox("分類", ["天然石", "配件", "耗材"])
            name = st.text_input("名稱")
            c3, c4 = st.columns(2)
            w, l = c3.number_input("寬度mm", 0.0), c4.number_input("長度mm", 0.0)
            st.write("---")
            c_p, c_q = st.columns(2)
            price = c_p.number_input("進貨總價", 0.0) if st.session_state['admin_mode'] else 0.0
            qty = c_q.number_input("進貨數量", 1)
            sup = st.selectbox("進貨廠商", DEFAULT_SUPPLIERS) if st.session_state['admin_mode'] else "隱藏"
            
            if st.form_submit_button("➕ 新增商品"):
                nid = generate_new_id(cat, st.session_state['inventory'])
                new_item = {'編號': nid, '倉庫': wh, '分類': cat, '名稱': name, '寬度mm': w, '長度mm': l, '形狀': '圓珠', '五行': '無', '進貨總價': price, '進貨數量(顆)': qty, '進貨日期': date.today(), '進貨廠商': sup, '庫存(顆)': qty, '單顆成本': price/qty if qty>0 else 0}
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_item])], ignore_index=True)
                save_inventory(); st.success(f"已存入 {wh}"); st.rerun()

    with tab4: # 📤 出庫功能
        inv_df_out = st.session_state['inventory'].copy()
        if not inv_df_out.empty:
            inv_df_out['label'] = inv_df_out.apply(make_inventory_label, axis=1)
            target_out = st.selectbox("選擇出庫商品", inv_df_out['label'].tolist(), key="outstock_sel")
            row_out_match = inv_df_out[inv_df_out['label'] == target_out]
            if not row_out_match.empty:
                row_o = row_out_match.iloc[0]
                idx_o = st.session_state['inventory'][st.session_state['inventory']['編號'] == row_o['編號']].index[0]
                with st.form("outstock_form"):
                    cur_s = int(row_o['庫存(顆)'])
                    st.write(f"倉庫: **{row_o['倉庫']}** | 目前庫存: **{cur_s}**")
                    qty_o = st.number_input("出庫數量", 0, cur_s, (1 if cur_s > 0 else 0))
                    note = st.text_area("備註")
                    if st.form_submit_button("📤 確認出庫"):
                        if qty_o > 0:
                            st.session_state['inventory'].at[idx_o, '庫存(顆)'] -= qty_o
                            save_inventory(); st.warning("已出庫"); time.sleep(1); st.rerun()

    with tab3: # 修改與盤點
        if not st.session_state['inventory'].empty:
            df_edit = st.session_state['inventory'].copy()
            df_edit['label'] = df_edit.apply(make_inventory_label, axis=1)
            target_e = st.selectbox("修改項目", df_edit['label'], key="edit_sel")
            row_e = df_edit[df_edit['label'] == target_e].iloc[0]
            idx_e = st.session_state['inventory'][st.session_state['inventory']['編號'] == row_e['編號']].index[0]
            with st.form("edit"):
                new_wh = st.selectbox("更改倉庫", DEFAULT_WAREHOUSES, index=(0 if row_e['倉庫'] not in DEFAULT_WAREHOUSES else DEFAULT_WAREHOUSES.index(row_e['倉庫'])))
                new_qt = st.number_input("盤點庫存", value=int(row_e['庫存(顆)']))
                if st.form_submit_button("💾 儲存修改"):
                    st.session_state['inventory'].at[idx_e, '倉庫'] = new_wh
                    st.session_state['inventory'].at[idx_e, '庫存(顆)'] = new_qt
                    save_inventory(); st.success("更新完成"); st.rerun()

    st.divider()
    st.subheader("📊 倉庫數據統計")
    if not st.session_state['inventory'].empty:
        df_stats = st.session_state['inventory'].copy()
        # 強制轉型確保統計正確
        df_stats['庫存(顆)'] = pd.to_numeric(df_stats['庫存(顆)'], errors='coerce').fillna(0)
        summary = df_stats.groupby('倉庫').agg({'編號': 'count', '庫存(顆)': 'sum'}).rename(columns={'編號': '品項數量', '庫存(顆)': '顆數總計'})
        st.table(summary.astype(int))

    st.subheader("📋 庫存總表清單")
    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True)

# ------------------------------------------
# 頁面 B & C
# ------------------------------------------
elif page == "📜 進貨紀錄查詢":
    st.subheader("📜 歷史紀錄")
    df_h = st.session_state['history'].copy()
    if not df_h.empty and not st.session_state['admin_mode']:
        df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
    st.dataframe(df_h, use_container_width=True)

elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計")
    items = st.session_state['inventory'].copy()
    if not items.empty:
        items['lbl'] = items.apply(lambda r: f"[{r['倉庫']}] {r['名稱']} | 存:{int(r['庫存(顆)'])}", axis=1)
        sel = st.selectbox("選擇材料", items['lbl'])
        qty = st.number_input("數量", 1)
        if st.button("⬇️ 加入"):
            r = items[items['lbl'] == sel].iloc[0]
            st.session_state['current_design'].append({'編號':r['編號'], '名稱':r['名稱'], '數量':qty, '單價':r['單顆成本']})
            st.rerun()
        
        if st.session_state['current_design']:
            ddf = pd.DataFrame(st.session_state['current_design'])
            st.table(ddf[['名稱', '數量']] if not st.session_state['admin_mode'] else ddf)
            if st.button("✅ 售出"):
                for x in st.session_state['current_design']:
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == x['編號'], '庫存(顆)'] -= x['數量']
                save_inventory(); st.session_state['current_design'] = []; st.success("已扣庫存"); st.rerun()
