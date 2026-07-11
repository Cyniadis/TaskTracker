import streamlit as st
import pandas as pd
import numpy as np

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode

# an example based on https://www.ag-grid.com/javascript-data-grid/component-cell-renderer/#simple-cell-renderer-example
BtnCellRenderer = JsCode(
    """
class BtnCellRenderer {
    init(params) {
        this.params = params;
        this.eGui = document.createElement('div');
        this.eGui.style.position = 'relative';  // To position elements within the cell
        if (String(this.params.value).includes('[clicked]')) {
            this.params.value = this.params.value.replace('[clicked]','');
            this.params.originalValue = this.params.value;
            this.makeButton('📍');
        } else {
            this.params.originalValue = this.params.value;
            this.makeButton('🔍');
        }
    }

    makeButton(symbol) {
        this.destroy();
        this.eGui.innerHTML = `
            <span id='click-button' style="position: absolute; left: 0; top: 50%; transform: translateY(-50%);">
                ${symbol}
            </span>
            <span style="margin-left: 24px;">${this.params.value}</span>`;
        this.eButton = this.eGui.querySelector('#click-button');
        this.btnClickedHandler = this.btnClickedHandler.bind(this);
        this.eButton.addEventListener('click', this.btnClickedHandler);
    }

    getGui() { return this.eGui; }

    refresh() { return true; }

    destroy() {
        if (this.eButton) { this.eGui.removeEventListener('click', this.btnClickedHandler); }
    }

    refreshTable(value) { this.params.setValue(value); }

    btnClickedHandler(event) {
        if(String(this.params.getValue()).includes('[clicked]')) {
            this.refreshTable(this.params.originalValue);
            this.makeButton('🔍');
        } else {
            this.refreshTable('[clicked]'+this.params.originalValue);
            this.makeButton('📍');
        }
    }
};
"""
)

def make_aggrid(df):
    df = df.copy()

    # casting to string wasn't needed for streamlit-aggrid<=0.3.4
    df = df.astype(str)

    gb = GridOptionsBuilder.from_dataframe(df)
    for field in [
        "col1",
        "col2",
    ]:
        gb.configure_column(field, cellRenderer=BtnCellRenderer)

    grid_options = gb.build()

    response = AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        try_to_convert_back_to_original_types=False,  # otherwise we lose [clicked] strings in numerical columns
        columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
        height=150,
    )
    return response

np.random.seed(42)
data = np.random.rand(5, 5)
columns = ["col1", "col2", "col3", "col4", "col5"]

df = pd.DataFrame(data, columns=columns)

st.subheader("AgGrid (click at least one 🔍)")
response = make_aggrid(df)

df = response["data"]
st.subheader("Raw output from AgGrid")
st.write(df)

result = []
for col in df.columns:
    for idx in df.index:
        if isinstance(df.at[idx, col], str) and df.at[idx, col].startswith("[clicked]"):
            result.append((col, idx))

st.subheader("Selected cells")
st.write(str(result))
