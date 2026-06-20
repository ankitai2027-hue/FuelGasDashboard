import streamlit as st
import pandas as pd

st.set_page_config(layout="wide") 
# =====================================================
# CONFIG
# =====================================================

FILE_NAME = "Fuel_Gas_Data.xlsx"

# Exact "Basic Data" sheet column names (from the uploaded Fuel_Gas_Data.xlsx)
MW_COL = "MW,gm/mol"
NCV_COL = "NCV,kcal/kg"
GCV_COL = "GCV,kcal/kg"

# =====================================================
# LOAD EXCEL SHEETS
# =====================================================

gas_df = pd.read_excel(
    FILE_NAME,
    sheet_name="Basic Data"
)

comp_df = pd.read_excel(
    FILE_NAME,
    sheet_name="Initial Composition"
)

# Remove accidental spaces in column names
gas_df.columns = gas_df.columns.str.strip()
comp_df.columns = comp_df.columns.str.strip()

# =====================================================
# VALIDATION
# =====================================================

if "Component" not in gas_df.columns:
    st.error("'Component' column not found in Basic Data sheet.")
    st.stop()

missing_basic_cols = [c for c in (MW_COL, NCV_COL, GCV_COL) if c not in gas_df.columns]

if missing_basic_cols:
    st.error(
        f"Column(s) {missing_basic_cols} not found in the 'Basic Data' sheet. "
        f"Available columns: {gas_df.columns.tolist()}"
    )
    st.stop()

required_comp_cols = ["Component", "Composition, Vol %"]

for col in required_comp_cols:
    if col not in comp_df.columns:
        st.error(
            f"'{col}' column not found in Initial Composition sheet."
        )
        st.stop()

# =====================================================
# LOOKUPS
# =====================================================

initial_comp = dict(
    zip(
        comp_df["Component"],
        comp_df["Composition, Vol %"]
    )
)

mw_lookup = dict(zip(gas_df["Component"], gas_df[MW_COL]))
ncv_lookup = dict(zip(gas_df["Component"], gas_df[NCV_COL]))
gcv_lookup = dict(zip(gas_df["Component"], gas_df[GCV_COL]))

gas_list = gas_df["Component"].tolist()


# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================

for gas in gas_list:

    default_value = float(
        initial_comp.get(gas, 0.0)
    )

    if f"{gas}_slider" not in st.session_state:
        st.session_state[f"{gas}_slider"] = default_value

    if f"{gas}_input" not in st.session_state:
        st.session_state[f"{gas}_input"] = default_value

# =====================================================
# RESET BUTTON
# =====================================================

if st.button("Reset to Initial Composition"):

    for gas in gas_list:

        value = float(
            initial_comp.get(gas, 0.0)
        )

        st.session_state[f"{gas}_slider"] = value
        st.session_state[f"{gas}_input"] = value

    st.rerun()

# =====================================================
# TITLE
# =====================================================

st.title("Fuel Gas Composition Dashboard")

# =====================================================
# COMPOSITION
# =====================================================


composition = {}

for gas in gas_list:
    composition[gas] = float(
        st.session_state[f"{gas}_slider"]
    )


# =====================================================
# TABLE HEADER
# =====================================================

header_labels = [
    "Component",
    "MW (gm/mol)",
    "NCV (kcal/kg)",
    "GCV (kcal/kg)",
    "Slider",
    "Vol%",
    "Wt%",
    "NCV Contribution",
    "GCV Contribution",
]

col_widths = [2, 2, 2, 2, 4, 2, 2, 2, 2]

header = st.columns(col_widths)

for idx, label in enumerate(header_labels):
    header[idx].markdown(f"**{label}**")
    
    
# =====================================================
# WEIGHT % AND CONTRIBUTIONS
# =====================================================
#
#   Wt%_i (fraction)     = (MW_i * Vol%_i) / SUMPRODUCT(MW, Vol%)
#   NCV Contribution_i   = NCV_i * Wt%_i
#   GCV Contribution_i   = GCV_i * Wt%_i 

sumproduct_mw_vol = sum(
mw_lookup[gas] * composition[gas]
for gas in gas_list
)

wt_frac = {}
ncv_contribution = {}
gcv_contribution = {}

for gas in gas_list:

    wt_frac[gas] = (
        (mw_lookup[gas] * composition[gas]) / sumproduct_mw_vol
        if sumproduct_mw_vol > 0 else 0.0
    )

    ncv_contribution[gas] = ncv_lookup[gas] * wt_frac[gas]
    gcv_contribution[gas] = gcv_lookup[gas] * wt_frac[gas]

# =====================================================
# EDITABLE COMPONENT ROWS
# =====================================================

for gas in gas_list:

    def update_input(g=gas):
        st.session_state[f"{g}_input"] = (
            st.session_state[f"{g}_slider"]
        )

    def update_slider(g=gas):
        st.session_state[f"{g}_slider"] = (
            st.session_state[f"{g}_input"]
        )

    row_cols = st.columns(col_widths)

    row_cols[0].write(gas)
    row_cols[1].write(mw_lookup[gas])
    row_cols[2].write(ncv_lookup[gas])
    row_cols[3].write(gcv_lookup[gas])

    # Slider
    with row_cols[4]:

        st.slider(
            label="",
            min_value=0.0,
            max_value=100.0,
            step=0.01,
            key=f"{gas}_slider",
            on_change=update_input,
            label_visibility="collapsed",
            format="%.3f"
        )

    # Manual Vol% input
    with row_cols[5]:

        st.number_input(
            label="",
            min_value=0.0,
            max_value=100.0,
            step=0.001,
            key=f"{gas}_input",
            on_change=update_slider,
            label_visibility="collapsed",
            format="%.3f"
        )

    row_cols[6].write(f"{wt_frac[gas] * 100:.2f}%")
    row_cols[7].write(f"{ncv_contribution[gas]:.2f}")
    row_cols[8].write(f"{gcv_contribution[gas]:.2f}")



# =====================================================
# TOTAL COMPOSITION CHECK
# =====================================================

total = sum(composition[gas] for gas in gas_list
)
valid_composition = (
    95 <= total <= 105
)

c1, c2 = st.columns([3, 1])

with c1:
    st.subheader("Total Composition")

with c2:
    st.metric(
        label="%",
        value=total
    )

if valid_composition:

    st.success(
        f"✓ Total Composition = {total}%"
    )

else:

    st.error(

        f"Total Composition = {total}%\n\n"

        "Composition should lie between "
        "95% and 105%."

    )

# =====================================================
# NCV, GCV, Wobbe Index Calculation
# =====================================================

#   Mixture NCV / GCV (kcal/kg)    = sum of all component contributions
#   Mixture NCV / GCV (kcal/nm3) = Mixture NCV / GCV (kcal/kg) *Avg MW /22.414
#   Mixture SG           = Mixture Avg MW/28.97 (*Air Molecular Weight = 28.97)
#   Mixture Wobbe Index NCV Basis  = Mixture NCV (kcal/nm3)/(SG)^0.5
#   Mixture Wobbe Index NCV Basis (MJ/nm3)  = Mixture Wobbe Index NCV Basis*4.184/1000
#   Mixture Wobbe Index GCV Basis  = Mixture GCV (kcal/nm3)/(SG)^0.5
#   Mixture Wobbe Index GCV Basis (MJ/nm3)  = Mixture Wobbe Index GCV Basis*4.184/1000

if valid_composition:



    mixture_avg_mw = sumproduct_mw_vol / 100  # g/mol
    mixture_SG = mixture_avg_mw/28.97

    #kcal/kg

    mixture_ncv_kcal_kg_total = sum(ncv_contribution.values())
    mixture_gcv_kcal_kg_total = sum(gcv_contribution.values())

    #kcal/nm3

    mixture_ncv_kcal_nm3_total = (mixture_ncv_kcal_kg_total*mixture_avg_mw)/22.414
    mixture_gcv_kcal_nm3_total = (mixture_gcv_kcal_kg_total*mixture_avg_mw)/22.414

    #WI NCV Basis

    mixture_WobbeIndex_ncv_kcal_nm3 = mixture_ncv_kcal_nm3_total/(mixture_SG)**0.5
    mixture_WobbeIndex_ncv_MJ_nm3 = mixture_WobbeIndex_ncv_kcal_nm3*4.184/1000

    #WI GCV Basis

    mixture_WobbeIndex_gcv_kcal_nm3 = mixture_gcv_kcal_nm3_total/(mixture_SG)**0.5
    mixture_WobbeIndex_gcv_MJ_Nm3 = mixture_WobbeIndex_gcv_kcal_nm3*4.184/1000

# =====================================================
# MIXTURE TOTALS
# =====================================================

if valid_composition:

    st.markdown("---")

    m1, m2 = st.columns(2)

    with m1:
        st.metric("Average MW (g/mol)", f"{mixture_avg_mw:.3f}")

    with m2:
        st.metric("Specific Gravity(SG) of Mixture", f"{mixture_SG:.3f}")


    st.markdown("---")

    m3, m4 = st.columns(2)

    with m3:
        st.metric("NCV, GCV")

    with m4:
        st.metric("Wobbe Index")

# =====================================================
# MIXTURE SUMMARY TABLE
# =====================================================

if valid_composition:

    st.markdown("---")

    summary_df = pd.DataFrame({

        "Basis": [
            "NCV",
            "GCV"
        ],

        "kcal/kg": [
            round(mixture_ncv_kcal_kg_total,3),
            round(mixture_gcv_kcal_kg_total,3)
        ],

        "kcal/Nm³": [
            round(mixture_ncv_kcal_nm3_total,3),
            round(mixture_gcv_kcal_nm3_total,3)
        ],

        "Basis": [
            "ncv_basis",
            "gcv_basis"
        ],

        "in kcal/Nm³": [
            round(mixture_WobbeIndex_ncv_kcal_nm3,3),
            round(mixture_WobbeIndex_gcv_kcal_nm3,3)
        ],

        "in MJ/Nm³": [
            round(mixture_WobbeIndex_ncv_MJ_nm3,3),
            round(mixture_WobbeIndex_gcv_MJ_Nm3,3)
        ]
    })

    st.subheader("Mixture Summary")

    st.dataframe(
        summary_df,
        use_container_width=True
    )

from io import BytesIO

# =====================================================
# EXPORT TABLE (same as dashboard, excluding slider)
# =====================================================

export_gas_df = pd.DataFrame({

    "Component": gas_list,

    "MW (gm/mol)": [
        round(mw_lookup[gas], 3)
        for gas in gas_list
    ],

    "NCV (kcal/kg)": [
        round(ncv_lookup[gas], 3)
        for gas in gas_list
    ],

    "GCV (kcal/kg)": [
        round(gcv_lookup[gas], 3)
        for gas in gas_list
    ],

    "Vol %": [
        round(composition[gas], 3)
        for gas in gas_list
    ],

    "Wt %": [
        round(wt_frac[gas] * 100, 3)
        for gas in gas_list
    ],

    "NCV Contribution": [
        round(ncv_contribution[gas], 3)
        for gas in gas_list
    ],

    "GCV Contribution": [
        round(gcv_contribution[gas], 3)
        for gas in gas_list
    ]
})

# =====================================================
# CREATE EXCEL FILE
# =====================================================

if valid_composition:
    output = BytesIO()

    from datetime import datetime

    today = datetime.now().strftime("%d%m%Y")


    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        sheet_name = f"Fuel_Gas_Results_{today}"

        # -----------------------------------------
        # GAS PROPERTY TABLE
        # -----------------------------------------

        export_gas_df.to_excel(
            writer,
            sheet_name=sheet_name,
            startrow=0,
            index=False
        )

    # -----------------------------------------
    # TOTAL COMPOSITION
    # -----------------------------------------
   

        total_row = len(export_gas_df) + 3 

        total_df = pd.DataFrame({

            "Parameter": [
                "Total Composition (%)"
            ],

            "Value": [
                round(total, 3)
            ]
        })

        total_df.to_excel(
            writer,
            sheet_name=sheet_name,
            startrow=total_row,
            index=False
        )

        # -----------------------------------------
        # MIXTURE PROPERTIES
        # -----------------------------------------

        mixture_row = total_row + len(total_df) + 3

        mixture_df = pd.DataFrame({

            "Parameter": [
                "Average MW (g/mol)",
                "Specific Gravity (SG)"
            ],

            "Value": [
                round(mixture_avg_mw, 3),
                round(mixture_SG, 3)
            ]
        })

        mixture_df.to_excel(
            writer,
            sheet_name=sheet_name,
            startrow=mixture_row,
            index=False
        )


        # -----------------------------------------
        # MIXTURE SUMMARY
        # -----------------------------------------

        summary_row = mixture_row + len(mixture_df) + 3

        summary_df.to_excel(
            writer,
            sheet_name=sheet_name,
            startrow=summary_row,
            index=False
        )

        output.seek(0)

# =====================================================
# DOWNLOAD BUTTON
# =====================================================

    st.markdown("---")

    st.download_button(
        label="📥 Export Results to Excel",
        data=output,
        file_name=f"Fuel_Gas_Results_{today}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


