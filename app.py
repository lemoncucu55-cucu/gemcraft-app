# === Tab 3: 修改 (新增盤點紀錄功能) ===
    with tab3:
        st.markdown("##### 🛠️ 修正或盤點")
        if not st.session_state['inventory'].empty:
            edit_df = st.session_state['inventory'].copy()
            edit_df['label'] = edit_df.apply(make_inventory_label, axis=1)
            sel_label = st.selectbox("🔍 選擇要修改的商品", edit_df['label'].tolist())
            orig_row = edit_df[edit_df['label'] == sel_label].iloc[0]
            orig_idx = st.session_state['inventory'][st.session_state['inventory']['編號'] == orig_row['編號']].index[0]

            with st.form("edit_form"):
                st.info(f"編輯中：{orig_row['編號']}")
                ec1, ec2, ec3 = st.columns(3)
                with ec1: ename = st.text_input("名稱", value=orig_row['名稱'])
                with ec2: ewidth = st.number_input("寬度mm", value=float(orig_row['寬度mm']), step=0.1)
                with ec3: elength = st.number_input("長度mm", value=float(orig_row['長度mm']), step=0.1)

                shp_opts = get_dynamic_options('形狀', DEFAULT_SHAPES)
                elm_opts = get_dynamic_options('五行', DEFAULT_ELEMENTS)
                sup_opts = get_dynamic_options('進貨廠商', DEFAULT_SUPPLIERS)
                
                def get_eidx(opts, val):
                    try: return opts.index(val)
                    except: return 0

                ec4, ec5, ec6 = st.columns(3)
                current_shape = orig_row['形狀'] if '形狀' in orig_row else ''
                with ec4: eshp_sel = st.selectbox("形狀", shp_opts, index=get_eidx(shp_opts, current_shape))
                with ec5: eelm_sel = st.selectbox("五行", elm_opts, index=get_eidx(elm_opts, orig_row['五行']))
                with ec6: esup_sel = st.selectbox("廠商", sup_opts, index=get_eidx(sup_opts, orig_row['進貨廠商']))

                em1, em2, em3 = st.columns(3)
                eshape = em1.text_input("↳ 新形狀") if eshp_sel == "➕ 手動輸入/新增" else eshp_sel
                eelem = em2.text_input("↳ 新五行") if eelm_sel == "➕ 手動輸入/新增" else eelm_sel
                esup = em3.text_input("↳ 新廠商") if esup_sel == "➕ 手動輸入/新增" else esup_sel

                st.divider()
                ec7, ec8 = st.columns(2)
                # 這裡記錄原本的庫存，用來比對
                old_qty = int(orig_row['庫存(顆)'])
                with ec7: 
                    estock = st.number_input(f"庫存數量 (盤點前: {old_qty})", value=old_qty, step=1)
                with ec8: 
                    ecost = st.number_input("單顆成本", value=float(orig_row['單顆成本']), step=0.1, format="%.2f")

                # 計算差異 (新 - 舊)
                qty_diff = estock - old_qty
                if qty_diff != 0:
                    st.caption(f"⚠️ 庫存將調整: {qty_diff:+d} 顆")

                bt1, bt2 = st.columns([1, 1])
                with bt1:
                    if st.form_submit_button("💾 儲存修改 / 確認盤點"):
                        st.session_state['inventory'].at[orig_idx, '名稱'] = ename
                        st.session_state['inventory'].at[orig_idx, '寬度mm'] = ewidth
                        st.session_state['inventory'].at[orig_idx, '長度mm'] = elength
                        st.session_state['inventory'].at[orig_idx, '形狀'] = eshape
                        st.session_state['inventory'].at[orig_idx, '五行'] = eelm
                        st.session_state['inventory'].at[orig_idx, '進貨廠商'] = esup
                        st.session_state['inventory'].at[orig_idx, '庫存(顆)'] = estock
                        st.session_state['inventory'].at[orig_idx, '單顆成本'] = ecost
                        
                        # === 判斷是用於「盤點修正」還是單純「資料修改」 ===
                        if qty_diff != 0:
                            action_type = '盤點修正'
                            action_note = f"盤點調整 {qty_diff:+d}"
                        else:
                            action_type = '資料更新'
                            action_note = "修改資料內容"

                        log = {
                            '紀錄時間': datetime.now().strftime("%Y-%m-%d %H:%M"), 
                            '單號': 'AUDIT' if qty_diff != 0 else 'EDIT', 
                            '動作': action_type,
                            '編號': orig_row['編號'], '分類': orig_row['分類'], '名稱': ename,
                            '規格': f"{ewidth}x{elength}mm ({action_note})", 
                            '形狀': eshape,
                            '廠商': esup, 
                            '進貨數量': qty_diff, # 這裡會記錄 +5 或 -3
                            '進貨總價': 0, 
                            '單價': ecost
                        }
                        st.session_state['history'] = pd.concat([st.session_state['history'], pd.DataFrame([log])], ignore_index=True)
                        save_inventory()
                        
                        if qty_diff != 0:
                            st.success(f"✅ 盤點完成！庫存已修正 ({qty_diff:+d})")
                        else:
                            st.success("✅ 資料更新成功")
                            
                        time.sleep(1)
                        st.rerun()

                with bt2:
                    if st.form_submit_button("🗑️ 刪除商品", type="primary"):
                        st.session_state['inventory'] = st.session_state['inventory'].drop(orig_idx).reset_index(drop=True)
                        save_inventory()
                        st.success("已刪除")
                        time.sleep(1)
                        st.rerun()
        else: st.info("無資料")
