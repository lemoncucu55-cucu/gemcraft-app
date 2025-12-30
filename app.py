st.caption("版本：v2025-12-30（含工資/雜支/運費）")


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

SENSITIVE_COLUMNS = [
    '進貨總價', '單顆成本', '材料成本', '工資', '雜支', '運費', '額外費用合計',
    '總成本', '單價', '小計',
    '售價(x3)', '售價(x5)', '進貨數量(顆)', '進貨數量',
    '進貨日期', '進貨廠商', '廠商'
]

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格',
    '廠商', '數量變動', '進貨總價', '單價', '備註'
]

# ✅ 設計銷售欄位（新增正式費用欄位）
DESIGN_SALES_COLUMNS = [
    '售出時間', '作品名稱', '材料明細',
    '材料成本', '工資', '雜支', '運費', '額外費用合計',
    '總成本', '建議售價x3', '建議售價x5',
    '備註'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv'

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
    except Exception:
        pass

def save_history():
    try:
        if 'history' in st.session_state:
            st.session_state['history'].to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    except Exception:
        pass

def save_design_sales():
    try:
        if 'design_sales' in st.session_state:
            st.session_state['design_sales'].to_csv(DESIGN_SALES_FILE, index=False, encoding='utf-8-sig')
    except Exception:
        pass

def robust_import_inventory(df: pd.DataFrame) -> pd.DataFrame:
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

# ✅ robust import for design_sales（避免舊 CSV 少欄位崩潰）
def robust_import_design_sales(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')

    for col in DESIGN_SALES_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[DESIGN_SALES_COLUMNS].copy()

    num_cols = ['材料成本', '工資', '雜支', '運費', '額外費用合計', '總成本', '建議售價x3', '建議售價x5']
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df

def robust_import_history(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')
    for col in HISTORY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[HISTORY_COLUMNS].copy()

    for col in ['數量變動', '進貨總價', '單價']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df

def format_size(row) -> str:
    try:
        w = float(row.get('寬度mm', 0))
        l = float(row.get('長度mm', 0))
        if l > 0:
            return f"{w}x{l}mm"
        return f"{w}mm"
    except Exception:
        return "0mm"

def make_inventory_label(row) -> str:
    sz = format_size(row)
    elem = f"({row.get('五行','')})" if row.get('五行', '') else ""
    sup = f" | {row.get('進貨廠商','')}" if st.session_state.get('admin_mode', False) else ""
    stock_val = int(float(row.get('庫存(顆)', 0)))
    return f"[{row.get('倉庫','Imeng')}] {elem} {row.get('編號','')} | {row.get('名稱','')} | {row.get('形狀','')} ({sz}){sup} | 存:{stock_val}"

def get_dynamic_options(col, defaults):
    opts = set(defaults)
    inv = st.session_state.get('inventory', pd.DataFrame(columns=COLUMNS))
    if not inv.empty and col in inv.columns:
        exist = inv[col].astype(str).dropna().unique().tolist()
        opts.update([x for x in exist if x.strip() and x != 'nan'])
    return ["➕ 手動輸入/新增"] + sorted(list(opts))

def resolve_manual_input(selected, label, default_value=""):
    if selected == "➕ 手動輸入/新增":
        return st.text_input(f"手動輸入 {label}", value=default_value).strip()
    return selected

def add_history_log(action, wh, row, qty_delta, total_price=0.0, vendor="", note=""):
    log = {
        '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
        '單號': 'IN' if qty_delta > 0 else 'OUT',
        '動作': action,
        '倉庫': wh,
        '編號': row.get('編號', ''),
        '分類': row.get('分類', ''),
        '名稱': row.get('名稱', ''),
        '規格': format_size(row),
        '廠商': vendor,
        '數量變動': float(qty_delta),
        '進貨總價': float(total_price),
        '單價': float(total_price) / float(qty_delta) if qty_delta != 0 else 0.0,
        '備註': note
    }
    st.session_state['history'] = pd.concat(
        [st.session_state['history'], pd.DataFrame([log])],
        ignore_index=True
    )

# ==========================================
# 3. 初始化 Session State / 讀檔
# ==========================================

if 'inventory' not in st.session_state:
    if os.path.exists(DEFAULT_CSV_FILE):
        try:
            st.session_state['inventory'] = robust_import_inventory(pd.read_csv(DEFAULT_CSV_FILE, encoding='utf-8-sig'))
        except Exception:
            st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)
    else:
        st.session_state['inventory'] = pd.DataFrame(columns=COLUMNS)

if 'history' not in st.session_state:
    if os.path.exists(HISTORY_FILE):
        try:
            st.session_state['history'] = robust_import_history(pd.read_csv(HISTORY_FILE, encoding='utf-8-sig'))
        except Exception:
            st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)
    else:
        st.session_state['history'] = pd.DataFrame(columns=HISTORY_COLUMNS)

if 'design_sales' not in st.session_state:
    if os.path.exists(DESIGN_SALES_FILE):
        try:
            raw = pd.read_csv(DESIGN_SALES_FILE, encoding='utf-8-sig')
            st.session_state['design_sales'] = robust_import_design_sales(raw)
        except Exception:
            st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)
    else:
        st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)

if 'admin_mode' not in st.session_state:
    st.session_state['admin_mode'] = False

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 4. UI
# ==========================================

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
        st.download_button(
            "📥 下載目前庫存總表",
            st.session_state['inventory'].to_csv(index=False).encode('utf-8-sig'),
            f'inventory_{date.today()}.csv',
            "text/csv"
        )
    if not st.session_state['history'].empty:
        st.download_button(
            "📜 下載出入庫紀錄表",
            st.session_state['history'].to_csv(index=False).encode('utf-8-sig'),
            f'history_{date.today()}.csv',
            "text/csv"
        )
    if not st.session_state['design_sales'].empty:
        st.download_button(
            "💍 下載設計作品紀錄",
            st.session_state['design_sales'].to_csv(index=False).encode('utf-8-sig'),
            f'design_sales_{date.today()}.csv',
            "text/csv"
        )

# ------------------------------------------
# 頁面 A: 庫存管理與進貨
# ------------------------------------------
if page == "📦 庫存管理與進貨":
    tab1, tab2, tab4, tab3 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 領用/出庫與入庫", "🛠️ 修改與盤點"])

    # ========= tab1 補貨 =========
    with tab1:
        inv = st.session_state['inventory']
        if inv.empty:
            st.info("目前沒有庫存資料。請先到「建立新商品」新增。")
        else:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇補貨商品", inv_l['label'].tolist(), key="t1_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]

            with st.form("restock_form"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}**")
                c1, c2 = st.columns(2)
                qty = c1.number_input("進貨數量", min_value=1, value=1)
                cost = c2.number_input("進貨總價", min_value=0.0, value=0.0) if st.session_state['admin_mode'] else 0.0
                note = st.text_input("備註（可選）", value="")

                if st.form_submit_button("確認補貨"):
                    old_q = float(row['庫存(顆)'])
                    old_c = float(row['單顆成本'])
                    new_q = old_q + float(qty)

                    if st.session_state['admin_mode']:
                        new_avg = ((old_q * old_c) + float(cost)) / new_q if new_q > 0 else 0
                        st.session_state['inventory'].at[idx, '單顆成本'] = new_avg

                    st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q

                    add_history_log(
                        action='補貨入庫',
                        wh=row['倉庫'],
                        row=row,
                        qty_delta=qty,
                        total_price=cost,
                        vendor=row.get('進貨廠商', ''),
                        note=note
                    )

                    save_inventory()
                    save_history()
                    st.success("已補貨並寫入歷史明細")
                    st.rerun()

    # ========= tab2 建立新商品 =========
    with tab2:
        with st.form("add_new"):
            c1, c2, c3 = st.columns(3)
            wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES)
            cat = c2.selectbox("分類", ["天然石", "配件", "耗材"])
            name = c3.text_input("名稱", value="")

            s1, s2, s3 = st.columns(3)
            w_mm = s1.number_input("寬度 (mm)", min_value=0.0, value=0.0)
            l_mm = s2.number_input("長度 (mm)", min_value=0.0, value=0.0)

            shape_sel = s3.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES))
            shape = resolve_manual_input(shape_sel, "形狀")

            c4, c5, c6 = st.columns(3)
            elem_sel = c4.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS))
            elem = resolve_manual_input(elem_sel, "五行")

            sup_sel = c5.selectbox("進貨廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS))
            sup = resolve_manual_input(sup_sel, "進貨廠商")

            qty_init = c6.number_input("初始數量", min_value=1, value=1)
            price_init = st.number_input("初始進貨總價", min_value=0.0, value=0.0) if st.session_state['admin_mode'] else 0.0

            if st.form_submit_button("➕ 建立商品"):
                if not name.strip():
                    st.error("名稱不可為空。")
                else:
                    nid = f"ST{int(time.time())}"
                    new_r = {
                        '編號': nid,
                        '倉庫': wh,
                        '分類': cat,
                        '名稱': name.strip(),
                        '寬度mm': float(w_mm),
                        '長度mm': float(l_mm),
                        '形狀': shape.strip(),
                        '五行': elem.strip(),
                        '進貨總價': float(price_init),
                        '進貨數量(顆)': float(qty_init),
                        '進貨日期': date.today().strftime("%Y-%m-%d"),
                        '進貨廠商': sup.strip(),
                        '庫存(顆)': float(qty_init),
                        '單顆成本': float(price_init) / float(qty_init) if float(qty_init) > 0 else 0.0
                    }

                    st.session_state['inventory'] = pd.concat(
                        [st.session_state['inventory'], pd.DataFrame([new_r])],
                        ignore_index=True
                    )

                    add_history_log(
                        action='新商品建立入庫',
                        wh=wh,
                        row=new_r,
                        qty_delta=qty_init,
                        total_price=price_init,
                        vendor=sup,
                        note=""
                    )

                    save_inventory()
                    save_history()
                    st.success(f"已建立商品「{name}」並寫入明細")
                    st.rerun()

    # ========= tab4 出庫/入庫 =========
    with tab4:
        inv = st.session_state['inventory']
        if inv.empty:
            st.info("目前沒有庫存資料。")
        else:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)

            c1, c2 = st.columns([3, 1])
            target = c1.selectbox("選擇品項", inv_l['label'].tolist(), key="move_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]

            action = st.radio("動作", ["📤 出庫/領用", "📥 入庫（非補貨：例如退貨/調回）"], horizontal=True)
            qty = c2.number_input("數量", min_value=1, value=1, key="move_qty")
            note = st.text_input("備註（可選）", value="", key="move_note")

            if st.button("✅ 確認執行"):
                cur_stock = float(st.session_state['inventory'].at[idx, '庫存(顆)'])

                if action.startswith("📤"):
                    if cur_stock < float(qty):
                        st.error(f"庫存不足：目前 {int(cur_stock)}，欲出庫 {qty}")
                    else:
                        st.session_state['inventory'].at[idx, '庫存(顆)'] = cur_stock - float(qty)
                        add_history_log(
                            action='出庫/領用',
                            wh=row['倉庫'],
                            row=row,
                            qty_delta=-float(qty),
                            total_price=0.0,
                            vendor=row.get('進貨廠商', ''),
                            note=note
                        )
                        save_inventory()
                        save_history()
                        st.success("已完成出庫/領用並寫入明細")
                        st.rerun()
                else:
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = cur_stock + float(qty)
                    add_history_log(
                        action='入庫（調整）',
                        wh=row['倉庫'],
                        row=row,
                        qty_delta=float(qty),
                        total_price=0.0,
                        vendor=row.get('進貨廠商', ''),
                        note=note
                    )
                    save_inventory()
                    save_history()
                    st.success("已完成入庫（調整）並寫入明細")
                    st.rerun()

    # ========= tab3 修改/盤點 =========
    with tab3:
        inv = st.session_state['inventory']
        if inv.empty:
            st.info("目前沒有庫存資料。")
        else:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇要修改/盤點的品項", inv_l['label'].tolist(), key="edit_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]

            st.subheader("🛠️ 修改基本資料 / 盤點庫存")
            with st.form("edit_form"):
                c1, c2, c3 = st.columns(3)
                wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES, index=DEFAULT_WAREHOUSES.index(row['倉庫']) if row['倉庫'] in DEFAULT_WAREHOUSES else 0)
                cat = c2.selectbox("分類", ["天然石", "配件", "耗材"], index=["天然石", "配件", "耗材"].index(row['分類']) if row['分類'] in ["天然石", "配件", "耗材"] else 0)
                name = c3.text_input("名稱", value=str(row['名稱']))

                s1, s2, s3 = st.columns(3)
                w_mm = s1.number_input("寬度 (mm)", min_value=0.0, value=float(row['寬度mm']))
                l_mm = s2.number_input("長度 (mm)", min_value=0.0, value=float(row['長度mm']))

                shape_sel = s3.selectbox("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES), index=0)
                shape = resolve_manual_input(shape_sel, "形狀", default_value=str(row['形狀']))

                e1, e2, e3 = st.columns(3)
                elem_sel = e1.selectbox("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS), index=0)
                elem = resolve_manual_input(elem_sel, "五行", default_value=str(row['五行']))

                sup_sel = e2.selectbox("進貨廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS), index=0)
                sup = resolve_manual_input(sup_sel, "進貨廠商", default_value=str(row['進貨廠商']))

                stock = e3.number_input("庫存(顆)（盤點用）", min_value=0.0, value=float(row['庫存(顆)']))

                cost = 0.0
                if st.session_state['admin_mode']:
                    cost = st.number_input("單顆成本（主管可改）", min_value=0.0, value=float(row['單顆成本']))

                note = st.text_input("備註（可選）", value="")

                if st.form_submit_button("✅ 儲存修改"):
                    old_stock = float(row['庫存(顆)'])
                    delta = float(stock) - old_stock

                    st.session_state['inventory'].at[idx, '倉庫'] = wh
                    st.session_state['inventory'].at[idx, '分類'] = cat
                    st.session_state['inventory'].at[idx, '名稱'] = name.strip()
                    st.session_state['inventory'].at[idx, '寬度mm'] = float(w_mm)
                    st.session_state['inventory'].at[idx, '長度mm'] = float(l_mm)
                    st.session_state['inventory'].at[idx, '形狀'] = shape.strip()
                    st.session_state['inventory'].at[idx, '五行'] = elem.strip()
                    st.session_state['inventory'].at[idx, '進貨廠商'] = sup.strip()
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = float(stock)

                    if st.session_state['admin_mode']:
                        st.session_state['inventory'].at[idx, '單顆成本'] = float(cost)

                    if abs(delta) > 1e-9:
                        add_history_log(
                            action='盤點調整',
                            wh=wh,
                            row=row,
                            qty_delta=delta,
                            total_price=0.0,
                            vendor=sup,
                            note=f"盤點調整：原{old_stock} -> 新{stock}. {note}".strip()
                        )

                    save_inventory()
                    save_history()
                    st.success("已儲存修改")
                    st.rerun()

# ------------------------------------------
# 頁面 B: 紀錄明細查詢
# ------------------------------------------
elif page == "📜 紀錄明細查詢":
    st.header("📜 出入庫紀錄查詢")

    hist = st.session_state['history'].copy()
    if hist.empty:
        st.info("目前沒有任何出入庫紀錄。")
    else:
        c1, c2, c3 = st.columns(3)
        kw = c1.text_input("關鍵字（名稱/編號/廠商）", value="")
        action_filter = c2.selectbox("動作篩選", ["全部"] + sorted(hist['動作'].astype(str).unique().tolist()))
        wh_filter = c3.selectbox("倉庫篩選", ["全部"] + sorted(hist['倉庫'].astype(str).unique().tolist()))

        df = hist.copy()

        if kw.strip():
            k = kw.strip()
            mask = (
                df['名稱'].astype(str).str.contains(k, na=False) |
                df['編號'].astype(str).str.contains(k, na=False) |
                df['廠商'].astype(str).str.contains(k, na=False)
            )
            df = df[mask]

        if action_filter != "全部":
            df = df[df['動作'].astype(str) == action_filter]

        if wh_filter != "全部":
            df = df[df['倉庫'].astype(str) == wh_filter]

        df = df.sort_values(by='紀錄時間', ascending=False)

        if st.session_state['admin_mode']:
            st.dataframe(df, use_container_width=True)
        else:
            safe_cols = [c for c in df.columns if c not in SENSITIVE_COLUMNS]
            st.dataframe(df[safe_cols], use_container_width=True)

# ------------------------------------------
# 頁面 C: 設計與成本計算（含工資/雜支/運費）
# ------------------------------------------
elif page == "🧮 設計與成本計算":
    st.header("🧮 作品設計與成本計算")

    inv = st.session_state['inventory']
    if inv.empty:
        st.warning("目前無庫存資料。")
    else:
        inv_l = inv.copy()
        inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)

        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv_l['label'].tolist(), key="design_pick")
        qty_pick = c2.number_input("數量", min_value=1, value=1, key="design_qty")

        if st.button("📥 加入材料清單"):
            idx = inv_l[inv_l['label'] == pick].index[0]
            item = inv.loc[idx]

            cur_stock = float(item['庫存(顆)'])
            if cur_stock < float(qty_pick):
                st.error(f"庫存不足：目前 {int(cur_stock)}，欲使用 {qty_pick}")
            else:
                st.session_state['current_design'].append({
                    '編號': item['編號'],
                    '名稱': item['名稱'],
                    '數量': float(qty_pick),
                    '單價': float(item['單顆成本']),
                    '小計': float(item['單顆成本']) * float(qty_pick)
                })
                st.rerun()

        if st.session_state['current_design']:
            df_curr = pd.DataFrame(st.session_state['current_design'])
            st.subheader("📋 目前設計清單")

            if st.session_state['admin_mode']:
                st.table(df_curr[['名稱', '數量', '單價', '小計']])
            else:
                st.table(df_curr[['名稱', '數量']])

            material_cost = float(df_curr['小計'].sum()) if '小計' in df_curr.columns else 0.0

            st.divider()
            st.subheader("💰 額外費用輸入")
            ca, cb, cc = st.columns(3)
            labor_val = ca.number_input("🛠️ 工資 (元)", min_value=0, value=0, step=10, key="labor")
            misc_val = cb.number_input("📦 雜支 (元)", min_value=0, value=0, step=5, key="misc")
            ship_val = cc.number_input("🚚 運費 (元)", min_value=0, value=0, step=1, key="ship")

            extra_sum = float(labor_val) + float(misc_val) + float(ship_val)
            total_cost = float(material_cost) + extra_sum

            if st.session_state['admin_mode']:
                st.info(f"🧱 材料成本: ${material_cost:.1f} + 🧰 額外費用: ${extra_sum:.1f}")
                st.metric("作品總成本", f"${total_cost:.1f}")
                s3, s5 = st.columns(2)
                s3.success(f"建議售價 (x3): ${round(total_cost * 3)}")
                s5.success(f"建議售價 (x5): ${round(total_cost * 5)}")

            with st.form("design_sale_form"):
                work_name = st.text_input("作品名稱", value="未命名作品")
                note = st.text_area("備註", value="")
                if st.form_submit_button("✅ 售出（自動扣庫存並儲存紀錄）"):
                    for d in st.session_state['current_design']:
                        st.session_state['inventory'].loc[
                            st.session_state['inventory']['編號'] == d['編號'],
                            '庫存(顆)'
                        ] = st.session_state['inventory'].loc[
                            st.session_state['inventory']['編號'] == d['編號'],
                            '庫存(顆)'
                        ] - float(d['數量'])

                        row_item = st.session_state['inventory'][st.session_state['inventory']['編號'] == d['編號']].iloc[0].to_dict()
                        add_history_log(
                            action='作品製作出庫',
                            wh=row_item.get('倉庫', ''),
                            row=row_item,
                            qty_delta=-float(d['數量']),
                            total_price=0.0,
                            vendor=row_item.get('進貨廠商', ''),
                            note=f"作品：{work_name}".strip()
                        )

                    details = ", ".join([f"{d['名稱']}x{int(d['數量'])}" for d in st.session_state['current_design']])

                    new_sale = {
                        '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '作品名稱': work_name.strip(),
                        '材料明細': details,

                        '材料成本': float(material_cost),
                        '工資': float(labor_val),
                        '雜支': float(misc_val),
                        '運費': float(ship_val),
                        '額外費用合計': float(extra_sum),

                        '總成本': float(total_cost),
                        '建議售價x3': round(total_cost * 3),
                        '建議售價x5': round(total_cost * 5),

                        '備註': note.strip()
                    }

                    st.session_state['design_sales'] = pd.concat(
                        [st.session_state['design_sales'], pd.DataFrame([new_sale])],
                        ignore_index=True
                    )

                    save_inventory()
                    save_history()
                    save_design_sales()

                    st.session_state['current_design'] = []
                    st.success("已完成售出紀錄（已扣庫存＋寫入紀錄）")
                    time.sleep(0.8)
                    st.rerun()

        c_clear, _ = st.columns([1, 3])
        if c_clear.button("🗑️ 清空設計清單"):
            st.session_state['current_design'] = []
            st.rerun()

        st.divider()
        st.subheader("🧾 作品售出紀錄")
        ds = st.session_state['design_sales'].copy()
        if ds.empty:
            st.info("尚無作品售出紀錄。")
        else:
            if st.session_state['admin_mode']:
                st.dataframe(ds.sort_values('售出時間', ascending=False), use_container_width=True)
            else:
                safe_cols = ['售出時間', '作品名稱', '材料明細', '建議售價x3', '建議售價x5', '備註']
                st.dataframe(ds[safe_cols].sort_values('售出時間', ascending=False), use_container_width=True)
