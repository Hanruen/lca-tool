"""
工程材料碳足跡計算工具
Integrated Hybrid LCA — Streamlit 主程式
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import io
import logging

from core.calculator import HybridLCACalculator, Material, Product
from utils.data_loader import load_io_data, validate_io_data
from utils.exporter import export_to_excel, result_to_dataframes

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="碳足跡計算工具",
    page_icon="🌿",
    layout="wide",
)

st.title("🌿 工程材料碳足跡計算工具")
st.caption("Integrated Hybrid LCA")

EMPTY_ROW = lambda: {"name": "", "unit": "", "sector": 0, "qty": None, "price": None}

if "calculator" not in st.session_state:
    st.session_state.calculator = None
if "result" not in st.session_state:
    st.session_state.result = None
if "sector_options" not in st.session_state:
    st.session_state.sector_options = [f"{i+1:03d}" for i in range(163)]
if "raw_rows" not in st.session_state:
    st.session_state.raw_rows = [EMPTY_ROW()]
if "energy_rows" not in st.session_state:
    st.session_state.energy_rows = [EMPTY_ROW()]
if "widget_version" not in st.session_state:
    st.session_state.widget_version = 0

with st.sidebar:
    st.header("IO 資料庫")
    from utils.template_generator import create_io_template, create_userinput_template

    # ── ① 預設值 ────────────────────────────
    st.markdown("**① 使用預設值**")
    st.caption("台灣主計總處 110 年產業關聯表（163 部門）")
    if st.button("載入預設 IO 資料", use_container_width=True):
        try:
            import numpy as np_lib, json
            from pathlib import Path
            data_dir = Path(__file__).parent / "data"
            npz = np_lib.load(data_dir / "tw110_io.npz")
            with open(data_dir / "tw110_sectors.json", encoding="utf-8") as _f:
                sector_names = json.load(_f)
            A_matrix = npz["A"].astype(float)
            B_IO_vec = npz["B"].astype(float)
            st.session_state.calculator     = HybridLCACalculator(A_matrix, B_IO_vec, sector_names)
            st.session_state.sector_options = sector_names
            st.success(f"✓ 預設資料載入完成（{len(sector_names)} 部門）")
        except Exception as e:
            st.error(f"載入失敗：{e}")

    st.divider()

    # ── ② 上傳自訂 IO 資料（含下載範本）──────
    st.markdown("**② 上傳自訂 IO 資料**")
    st.download_button(
        label="⬇️ 下載 IO 填報範本",
        data=create_io_template(),
        file_name="IO填報範本.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    io_file = st.file_uploader("上傳填妥的 IO Excel（含 IO_A、B_IO、Sector）", type=["xlsx", "xls"], key="io_upload")
    if io_file:
        try:
            with st.spinner("讀取中..."):
                A_matrix, B_IO_vec, sector_names = load_io_data(io_file)
                warns = validate_io_data(A_matrix, B_IO_vec, sector_names)
            for w in warns:
                st.warning(w)
            st.session_state.calculator     = HybridLCACalculator(A_matrix, B_IO_vec, sector_names)
            st.session_state.sector_options = sector_names
            st.success(f"✓ 載入完成（{len(sector_names)} 部門）")
        except Exception as e:
            st.error(f"載入失敗：{e}")


def render_material_table(rows_key, prefix):
    rows = st.session_state[rows_key]
    v = st.session_state.widget_version

    col_add, col_clr, _ = st.columns([1, 1, 4])
    with col_add:
        if st.button("＋ 新增", use_container_width=True, key=f"{prefix}_add"):
            rows.append(EMPTY_ROW())
            st.rerun()
    with col_clr:
        if st.button("清除全部", use_container_width=True, key=f"{prefix}_clr"):
            st.session_state[rows_key] = [EMPTY_ROW()]
            st.rerun()

    h1, h2, h3, h4, h5, h6 = st.columns([2, 3, 1, 1.2, 1.5, 0.5])
    h1.markdown("**名稱**"); h2.markdown("**對應 IO 部門**"); h3.markdown("**單位**")
    h4.markdown("**數量**"); h5.markdown("**單價 ($NTD/單位)**"); h6.markdown("**刪除**")

    to_delete = []
    for idx, row in enumerate(rows):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 3, 1, 1.2, 1.5, 0.5])
        with c1:
            row["name"] = st.text_input("名稱", value=row["name"],
                label_visibility="collapsed", key=f"{prefix}_n{v}_{idx}")
        with c2:
            row["sector"] = st.selectbox("部門",
                range(len(st.session_state.sector_options)),
                format_func=lambda x: st.session_state.sector_options[x],
                index=min(row["sector"], len(st.session_state.sector_options) - 1),
                label_visibility="collapsed", key=f"{prefix}_s{v}_{idx}")
        with c3:
            row["unit"] = st.text_input("單位", value=row.get("unit", ""),
                label_visibility="collapsed", placeholder="單位",
                key=f"{prefix}_u{v}_{idx}")
        with c4:
            row["qty"] = st.number_input("數量", value=row["qty"],
                label_visibility="collapsed", placeholder="數量",
                key=f"{prefix}_q{v}_{idx}")
        with c5:
            row["price"] = st.number_input("單價", value=row["price"], min_value=0.0,
                label_visibility="collapsed", placeholder="單價",
                key=f"{prefix}_p{v}_{idx}")
        with c6:
            if st.button("✕", key=f"{prefix}_d{v}_{idx}", use_container_width=True):
                to_delete.append(idx)

    if to_delete:
        st.session_state[rows_key] = [
            r for i, r in enumerate(rows) if i not in to_delete
        ]
        st.rerun()


tab1, tab2, tab3 = st.tabs(["📋 輸入投入&產出資訊", "📊 計算結果", "🔍 明細"])

with tab1:

    # ── 匯入投入產出 Excel ──────────────────────
    with st.expander("📂 匯入投入產出 Excel", expanded=False):
        dl_col, up_col = st.columns(2)
        with dl_col:
            st.download_button(
                label="⬇️ 下載投入產出範本",
                data=create_userinput_template(),
                file_name="投入產出填報範本.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with up_col:
            upload_ui = st.file_uploader("上傳填妥的 Excel", type=["xlsx"], key="ui_upload")

        if upload_ui:
            try:
                from utils.data_loader import parse_user_input
                prod_imp, raw_imp, energy_imp = parse_user_input(upload_ui)
                n_prod = 1 if prod_imp else 0
                st.success(f"讀取到：產品 {n_prod} 項，原物料 {len(raw_imp)} 項，能資源 {len(energy_imp)} 項")
                if st.button("套用"):
                    if prod_imp:
                        # 產品資訊帶入 session state，讓介面顯示
                        st.session_state["imp_product"] = prod_imp
                    st.session_state.raw_rows = [
                        {"name": m.name, "unit": m.unit,
                         "sector": m.sector_id,
                         "qty": m.quantity, "price": m.price}
                        for m in raw_imp
                    ] or [EMPTY_ROW()]
                    st.session_state.energy_rows = [
                        {"name": m.name, "unit": m.unit,
                         "sector": m.sector_id,
                         "qty": m.quantity, "price": m.price}
                        for m in energy_imp
                    ] or [EMPTY_ROW()]
                    st.session_state.widget_version += 1
                    st.rerun()
            except Exception as e:
                st.error(f"匯入失敗：{e}")

    st.divider()
    st.subheader("產品資訊")

    # 若有匯入的產品資訊，帶入預設值
    imp_prod = st.session_state.get("imp_product", None)
    default_prod_name   = imp_prod["name"]    if imp_prod else "建設工程"
    default_prod_sector = imp_prod["sector"]  if imp_prod else 0
    default_prod_unit   = imp_prod["unit"]    if imp_prod else ""
    default_prod_qty    = imp_prod["qty"]     if imp_prod else 1.0
    default_prod_price  = imp_prod["price"]   if imp_prod else None

    v = st.session_state.widget_version
    c1, c2, c3, c4, c5 = st.columns([2, 3, 1, 1.2, 1.5])
    with c1:
        product_name = st.text_input("產品名稱", value=default_prod_name, key=f"prod_name_{v}")
    with c2:
        product_sector = st.selectbox(
            "對應 IO 部門",
            options=list(range(len(st.session_state.sector_options))),
            format_func=lambda x: st.session_state.sector_options[x],
            index=min(default_prod_sector, len(st.session_state.sector_options)-1),
            key=f"prod_sector_{v}",
        )
    with c3:
        product_unit = st.text_input("單位", value=default_prod_unit,
                                     placeholder="單位", key=f"prod_unit_{v}")
    with c4:
        product_qty = st.number_input("數量", min_value=0.0,
                                      value=float(default_prod_qty), key=f"prod_qty_{v}")
    with c5:
        product_price = st.number_input("單價 ($NTD/單位)", min_value=0.0,
                                        value=default_prod_price,
                                        placeholder="單價", step=1.0, key=f"prod_price_{v}")

    st.divider()
    st.subheader("原物料投入")
    render_material_table("raw_rows", "raw")

    st.divider()
    st.subheader("能資源投入")
    render_material_table("energy_rows", "energy")

    st.divider()
    if st.button("🚀 開始計算碳足跡", type="primary", use_container_width=True):
        if not st.session_state.calculator:
            st.error("請先在左側載入 IO 資料庫")
        else:
            all_rows = st.session_state.raw_rows + st.session_state.energy_rows
            valid = [r for r in all_rows if r["name"] and (r["qty"] or 0) >= 0 and (r["price"] or 0) >= 0]
            if not valid:
                st.error("請至少輸入一項有效材料")
            else:
                try:
                    with st.spinner("計算中..."):
                        product = Product(product_name, product_sector + 1, float(product_price or 0))
                        materials = [
                            Material(
                                name=r["name"],
                                sector_id=r["sector"] + 1,
                                quantity=float(r["qty"] or 0),
                                price=float(r["price"] or 0),
                                unit=r.get("unit", ""),
                            ) for r in valid
                        ]
                        result = st.session_state.calculator.calculate(materials, product)
                        result.n_raw = len([r for r in st.session_state.raw_rows if r["name"]])
                        st.session_state.result = result
                    st.success("✓ 計算完成！請切換至「計算結果」分頁")
                except Exception as e:
                    st.error(f"計算錯誤：{e}")

with tab2:
    if not st.session_state.result:
        st.info("尚未計算，請至「輸入材料」分頁完成設定")
    else:
        r = st.session_state.result
        n_raw = getattr(r, "n_raw", len(r.material_names))

        k1, k2, k3 = st.columns(3)
        k1.metric("總碳排放量", f"{r.total_emission:,.4f} kg CO₂e")
        k2.metric("PBLCA",
                  f"{r.process_total:,.4f} kg CO₂e",
                  f"佔總量 {r.process_total / r.total_emission * 100:.1f}%" if r.total_emission else "—",
                  delta_color="off")
        k3.metric("IOLCA",
                  f"{r.io_total:,.4f} kg CO₂e",
                  f"佔總量 {r.io_total / r.total_emission * 100:.1f}%" if r.total_emission else "—",
                  delta_color="off")

        st.divider()
        col_pie, col_tbl = st.columns([1.2, 1])
        with col_pie:
            fig = px.pie(
                names=["PBLCA", "IOLCA"],
                values=[r.process_total, r.io_total],
                title="碳排放來源比例",
                color_discrete_sequence=["#3B82F6", "#10B981"],
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_tbl:
            raw_names = r.material_names[:n_raw]
            raw_em    = r.material_emissions[:n_raw]
            eng_names = r.material_names[n_raw:]
            eng_em    = r.material_emissions[n_raw:]

            # Scope 1：產品（移至最上方）
            st.subheader("Scope 1 — 產品")
            st.dataframe(pd.DataFrame({
                "名稱": [r.product_name],
                "碳排放量 (kg CO₂e)": [round(r.product_emission, 6)],
            }), use_container_width=True, hide_index=True)
            st.caption(f"小計：{r.product_emission:,.4f} kg CO₂e")

            st.divider()

            # Scope 2：能資源投入
            st.subheader("Scope 2 — 能資源投入")
            if eng_names:
                st.dataframe(pd.DataFrame({
                    "名稱": eng_names,
                    "碳排放量 (kg CO₂e)": [round(float(e), 6) for e in eng_em],
                }), use_container_width=True, hide_index=True)
                st.caption(f"小計：{sum(float(e) for e in eng_em):,.4f} kg CO₂e")
            else:
                st.caption("無能資源投入")

            st.divider()

            # Scope 3：原物料投入 + IO 合計
            scope3_raw   = sum(float(e) for e in raw_em)
            scope3_io    = float(r.io_total)
            scope3_total = scope3_raw + scope3_io
            st.subheader("Scope 3 — 原物料投入 + IO 合計")
            if raw_names:
                st.dataframe(pd.DataFrame({
                    "名稱": raw_names,
                    "碳排放量 (kg CO₂e)": [round(float(e), 6) for e in raw_em],
                }), use_container_width=True, hide_index=True)
            else:
                st.caption("無原物料投入")
            st.caption(f"原物料小計：{scope3_raw:,.4f} kg CO₂e　｜　IO 供應鏈：{scope3_io:,.4f} kg CO₂e　｜　Scope 3 合計：{scope3_total:,.4f} kg CO₂e")

        st.divider()
        st.subheader(f"IOLCA 熱點（前 20 / {len(r.sector_names)} 部門）")
        _, hotspot = result_to_dataframes(r, top_n=20)
        fig2 = px.bar(
            hotspot.sort_values("碳排放量 (kg CO₂e)"),
            x="碳排放量 (kg CO₂e)", y="部門名稱", orientation="h",
            color="碳排放量 (kg CO₂e)", color_continuous_scale="Blues",
        )
        fig2.update_layout(yaxis_title="", coloraxis_showscale=False, height=500)
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        buf = io.BytesIO()
        export_to_excel(r, buf)
        buf.seek(0)
        st.download_button(
            "⬇️ 下載 Excel 報表", data=buf,
            file_name=f"{r.product_name}_碳足跡報表.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

with tab3:
    if not st.session_state.result:
        st.info("尚未計算")
    else:
        r = st.session_state.result
        summary, _ = result_to_dataframes(r)
        f1, f2, _ = st.columns([1, 1, 2])
        with f1:
            cats = st.multiselect("類別篩選", ["輸入材料", "產品", "IO 部門"],
                                  default=["輸入材料", "產品", "IO 部門"])
        with f2:
            sort_by = st.radio("排序", ["原始順序", "碳排放量大→小"], horizontal=True)

        df = summary[summary["類別"].isin(cats)].copy()
        if sort_by == "碳排放量大→小":
            df = df.sort_values("碳排放量 (kg CO₂e)", ascending=False)

        st.caption(f"共 {len(df)} 筆，非零 {(df['碳排放量 (kg CO₂e)'] != 0).sum()} 筆")
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"碳排放量 (kg CO₂e)": st.column_config.NumberColumn(format="%.6f")})
