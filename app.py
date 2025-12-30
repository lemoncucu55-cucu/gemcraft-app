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

HISTORY_COLUMNS = [
    '紀錄時間', '單號', '動作', '倉庫', '編號', '分類', '名稱', '規格',
    '廠商', '數量變動', '進貨總價', '單價'
]

# 作品設計紀錄：正式存成欄位（材料成本/工資/雜支/運費）
DESIGN_SALES_COLUMNS = [
    '售出時間', '作品名稱', '材料明細',
    '材料成本', '工資', '雜支', '運費', '總成本',
    '建議售價x3', '建議售價x5', '備註'
]

# 主管模式需要隱藏敏感資訊的欄位（你可自行增減）
SENSITIVE_COLUMNS = [
    '進貨總價', '單顆成本', '進貨數量(顆)', '進貨日期', '進貨廠商',
    '材料成本', '工資', '雜支', '運費', '總成本', '單價', '小計',
    '建議售價x3', '建議售價x5'
]

DEFAULT_CSV_FILE = 'inventory_backup_v2.csv'
HISTORY_FILE = 'inventory_history.csv'
DESIGN_SALES_FILE = 'design_sales_history.csv'

DEFAULT_WAREHOUSES = ["Imeng", "千畇"]
DEFAULT_SUPPLIERS = ["小聰頭", "廠商A", "廠商B", "自用", "蝦皮", "淘寶", "TB-東吳天然石坊", "永安", "Rich"]
DEFAULT_SHAPES = ["圓珠", "切角", "鑽切", "圓筒", "方體", "長柱", "不規則", "造型", "原礦"]
DEFAULT_ELEMENTS = ["金", "木", "水", "火", "土", "綜合", "銀", "銅", "14K包金"]

# ==========================================
# 2. 儲存/載入 & Robust Import
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
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')

    # 若曾經加過 label 欄位，直接丟掉避免衝突
    if 'label' in df.columns:
        df = df.drop(columns=['label'])

    # 若缺倉庫欄位，補預設
    if '倉庫' not in df.columns:
        df.insert(1, '倉庫', 'Imeng')

    # 補齊欄位
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNS].copy()

    # 數值欄位轉型
    for col in ['寬度mm', '長度mm', '進貨總價', '進貨數量(顆)', '庫存(顆)', '單顆成本']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 日期欄位允許字串
    if '進貨日期' in df.columns:
        df['進貨日期'] = df['進貨日期'].astype(str).replace('nan', '')

    return df

def robust_import_history(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')

    for col in HISTORY_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[HISTORY_COLUMNS].copy()
    df['數量變動'] = pd.to_numeric(df['數量變動'], errors='coerce').fillna(0)
    df['進貨總價'] = pd.to_numeric(df['進貨總價'], errors='coerce').fillna(0)
    df['單價'] = pd.to_numeric(df['單價'], errors='coerce').fillna(0)
    return df

def robust_import_design_sales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip().str.replace('\ufeff', '')

    for col in DESIGN_SALES_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[DESIGN_SALES_COLUMNS].copy()

    # 轉型數值欄位
    for col in ['材料成本', '工資', '雜支', '運費', '總成本', '建議售價x3', '建議售價x5']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df

# ==========================================
# 3. UI 小工具
# ==========================================

def format_size(row) -> str:
    try:
        w = float(row.get('寬度mm', 0))
        l = float(row.get('長度mm', 0))
        if l > 0:
            return f"{w:g}x{l:g}mm"
        return f"{w:g}mm"
    except Exception:
        return "0mm"

def make_inventory_label(row) -> str:
    sz = format_size(row)
    elem = f"({row.get('五行','')})" if row.get('五行','') else ""
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

def input_or_select(label, options, key):
    choice = st.selectbox(label, options, key=key)
    if choice == "➕ 手動輸入/新增":
        return st.text_input(f"{label}（手動輸入）", key=f"{key}_manual").strip()
    return choice

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# ==========================================
# 4. 初始化 session_state
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
            st.session_state['design_sales'] = robust_import_design_sales(pd.read_csv(DESIGN_SALES_FILE, encoding='utf-8-sig'))
        except Exception:
            st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)
    else:
        st.session_state['design_sales'] = pd.DataFrame(columns=DESIGN_SALES_COLUMNS)

if 'admin_mode' not in st.session_state:
    st.session_state['admin_mode'] = False

if 'current_design' not in st.session_state:
    st.session_state['current_design'] = []

# ==========================================
# 5. 頁面設定
# ==========================================

st.set_page_config(page_title="GemCraft 庫存管理系統", layout="wide")
st.title("💎 GemCraft 庫存管理系統")
st.caption("✅ 已更新：v2025-12-30（含工資/雜支/運費）")

# ==========================================
# 6. Sidebar：權限、導航、下載、上傳
# ==========================================

with st.sidebar:
    st.header("🔑 權限驗證")
    pwd = st.text_input("主管密碼", type="password")
    st.session_state['admin_mode'] = (pwd == "admin123")

    st.header("功能導航")
    page = st.radio("前往", ["📦 庫存管理與進貨", "📜 紀錄明細查詢", "🧮 設計與成本計算"])

    st.divider()
    st.header("📥 下載報表")

    inv = st.session_state['inventory']
    his = st.session_state['history']
    dsg = st.session_state['design_sales']

    if not inv.empty:
        st.download_button(
            "📥 下載目前庫存總表",
            inv.to_csv(index=False).encode('utf-8-sig'),
            f'inventory_{date.today()}.csv',
            "text/csv"
        )
    if not his.empty:
        st.download_button(
            "📜 下載出入庫紀錄表",
            his.to_csv(index=False).encode('utf-8-sig'),
            f'history_{date.today()}.csv',
            "text/csv"
        )
    if not dsg.empty:
        st.download_button(
            "💍 下載設計作品紀錄",
            dsg.to_csv(index=False).encode('utf-8-sig'),
            f'design_sales_{date.today()}.csv',
            "text/csv"
        )

    # ✅ 上傳功能（拖拉 CSV）加回來
    st.divider()
    st.header("📤 上傳報表/匯入資料")

    up = st.file_uploader("上傳庫存總表 CSV（inventory_...csv / inventory_backup_v2.csv）", type=["csv"], key="upload_inventory")
    if up is not None:
        try:
            df_up = pd.read_csv(up, encoding="utf-8-sig")
        except Exception:
            df_up = pd.read_csv(up, encoding="utf-8")
        st.session_state["inventory"] = robust_import_inventory(df_up)
        save_inventory()
        st.success("✅ 已匯入庫存總表並存檔")
        st.rerun()

    up_h = st.file_uploader("上傳出入庫紀錄 CSV（inventory_history.csv / history_...csv）", type=["csv"], key="upload_history")
    if up_h is not None:
        try:
            df_h = pd.read_csv(up_h, encoding="utf-8-sig")
        except Exception:
            df_h = pd.read_csv(up_h, encoding="utf-8")
        st.session_state["history"] = robust_import_history(df_h)
        save_history()
        st.success("✅ 已匯入出入庫紀錄並存檔")
        st.rerun()

    up_d = st.file_uploader("上傳設計作品紀錄 CSV（design_sales_history.csv / design_sales_...csv）", type=["csv"], key="upload_design_sales")
    if up_d is not None:
        try:
            df_d = pd.read_csv(up_d, encoding="utf-8-sig")
        except Exception:
            df_d = pd.read_csv(up_d, encoding="utf-8")
        st.session_state["design_sales"] = robust_import_design_sales(df_d)
        save_design_sales()
        st.success("✅ 已匯入設計作品紀錄並存檔")
        st.rerun()

# ==========================================
# 7. 頁面 A：庫存管理與進貨
# ==========================================

if page == "📦 庫存管理與進貨":
    tab1, tab2, tab3, tab4 = st.tabs(["🔄 舊品補貨", "✨ 建立新商品", "📤 出庫/入庫", "🛠️ 修改與盤點"])

    # -------- tab1：補貨 ----------
    with tab1:
        inv = st.session_state['inventory']
        if inv.empty:
            st.info("目前庫存是空的。請到「建立新商品」新增第一筆資料，或用左側上傳匯入。")
        else:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇補貨商品", inv_l['label'].tolist(), key="t1_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]

            with st.form("restock_form"):
                st.write(f"倉庫: **{row['倉庫']}** | 名稱: **{row['名稱']}** | 目前庫存: **{int(row['庫存(顆)'])}**")
                c1, c2 = st.columns(2)
                qty = c1.number_input("進貨數量", min_value=1, value=1, step=1)
                cost = c2.number_input("進貨總價", min_value=0.0, value=0.0, step=10.0) if st.session_state['admin_mode'] else 0.0

                if st.form_submit_button("確認補貨"):
                    old_q, old_c = float(row['庫存(顆)']), float(row['單顆成本'])
                    new_q = old_q + qty

                    # 主管模式才更新成本
                    if st.session_state['admin_mode'] and new_q > 0:
                        new_avg = ((old_q * old_c) + cost) / new_q
                        st.session_state['inventory'].at[idx, '單顆成本'] = new_avg

                    st.session_state['inventory'].at[idx, '庫存(顆)'] = new_q
                    st.session_state['inventory'].at[idx, '進貨日期'] = str(date.today())
                    if st.session_state['admin_mode']:
                        st.session_state['inventory'].at[idx, '進貨總價'] = float(cost)

                    log = {
                        '紀錄時間': now_str(),
                        '單號': 'IN',
                        '動作': '補貨入庫',
                        '倉庫': row['倉庫'],
                        '編號': row['編號'],
                        '分類': row['分類'],
                        '名稱': row['名稱'],
                        '規格': format_size(row),
                        '廠商': row.get('進貨廠商', ''),
                        '數量變動': qty,
                        '進貨總價': cost,
                        '單價': (cost / qty if qty > 0 else 0)
                    }
                    st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)

                    save_inventory()
                    save_history()
                    st.success("✅ 已補貨並寫入歷史明細")
                    st.rerun()

    # -------- tab2：建立新商品 ----------
    with tab2:
        with st.form("add_new"):
            c1, c2, c3 = st.columns(3)
            wh = c1.selectbox("倉庫", DEFAULT_WAREHOUSES)
            cat = c2.selectbox("分類", ["天然石", "配件", "耗材"])
            name = c3.text_input("名稱", value="")

            s1, s2, s3 = st.columns(3)
            w_mm = s1.number_input("寬度 (mm)", min_value=0.0, value=0.0, step=0.5)
            l_mm = s2.number_input("長度 (mm)", min_value=0.0, value=0.0, step=0.5)
            shape = input_or_select("形狀", get_dynamic_options('形狀', DEFAULT_SHAPES), "new_shape")

            c4, c5, c6 = st.columns(3)
            elem = input_or_select("五行", get_dynamic_options('五行', DEFAULT_ELEMENTS), "new_elem")
            sup = input_or_select("進貨廠商", get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS), "new_sup")
            qty_init = c6.number_input("初始數量", min_value=1, value=1, step=1)

            price_init = st.number_input("初始進貨總價", min_value=0.0, value=0.0, step=10.0) if st.session_state['admin_mode'] else 0.0

            if st.form_submit_button("➕ 建立商品"):
                if not name.strip():
                    st.error("請輸入名稱")
                    st.stop()

                nid = f"ST{int(time.time())}"
                unit_cost = (price_init / qty_init) if qty_init > 0 else 0

                new_r = {
                    '編號': nid,
                    '倉庫': wh,
                    '分類': cat,
                    '名稱': name.strip(),
                    '寬度mm': w_mm,
                    '長度mm': l_mm,
                    '形狀': shape,
                    '五行': elem,
                    '進貨總價': float(price_init) if st.session_state['admin_mode'] else 0.0,
                    '進貨數量(顆)': float(qty_init),
                    '進貨日期': str(date.today()),
                    '進貨廠商': sup,
                    '庫存(顆)': float(qty_init),
                    '單顆成本': float(unit_cost) if st.session_state['admin_mode'] else 0.0
                }

                st.session_state['inventory'] = pd.concat([st.session_state['inventory'], pd.DataFrame([new_r])], ignore_index=True)

                log_new = {
                    '紀錄時間': now_str(),
                    '單號': 'NEW',
                    '動作': '新商品建立入庫',
                    '倉庫': wh,
                    '編號': nid,
                    '分類': cat,
                    '名稱': name.strip(),
                    '規格': f"{w_mm:g}x{l_mm:g}mm" if l_mm > 0 else f"{w_mm:g}mm",
                    '廠商': sup,
                    '數量變動': qty_init,
                    '進貨總價': float(price_init) if st.session_state['admin_mode'] else 0.0,
                    '單價': float(unit_cost) if st.session_state['admin_mode'] else 0.0
                }
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log_new])], ignore_index=True)

                save_inventory()
                save_history()
                st.success(f"✅ 已建立商品「{name}」並寫入明細")
                st.rerun()

    # -------- tab3：出庫/入庫 ----------
    with tab3:
        inv = st.session_state['inventory']
        if inv.empty:
            st.info("目前庫存是空的。請先新增或上傳匯入。")
        else:
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇商品", inv_l['label'].tolist(), key="move_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]

            move_type = st.radio("動作", ["📤 出庫（領用/售出）", "📥 入庫（退回/補上）"], horizontal=True)
            qty = st.number_input("數量", min_value=1, value=1, step=1)

            if st.button("✅ 確認動作"):
                stock_now = float(row['庫存(顆)'])
                delta = -qty if "出庫" in move_type else qty
                if stock_now + delta < 0:
                    st.error(f"庫存不足！目前庫存 {stock_now}，無法出庫 {qty}")
                    st.stop()

                st.session_state['inventory'].at[idx, '庫存(顆)'] = stock_now + delta

                log = {
                    '紀錄時間': now_str(),
                    '單號': 'MOVE',
                    '動作': '出庫' if delta < 0 else '入庫',
                    '倉庫': row['倉庫'],
                    '編號': row['編號'],
                    '分類': row['分類'],
                    '名稱': row['名稱'],
                    '規格': format_size(row),
                    '廠商': row.get('進貨廠商', ''),
                    '數量變動': delta,
                    '進貨總價': 0,
                    '單價': float(row.get('單顆成本', 0)) if st.session_state['admin_mode'] else 0
                }
                st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)

                save_inventory()
                save_history()
                st.success("✅ 已完成並寫入歷史明細")
                st.rerun()

    # -------- tab4：修改與盤點 ----------
    with tab4:
        inv = st.session_state['inventory']
        if inv.empty:
            st.info("目前庫存是空的。請先新增或上傳匯入。")
        else:
            st.write("你可以在這裡進行「庫存盤點」或修改基本資訊。")
            inv_l = inv.copy()
            inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
            target = st.selectbox("選擇要修改的商品", inv_l['label'].tolist(), key="edit_sel")
            idx = inv_l[inv_l['label'] == target].index[0]
            row = inv.loc[idx]

            with st.form("edit_form"):
                c1, c2, c3 = st.columns(3)
                new_name = c1.text_input("名稱", value=str(row['名稱']))
                new_cat = c2.text_input("分類", value=str(row['分類']))
                new_stock = c3.number_input("庫存(顆)", min_value=0, value=int(float(row['庫存(顆)'])), step=1)

                new_supplier = st.text_input("進貨廠商", value=str(row.get('進貨廠商', '')))
                new_shape = st.text_input("形狀", value=str(row.get('形狀', '')))
                new_elem = st.text_input("五行", value=str(row.get('五行', '')))

                if st.session_state['admin_mode']:
                    new_unit = st.number_input("單顆成本", min_value=0.0, value=float(row.get('單顆成本', 0.0)), step=1.0)
                else:
                    new_unit = float(row.get('單顆成本', 0.0))

                if st.form_submit_button("💾 儲存修改"):
                    st.session_state['inventory'].at[idx, '名稱'] = new_name.strip()
                    st.session_state['inventory'].at[idx, '分類'] = new_cat.strip()
                    st.session_state['inventory'].at[idx, '庫存(顆)'] = float(new_stock)
                    st.session_state['inventory'].at[idx, '進貨廠商'] = new_supplier.strip()
                    st.session_state['inventory'].at[idx, '形狀'] = new_shape.strip()
                    st.session_state['inventory'].at[idx, '五行'] = new_elem.strip()
                    if st.session_state['admin_mode']:
                        st.session_state['inventory'].at[idx, '單顆成本'] = float(new_unit)

                    save_inventory()
                    st.success("✅ 已儲存修改")
                    st.rerun()

# ==========================================
# 8. 頁面 B：紀錄明細查詢
# ==========================================

elif page == "📜 紀錄明細查詢":
    st.header("📜 出入庫紀錄明細查詢")

    his = st.session_state['history']
    if his.empty:
        st.info("目前沒有出入庫紀錄。")
    else:
        c1, c2, c3 = st.columns(3)
        kw = c1.text_input("關鍵字（編號/名稱/動作）", value="")
        wh = c2.selectbox("倉庫", ["全部"] + DEFAULT_WAREHOUSES)
        act = c3.selectbox("動作", ["全部", "補貨入庫", "新商品建立入庫", "出庫", "入庫"])

        df = his.copy()

        if kw.strip():
            k = kw.strip()
            df = df[df.apply(lambda r: k in str(r.get('編號','')) or k in str(r.get('名稱','')) or k in str(r.get('動作','')), axis=1)]

        if wh != "全部":
            df = df[df['倉庫'] == wh]

        if act != "全部":
            df = df[df['動作'] == act]

        df = df.sort_values(by="紀錄時間", ascending=False)

        if not st.session_state['admin_mode']:
            # 非主管模式：遮掉敏感欄位（若存在）
            show_cols = [c for c in df.columns if c not in ['進貨總價', '單價']]
            st.dataframe(df[show_cols], use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

# ==========================================
# 9. 頁面 C：設計與成本計算（含工資/雜支/運費）
# ==========================================

elif page == "🧮 設計與成本計算":
    st.header("🧮 作品設計與成本計算")

    inv = st.session_state['inventory']
    if inv.empty:
        st.warning("目前無庫存資料。請先到「庫存管理與進貨」新增商品，或用左側「上傳報表」匯入庫存 CSV。")
    else:
        inv_l = inv.copy()
        inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)

        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv_l['label'].tolist())
        qty_pick = c2.number_input("數量", min_value=1, value=1, step=1)

        if st.button("📥 加入材料清單"):
            idx = inv_l[inv_l['label'] == pick].index[0]
            item = inv.loc[idx]

            unit_cost = float(item.get('單顆成本', 0.0)) if st.session_state['admin_mode'] else 0.0
            st.session_state['current_design'].append({
                '編號': item['編號'],
                '名稱': item['名稱'],
                '數量': int(qty_pick),
                '單價': unit_cost,
                '小計': unit_cost * int(qty_pick)
            })
            st.rerun()

        # 顯示目前設計清單
        if st.session_state['current_design']:
            df_curr = pd.DataFrame(st.session_state['current_design'])

            st.subheader("📋 目前設計清單")
            if st.session_state['admin_mode']:
                st.table(df_curr[['名稱', '數量', '單價', '小計']])
            else:
                st.table(df_curr[['名稱', '數量']])

            # 成本計算
            material_cost = float(df_curr['小計'].sum()) if st.session_state['admin_mode'] else 0.0

            st.divider()
            st.subheader("💰 額外費用輸入")
            ca, cb, cc = st.columns(3)
            labor_val = ca.number_input("🛠️ 工資 (元)", min_value=0.0, value=0.0, step=10.0)
            misc_val = cb.number_input("📦 雜支 (元)", min_value=0.0, value=0.0, step=5.0)
            ship_val = cc.number_input("🚚 運費 (元)", min_value=0.0, value=0.0, step=1.0)

            total_cost = material_cost + float(labor_val) + float(misc_val) + float(ship_val)

            if st.session_state['admin_mode']:
                st.info(f"🧱 材料成本: ${material_cost:.1f} + 額外費用: ${(labor_val + misc_val + ship_val):.1f}")
                st.metric("作品總成本", f"${total_cost:.1f}")
                s3, s5 = st.columns(2)
                s3.success(f"建議售價 (x3): ${round(total_cost * 3)}")
                s5.success(f"建議售價 (x5): ${round(total_cost * 5)}")
            else:
                st.info("非主管模式：為避免成本外洩，成本/售價不顯示（仍可正常扣庫存與做作品紀錄）。")

            st.divider()

            with st.form("design_sale_form"):
                work_name = st.text_input("作品名稱", value="未命名作品")
                note = st.text_area("備註", value="")

                if st.form_submit_button("✅ 售出（自動扣庫存並儲存紀錄）"):
                    # 防呆：庫存不足不可售出
                    for d in st.session_state['current_design']:
                        stock_now = float(st.session_state['inventory'].loc[
                            st.session_state['inventory']['編號'] == d['編號'], '庫存(顆)'
                        ].values[0])
                        if stock_now < d['數量']:
                            st.error(f"庫存不足：{d['名稱']} 目前庫存 {stock_now}，但你要扣 {d['數量']}")
                            st.stop()

                    # 扣庫存
                    for d in st.session_state['current_design']:
                        st.session_state['inventory'].loc[
                            st.session_state['inventory']['編號'] == d['編號'], '庫存(顆)'
                        ] -= d['數量']

                        # 同步寫入 history（可追蹤作品耗用）
                        row = st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == d['編號']].iloc[0]
                        log = {
                            '紀錄時間': now_str(),
                            '單號': 'SALE',
                            '動作': '出庫',
                            '倉庫': row['倉庫'],
                            '編號': row['編號'],
                            '分類': row['分類'],
                            '名稱': row['名稱'],
                            '規格': format_size(row),
                            '廠商': row.get('進貨廠商', ''),
                            '數量變動': -int(d['數量']),
                            '進貨總價': 0,
                            '單價': float(row.get('單顆成本', 0)) if st.session_state['admin_mode'] else 0
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)

                    details = ", ".join([f"{d['名稱']}x{d['數量']}" for d in st.session_state['current_design']])

                    new_sale = {
                        '售出時間': now_str(),
                        '作品名稱': work_name.strip(),
                        '材料明細': details,
                        '材料成本': float(material_cost),
                        '工資': float(labor_val),
                        '雜支': float(misc_val),
                        '運費': float(ship_val),
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
                    st.success("✅ 已完成售出紀錄並扣庫存")
                    time.sleep(0.8)
                    st.rerun()

            if st.button("🗑️ 清空設計清單"):
                st.session_state['current_design'] = []
                st.rerun()

        else:
            st.info("先選擇材料並加入清單後，才會出現工資/雜支/運費與成本計算。")
