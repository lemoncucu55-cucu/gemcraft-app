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
    '進貨總價', '進貨數量(顆)', '進貨數量(顆)', '進貨日期', '進貨廠商', 
    '庫存(顆)', '單顆成本'
]

SENSITIVE_COLUMNS = [
    '進貨總價', '單顆成本', '材料成本', '總成本', '單價', '小計', 
    '售價(x3)', '售價(x5)', '進貨數量(顆)', '進貨數量', '進貨日期', '進貨廠商', '廠商'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格', 
    '廠商', '數量變動', '進貨總價', '單價'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DEFAULT_WAREHOUSES = ["Imeng", "千畇"]
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

# ==========================================
# 2. 核心函式
# ==========================================

def save_inventory():
    try:
        if 'inventory' in st.session_state:
            st.session_state['inventory'].to_csv(DEFAULT_CSV_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def save_history():
    try:
        if 'history' in st.session_state:
            st.session_state['history'].to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    except Exception: pass

def robust_import_inventory(df):
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    if 'label' in df.columns:
        df = df.drop(columns=['label'])
    if '倉庫' not in df.columns:
        df.insert(1, '倉庫', 'Imeng')
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].copy()
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def format_size(row):
    try:
        w = float(row.get('寬度mm', 0))
        l = float(row.get('長度mm', 0))
        if l > 0:
            return f"{w}x{l}mm"
        return f"{w}mm"
    except:
        return "0mm"

def make_inventory_label(row):
    sz = format_size(row)
    elem = f"({row.get('五行','')})" if row.get('五行','') else ""
    sup = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    stock_val = int(float(row.get('庫存(顆)', 0)))
    return f"[{row.get('倉庫','Imeng')}] {elem} {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup} | 存:{stock_val}"

def get_dynamic_options(col, defaults):
    opts = set(defaults)
    if not st.session_state['inventory'].empty:
        exist = st.session_state['inventory'][col].astype(str).dropna().unique().tolist()
        opts.update([x for x in exist if x.strip() and x != 'nan'])
    return ["➕ 手動輸入/新增"] + sorted(list(opts))

# ==========================================
# 3. 初始化與 UI
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try: st.session_state['inventory'] = robust_import_inventory(pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig'))
        except: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else: st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try: st.session_state['history'] = pd.read_csv(HISTORY_FILE, encoding='utf-8-sig')
        except: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
    else: st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'admin_mode' not in st.session_state: st.session_state['admin_mode'] = False
if 'current_design' not in st.session_state: st.session_state['current_design'] = []

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")
    
    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 紀錄明細查詢", "🧮 設計與成本計算"])
    
    st.divider()
    st.header("📥 下載報表")
    if not st.session_state['inventory'].empty:
        csv_inv = st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載目前庫存總表", csv_inv, f'inventory_{date.today()}.csv', "text/csv")
    if not st.session_state['history'].empty:
        csv_hist = st.session_state['history'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📜 下載出入庫紀錄表", csv_hist, f'history_{date.today()}.csv', "text/csv")

    st.divider()
    if st.button("🔴 重置系統", type="secondary"):
        st.session_state.clear(); st.rerun()

# ------------------------------------------
# 頁面 A: 庫存管理
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    tab1, tab2, tab4, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用與出庫", "🛠️ 修改與盤點"])
    
    with tab1: # 補貨
        inv = st.session_state['inventory']
        if not inv.empty:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇補貨商品", inv_l['label'].tolist(), key="t1_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]
            with st.form("restock_form"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}**")
                c1, c2 = st.columns(2)
                qty = c1.number_input("進貨數量", min_value=1, value=1)
                cost = c2.number_input("進貨總價", min_value=0.0) if st.session_state['admin_mode'] else 0.0
                if st.form_submit_button("確認補貨"):
                    old_q, old_c = float(row['庫存(顆)']), float(row['單顆成本'])
                    new_q = old_q + qty
                    new_avg = ((old_q * old_c) + cost) / new_q if new_q > 0 else 0
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                    if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = new_avg
                    log = {'紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'IN', '動作': '補貨入庫', '倉庫': row['倉庫'], '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'], '規格': format_size(row), '廠商': row['進貨廠商'], '數量變動': qty, '進貨總價': cost, '單價': (cost/qty if qty>0 else 0)}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    save_inventory(); save_history(); st.success("已補貨"); st.rerun()

    with tab2: # ✨ 建立新商品
        with st.form("add_new"):
            c1, c2, c3 = st.columns(3)
            wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES)
            cat = c2.selectbox("分類", ["天然石", "配件", "耗材"])
            name = c3.text_input("名稱")
            
            st.markdown("##### 📏 規格尺寸")
            s1, s2, s3 = st.columns(3)
            w_mm = s1.number_input("寬度 (mm)", min_value=0.0, step=0.1, value=0.0)
            l_mm = s2.number_input("長度 (mm)", min_value=0.0, step=0.1, value=0.0)
            shape = s3.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            if shape == "➕ 手動輸入/新增": shape = st.text_input("輸入自定義形狀")
            
            st.markdown("##### 🏷️ 其他資訊")
            c4, c5, c6 = st.columns(3)
            elem = c4.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS))
            if elem == "➕ 手動輸入/新增": elem = st.text_input("輸入自定義五行")
            sup = c5.selectbox("進貨廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS))
            if sup == "➕ 手動輸入/新增": sup = st.text_input("輸入自定義廠商")
            qty_init = c6.number_input("初始數量", min_value=1, value=1)
            
            if st.form_submit_button("➕ 建立商品"):
                nid = f"ST{int(time.time())}"
                new_r = {
                    '編號': nid, '倉庫': wh, '分類': cat, '名稱': name, 
                    '寬度mm': w_mm, '長度mm': l_mm, '形狀': shape, '五行': elem, 
                    '進貨廠商': sup, '庫存(顆)': qty_init, '單顆成本': 0, '進貨日期': date.today()
                }
                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_r])], ignore_index=True)
                save_inventory(); st.success(f"已成功建立新商品：{name}"); st.rerun()

    with tab4: # 📤 領用與出庫
        inv_o = st.session_state['inventory'].copy()
        if not inv_o.empty:
            inv_o['label'] = inv_o.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇出庫商品", inv_o['label'].tolist(), key="t4_sel")
            idx = inv_o[inv_o['label'] == target].index[0]
            row = st.session_state['inventory'].loc[idx]
            cur_s = int(float(row['庫存(顆)']))
            with st.form("out_form"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}** | 目前庫存: **{cur_s}**")
                qty_o = st.number_input("出庫數量", min_value=0, max_value=max(0, cur_s), value=0)
                reason = st.selectbox("出庫類別", ["自用", "損壞", "樣品", "其他"])
                note_out = st.text_area("詳細備註/說明")
                if st.form_submit_button("確認出庫"):
                    if qty_o > 0:
                        st.session_state['inventory'].at[idx, '庫存(顆)'] -= qty_o
                        action_msg = f"領用出庫({reason})" + (f" - {note_out}" if note_out else "")
                        log = {'紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'OUT', '動作': action_msg, '倉庫': row['倉庫'], '編號': row['編號'], '分類': row['分類'], '名稱': row['名稱'], '規格': format_size(row), '廠商': row['進貨廠商'], '數量變動': -qty_o, '進貨總價': 0, '單價': row['單顆成本']}
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                        save_inventory(); save_history(); st.warning("已扣除庫存並記錄"); st.rerun()

    with tab3: # 🛠️ 修改與盤點
        if not st.session_state['inventory'].empty:
            inv_e = st.session_state['inventory'].copy()
            inv_e['label'] = inv_e.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇要修正的商品", inv_e['label'].tolist(), key="t3_sel")
            idx = inv_e[inv_e['label'] == target].index[0]
            orig = st.session_state['inventory'].loc[idx]
            val = int(float(orig['庫存(顆)']))
            with st.form("edit_manual_form"):
                st.write(f"正在修正編號: **{orig['編號']}**")
                c1, c2 = st.columns(2)
                nm = c1.text_input("商品名稱修正", orig['名稱'])
                wh = c2.selectbox("調整所屬倉庫", DEFAULT_WAREHOUSES, index=DEFAULT_WAREHOUSES.index(orig['倉庫']) if orig['倉庫'] in DEFAULT_WAREHOUSES else 0)
                
                c3, c4, c5 = st.columns(3)
                wm = c3.number_input("寬度mm修正", value=float(orig['寬度mm']))
                lm = c4.number_input("長度mm修正", value=float(orig['長度mm']))
                qt = c5.number_input("盤點庫存量修正", min_value=0, value=val)
                
                co = st.number_input("單顆成本修正", min_value=0.0, value=float(orig['單顆成本'])) if st.session_state['admin_mode'] else float(orig['單顆成本'])
                el = st.selectbox("五行修正", get_dynamic_options('五行', DEFAULT_ELEMENTS), index=0)
                note_edit = st.text_area("修正原因備註")
                if st.form_submit_button("💾 儲存盤點修正"):
                    st.session_state['inventory'].at[idx, '名稱'] = nm
                    st.session_state['inventory'].at[idx, '倉庫'] = wh
                    st.session_state['inventory'].at[idx, '寬度mm'] = wm
                    st.session_state['inventory'].at[idx, '長度mm'] = lm
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = qt
                    st.session_state['inventory'].at[idx, '五行'] = el if el != "➕ 手動輸入/新增" else orig['五行']
                    if st.session_state['admin_mode']: st.session_state['inventory'].at[idx, '單顆成本'] = co
                    action_msg = "盤點修正" + (f" - {note_edit}" if note_edit else "")
                    log = {'紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), '單號': 'ADJUST', '動作': action_msg, '倉庫': wh, '編號': orig['編號'], '分類': orig['分類'], '名稱': nm, '規格': format_size(orig), '廠商': orig['進貨廠商'], '數量變動': (qt - val), '進貨總價': 0, '單價': co}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                    save_inventory(); save_history(); st.success("修正已儲存"); st.rerun()
            if st.button("🗑️ 刪除該商品"):
                if st.session_state['admin_mode']:
                    st.session_state['inventory'] = st.session_state['inventory'].drop(idx).reset_index(drop=True)
                    save_inventory(); st.warning("已刪除"); st.rerun()
                else: st.error("權限不足")

    st.divider()
    vdf = st.session_state['inventory'].copy()
    if not vdf.empty:
        if not st.session_state['admin_mode']:
            vdf = vdf.drop(columns=[c for c in SENSITIVE_COLUMNS if c in vdf.columns])
        st.dataframe(vdf, use_container_width=True)

# ------------------------------------------
# 頁面 B: 紀錄查詢
# ------------------------------------------
elif page == "📜 紀錄明細查詢":
    st.subheader("📜 歷史出入庫明細")
    df_h = st.session_state['history'].copy()
    if not df_h.empty:
        if not st.session_state['admin_mode']:
            df_h = df_h.drop(columns=[c for c in SENSITIVE_COLUMNS if c in df_h.columns])
        st.dataframe(df_h, use_container_width=True)
    else: st.info("尚無紀錄")

# ------------------------------------------
# 頁面 C: 設計與計算 (強制顯示費用填寫區 - 終極修正版)
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.subheader("🧮 作品設計與成本核算")
    
    # --- 💡 這裡做了重大變動：將費用填寫框移到最前面，確保一定會出現 ---
    with st.expander("💰 第一步：填寫附加費用 (工資/雜支/運費)", expanded=True):
        f_c1, f_c2, f_c3 = st.columns(3)
        labor_val = f_c1.number_input("製作工資", min_value=0.0, step=10.0, key="fixed_labor")
        misc_val = f_c2.number_input("雜支包材", min_value=0.0, step=10.0, key="fixed_misc")
        ship_val = f_c3.number_input("物流運費", min_value=0.0, step=10.0, key="fixed_ship")
        st.caption("※ 即使沒有材料，這裡也應該顯示。如果沒看到，請重新整理網頁。")

    st.divider()

    items = st.session_state['inventory'].copy()
    if not items.empty:
        # 1. 材料選擇區
        st.markdown("##### 第二步：選擇材料")
        items['lbl'] = items.apply(make_inventory_label, axis=1)
        sel_col, qty_col = st.columns([3, 1])
        sel = sel_col.selectbox("選擇材料", items['lbl'], key="design_sel_v3")
        idx = items[items['lbl'] == sel].index[0]
        cur_s = int(float(items.loc[idx, '庫存(顆)']))
        qty = qty_col.number_input("數量", min_value=0, max_value=max(0, cur_s), value=0)
        
        if st.button("⬇️ 加入清單"):
            if qty > 0:
                st.session_state['current_design'].append({
                    '編號': items.loc[idx, '編號'], 
                    '名稱': items.loc[idx, '名稱'], 
                    '數量': qty, 
                    '單價': items.loc[idx, '單顆成本'],
                    '倉庫': items.loc[idx, '倉庫'],
                    '分類': items.loc[idx, '分類'],
                    '規格': format_size(items.loc[idx])
                })
                st.rerun()

        # 2. 結算清單顯示
        if st.session_state['current_design']:
            st.markdown("##### 第三步：確認清單並售出")
            ddf = pd.DataFrame(st.session_state['current_design'])
            ddf['小計'] = ddf['數量'] * ddf['單價']
            
            # 根據權限顯示欄位
            show_cols = ['名稱', '數量', '單價', '小計'] if st.session_state['admin_mode'] else ['名稱', '數量']
            st.table(ddf[show_cols])

            # 3. 計算總額
            mat_total = ddf['小計'].sum()
            extra_total = labor_val + misc_val + ship_val
            grand_total = mat_total + extra_total
            
            if st.session_state['admin_mode']:
                st.info(f"📊 主管總計：材料 ${mat_total:.0f} + 額外 ${extra_total:.0f} = **總成本 ${grand_total:.0f}**")
            
            # 4. 功能按鈕
            b_c1, b_c2 = st.columns(2)
            if b_c1.button("✅ 確認售出 (扣庫存)", use_container_width=True):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                # 扣庫存與記錄
                for _, r in ddf.iterrows():
                    st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == r['編號'], '庫存(顆)'] -= r['數量']
                    log = {'紀錄時間': ts, '單號': 'SALE', '動作': "作品售出", '倉庫': r['倉庫'], '編號': r['編號'], '分類': r['分類'], '名稱': r['名稱'], '規格': r['規格'], '廠商': '-', '數量變動': -r['數量'], '進貨總價': 0, '單價': r['單價']}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                
                # 紀錄費用
                if extra_total > 0:
                    f_log = {'紀錄時間': ts, '單號': 'FEES', '動作': f"附加費(工{labor_val}/雜{misc_val}/運{ship_val})", '倉庫': '-', '編號': '-', '分類': '費用', '名稱': '設計與運費', '規格': '-', '廠商': '-', '數量變動': 0, '進貨總價': extra_total, '單價': extra_total}
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([f_log])], ignore_index=True)
                
                save_inventory(); save_history()
                st.session_state['current_design'] = []
                st.success("已完成售出並存入歷史紀錄")
                time.sleep(1); st.rerun()

            if b_c2.button("🗑️ 清空設計清單", use_container_width=True):
                st.session_state['current_design'] = []
                st.rerun()
    else:
        st.info("無庫存資料")
