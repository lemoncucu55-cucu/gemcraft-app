# --- 頁面 C: 設計與成本計算 (保證顯示工資欄位版) ---
elif page == "🧮 設計與成本計算":
    st.header("🧱 作品設計")
    inv = st.session_state['inventory']
    if inv.empty:
        st.warning("請先前往庫存管理進貨。")
    else:
        # A. 選擇材料區
        inv_l = inv.copy()
        inv_l['label'] = inv_l.apply(make_inventory_label, axis=1)
        c1, c2 = st.columns([3, 1])
        pick = c1.selectbox("選擇材料", inv_l['label'].tolist())
        qty_pick = c2.number_input("數量", min_value=1, value=1)
        
        if st.button("📥 加入材料清單"):
            idx = inv_l[inv_l['label'] == pick].index[0]
            item = inv.loc[idx]
            st.session_state['current_design'].append({
                '編號': item['編號'], '名稱': item['名稱'], '數量': qty_pick,
                '單價': float(item['單顆成本']), '小計': float(item['單顆成本']) * qty_pick
            })
            st.rerun()

        # B. 費用計算與顯示區 (只要清單不為空就顯示)
        if st.session_state['current_design']:
            df_design = pd.DataFrame(st.session_state['current_design'])
            st.subheader("📋 目前材料明細")
            
            # 只有主管能看材料小計
            d_cols = ['名稱', '數量', '小計'] if st.session_state['admin_mode'] else ['名稱', '數量']
            st.table(df_design[d_cols])
            mat_subtotal = df_design['小計'].sum()
            
            st.divider()
            st.subheader("💰 額外成本紀錄")
            
            # 【關鍵修改】: 將輸入框移出 admin_mode 判斷，所有人都能填寫
            cx, cy, cz = st.columns(3)
            labor = cx.number_input("🛠️ 工資 (元)", min_value=0, value=0, step=10, key="labor_in")
            misc = cy.number_input("📦 雜支 (元)", min_value=0, value=0, step=5, key="misc_in")
            ship = cz.number_input("🚚 運費 (元)", min_value=0, value=0, step=1, key="ship_in")
            
            total_cost = mat_subtotal + labor + misc + ship
            
            # 只有主管能看到總成本與建議售價
            if st.session_state['admin_mode']:
                st.metric("🔥 作品總成本", f"${total_cost:.1f}")
                s3, s5 = st.columns(2)
                s3.success(f"建議售價 (x3): ${round(total_cost * 3)}")
                s5.success(f"建議售價 (x5): ${round(total_cost * 5)}")

            # C. 作品名稱與存檔
            with st.form("sale_submit_form"):
                work_name = st.text_input("作品名稱", "未命名作品")
                note = st.text_area("備註")
                confirm_sale = st.checkbox("售出 (自動扣除庫存並儲存紀錄)", value=True)
                
                # 提交按鈕
                if st.form_submit_button("✅ 儲存設計紀錄"):
                    # 組合細節文字
                    details_str = ", ".join([f"{d['名稱']}x{d['數量']}" for d in st.session_state['current_design']])
                    
                    # 紀錄資料
                    new_sale_entry = {
                        '售出時間': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        '作品名稱': work_name,
                        '材料明細': details_str,
                        '材料小計': mat_subtotal,
                        '工資': labor,
                        '雜支': misc,
                        '運費': ship,
                        '總成本': total_cost,
                        '建議售價x3': round(total_cost * 3),
                        '建議售價x5': round(total_cost * 5),
                        '備註': note
                    }
                    st.session_state['design_sales'] = pd.concat([st.session_state['design_sales'], pd.DataFrame([new_sale_entry])], ignore_index=True)
                    
                    # 扣庫存邏輯
                    if confirm_sale:
                        for d in st.session_state['current_design']:
                            st.session_state['inventory'].loc[st.session_state['inventory']['編號'] == d['編號'], '庫存(顆)'] -= d['數量']
                    
                    save_inventory()
                    save_design_sales()
                    st.session_state['current_design'] = [] # 清空
                    st.success(f"作品「{work_name}」紀錄成功！")
                    time.sleep(1)
                    st.rerun()

        if st.button("🗑️ 清空目前的設計清單"):
            st.session_state['current_design'] = []
            st.rerun()
