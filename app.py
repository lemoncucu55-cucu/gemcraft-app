# --- 修正後的設計與成本計算區塊 ---
if st.session_state['current_design']:
    df_design = pd.DataFrame(st.session_state['current_design'])
    st.subheader("📋 目前材料明細")
    
    # 決定顯示哪些欄位
    display_cols = ['名稱', '數量', '小計'] if st.session_state['admin_mode'] else ['名稱', '數量']
    st.table(df_design[display_cols])
    
    mat_subtotal = df_design['小計'].sum()
    
    st.divider()
    st.subheader("💰 成本與額外費用")
    
    # 讓輸入框在任何模式下都可見 (如果您希望非主管也能輸入，請移除 admin_mode 判斷)
    ca, cb, cc = st.columns(3)
    labor = ca.number_input("🛠️ 工資 (元)", min_value=0, value=0, step=10)
    misc = cb.number_input("📦 雜支/包材 (元)", min_value=0, value=0, step=5)
    ship = cc.number_input("🚚 運費成本 (元)", min_value=0, value=0, step=1)
    
    total_cost = mat_subtotal + labor + misc + ship
    
    # 僅主管可看見總成本與建議售價
    if st.session_state['admin_mode']:
        st.metric("🔥 作品總成本", f"${total_cost:.1f}")
        s3, s5 = st.columns(2)
        s3.success(f"建議售價 (x3): ${round(total_cost * 3)}")
        s5.success(f"建議售價 (x5): ${round(total_cost * 5)}")

    # 售出存檔表單 (保持在下方)
    with st.form("sale_form"):
        work_name = st.text_input("作品名稱", "未命名作品")
        note = st.text_area("備註")
        if st.form_submit_button("✅ 售出並存檔"):
            # ... 存檔邏輯 (同前次提供內容) ...
            st.rerun()
