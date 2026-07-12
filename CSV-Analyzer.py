import io
import re
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="CSV Explorer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CSV Explorer and Analyzer")
st.caption("Upload a CSV file, search it, inspect full rows, analyze columns, and build charts.")

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data
def load_csv(uploaded_file, encoding):
    return pd.read_csv(uploaded_file, encoding=encoding)

def build_search_series(df: pd.DataFrame) -> pd.Series:
    return df.astype(str).fillna("").agg(" | ".join, axis=1)

def detect_datetime_columns(df: pd.DataFrame):
    datetime_cols = []
    for col in df.columns:
        sample = df[col].dropna()
        if sample.empty:
            continue
        converted = pd.to_datetime(sample.head(200), errors="coerce", utc=True)
        if converted.notna().mean() > 0.6:
            datetime_cols.append(col)
    return datetime_cols

def convert_datetime_columns(df: pd.DataFrame, cols):
    out = df.copy()
    for col in cols:
        out[col] = pd.to_datetime(out[col], errors="coerce", utc=True)
    return out

def safe_numeric_df(df: pd.DataFrame):
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    return df[numeric_cols], numeric_cols

def text_column_candidates(df: pd.DataFrame):
    candidates = []
    for col in df.columns:
        if df[col].dtype == "object":
            candidates.append(col)
    return candidates

def keyword_frequency(df: pd.DataFrame, text_col: str, top_n: int = 20):
    text = (
        df[text_col]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"http\\S+", " ", regex=True)
        .str.replace(r"[^\\w\\s\\u0600-\\u06FF]", " ", regex=True)
        .str.replace(r"\\s+", " ", regex=True)
    )
    words = " ".join(text.tolist()).split()
    stop_words = {
        "the", "and", "for", "with", "this", "that", "from", "have", "you", "your",
        "الى", "على", "في", "من", "عن", "مع", "هذا", "هذه", "الى", "او", "أو", "ما",
        "تم", "هل", "ثم", "كل", "كان", "كما", "بعد", "قبل", "اذا", "إذا", "لا", "لم"
    }
    words = [w for w in words if len(w) > 2 and w not in stop_words]
    freq = pd.Series(words).value_counts().head(top_n)
    return freq

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.header("Upload")
uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])
encoding = st.sidebar.selectbox("Encoding", ["utf-8", "utf-8-sig", "cp1256", "latin1"], index=1)

if uploaded_file is None:
    st.info("Upload a CSV file from the sidebar to begin.")
    st.stop()

# -----------------------------
# Load data
# -----------------------------
try:
    df = load_csv(uploaded_file, encoding)
except Exception as e:
    st.error(f"Could not read the file: {e}")
    st.stop()

original_df = df.copy()

# Optional datetime conversion
datetime_candidates = detect_datetime_columns(df)
if datetime_candidates:
    selected_dt_cols = st.sidebar.multiselect(
        "Datetime columns to parse",
        options=datetime_candidates,
        default=[]
    )
    if selected_dt_cols:
        df = convert_datetime_columns(df, selected_dt_cols)

# -----------------------------
# Overview
# -----------------------------
st.subheader("Dataset overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", f"{df.shape[0]:,}")
c2.metric("Columns", f"{df.shape[1]:,}")
c3.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
dup_count = int(df.duplicated().sum())
c4.metric("Duplicate rows", f"{dup_count:,}")

with st.expander("Column information", expanded=False):
    info_df = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        "missing_pct": [round(df[c].isna().mean() * 100, 2) for c in df.columns],
        "unique_values": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })
    st.dataframe(info_df, use_container_width=True)

# -----------------------------
# Preview
# -----------------------------
st.subheader("Data preview")

preview_rows = st.slider("Preview rows", min_value=5, max_value=100, value=20, step=5)
st.dataframe(df.head(preview_rows), use_container_width=True)

# -----------------------------
# Search and row inspector
# -----------------------------
st.subheader("Search")

search_text = st.text_input("Search across all columns")
case_sensitive = st.checkbox("Case sensitive", value=False)
use_regex = st.checkbox("Use regex", value=False)

filtered_df = df.copy()

if search_text.strip():
    search_series = build_search_series(df)

    if use_regex:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            mask = search_series.str.contains(search_text, regex=True, na=False, flags=flags)
        except re.error as e:
            st.error(f"Invalid regex: {e}")
            st.stop()
    else:
        needle = search_text if case_sensitive else search_text.lower()
        haystack = search_series if case_sensitive else search_series.str.lower()
        mask = haystack.str.contains(re.escape(needle), regex=True, na=False)

    filtered_df = df[mask].copy()

st.write(f"Matching rows: **{len(filtered_df):,}**")
st.dataframe(filtered_df.head(200), use_container_width=True)

if not filtered_df.empty:
    st.markdown("### Full row viewer")
    row_index_options = filtered_df.index.tolist()
    selected_row_idx = st.selectbox("Choose a row index", row_index_options)
    selected_row = filtered_df.loc[selected_row_idx]

    row_display = pd.DataFrame({
        "column": selected_row.index,
        "value": selected_row.values
    })
    st.dataframe(row_display, use_container_width=True)

    row_json = selected_row.to_dict()
    with st.expander("Row as JSON", expanded=False):
        st.json(row_json)

# -----------------------------
# Filters
# -----------------------------
st.subheader("Filters")

filter_mode = st.radio("Choose filter mode", ["None", "Categorical", "Numeric range"], horizontal=True)

working_df = filtered_df.copy()

if filter_mode == "Categorical":
    cat_candidates = [c for c in working_df.columns if working_df[c].dtype == "object" or str(working_df[c].dtype).startswith("category")]
    if cat_candidates:
        cat_col = st.selectbox("Select categorical column", cat_candidates)
        unique_vals = working_df[cat_col].dropna().astype(str).unique().tolist()
        selected_vals = st.multiselect("Values", unique_vals, default=unique_vals[:10] if len(unique_vals) > 10 else unique_vals)
        if selected_vals:
            working_df = working_df[working_df[cat_col].astype(str).isin(selected_vals)]
    else:
        st.info("No categorical columns found.")

elif filter_mode == "Numeric range":
    numeric_df, numeric_cols = safe_numeric_df(working_df)
    if numeric_cols:
        num_col = st.selectbox("Select numeric column", numeric_cols)
        min_val = float(working_df[num_col].min())
        max_val = float(working_df[num_col].max())
        range_vals = st.slider("Range", min_value=min_val, max_value=max_val, value=(min_val, max_val))
        working_df = working_df[(working_df[num_col] >= range_vals[0]) & (working_df[num_col] <= range_vals[1])]
    else:
        st.info("No numeric columns found.")

st.write(f"Rows after filters: **{len(working_df):,}**")

# -----------------------------
# Analysis
# -----------------------------
st.subheader("Analysis")

tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Missing data", "Correlations", "Text analysis"])

with tab1:
    numeric_df, numeric_cols = safe_numeric_df(working_df)
    if numeric_cols:
        st.markdown("### Numeric summary")
        st.dataframe(working_df[numeric_cols].describe().T, use_container_width=True)
    else:
        st.info("No numeric columns available for summary statistics.")

    st.markdown("### Top values")
    top_col = st.selectbox("Choose a column for frequency counts", working_df.columns, key="top_col")
    vc = working_df[top_col].astype(str).value_counts(dropna=False).head(20)
    st.dataframe(vc.rename_axis("value").reset_index(name="count"), use_container_width=True)

with tab2:
    miss = pd.DataFrame({
        "column": working_df.columns,
        "missing_count": [int(working_df[c].isna().sum()) for c in working_df.columns],
        "missing_pct": [round(working_df[c].isna().mean() * 100, 2) for c in working_df.columns],
    }).sort_values("missing_count", ascending=False)

    st.dataframe(miss, use_container_width=True)

    miss_nonzero = miss[miss["missing_count"] > 0]
    if not miss_nonzero.empty:
        fig_miss = px.bar(
            miss_nonzero,
            x="column",
            y="missing_count",
            title="Missing values by column"
        )
        st.plotly_chart(fig_miss, use_container_width=True)
    else:
        st.success("No missing values found.")

with tab3:
    numeric_df, numeric_cols = safe_numeric_df(working_df)
    if len(numeric_cols) >= 2:
        corr = working_df[numeric_cols].corr(numeric_only=True)
        fig_corr = px.imshow(
            corr,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            title="Correlation matrix"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    else:
        st.info("Need at least two numeric columns for correlation analysis.")

with tab4:
    text_candidates = text_column_candidates(working_df)
    if text_candidates:
        text_col = st.selectbox("Choose text column", text_candidates)
        top_n_words = st.slider("Top words", 5, 50, 20)
        freq = keyword_frequency(working_df, text_col, top_n=top_n_words)

        if not freq.empty:
            freq_df = freq.reset_index()
            freq_df.columns = ["word", "count"]
            st.dataframe(freq_df, use_container_width=True)

            fig_words = px.bar(freq_df, x="word", y="count", title=f"Top words in {text_col}")
            st.plotly_chart(fig_words, use_container_width=True)
        else:
            st.info("No words available after cleaning.")
    else:
        st.info("No text columns found.")

# -----------------------------
# Visualization builder
# -----------------------------
st.subheader("Visualization")

chart_type = st.selectbox(
    "Chart type",
    ["Bar", "Line", "Scatter", "Histogram", "Box", "Pie"]
)

all_cols = working_df.columns.tolist()
numeric_df, numeric_cols = safe_numeric_df(working_df)

if chart_type in ["Bar", "Line", "Scatter"]:
    x_col = st.selectbox("X-axis", all_cols, key="x_axis")
    y_col = st.selectbox("Y-axis", numeric_cols if numeric_cols else all_cols, key="y_axis")
    color_col = st.selectbox("Color (optional)", ["None"] + all_cols, key="color_axis")

    color_arg = None if color_col == "None" else color_col

    if chart_type == "Bar":
        fig = px.bar(working_df, x=x_col, y=y_col, color=color_arg, title=f"{chart_type} chart")
    elif chart_type == "Line":
        fig = px.line(working_df, x=x_col, y=y_col, color=color_arg, title=f"{chart_type} chart")
    else:
        fig = px.scatter(working_df, x=x_col, y=y_col, color=color_arg, title=f"{chart_type} chart")

    st.plotly_chart(fig, use_container_width=True)

elif chart_type == "Histogram":
    hist_col = st.selectbox("Column", numeric_cols if numeric_cols else all_cols, key="hist_col")
    bins = st.slider("Bins", 5, 100, 20)
    fig = px.histogram(working_df, x=hist_col, nbins=bins, title="Histogram")
    st.plotly_chart(fig, use_container_width=True)

elif chart_type == "Box":
    y_col = st.selectbox("Numeric column", numeric_cols if numeric_cols else all_cols, key="box_y")
    x_group = st.selectbox("Group by (optional)", ["None"] + all_cols, key="box_x")
    if x_group == "None":
        fig = px.box(working_df, y=y_col, title="Box plot")
    else:
        fig = px.box(working_df, x=x_group, y=y_col, title="Box plot")
    st.plotly_chart(fig, use_container_width=True)

elif chart_type == "Pie":
    pie_col = st.selectbox("Category column", all_cols, key="pie_col")
    pie_counts = working_df[pie_col].astype(str).value_counts().reset_index()
    pie_counts.columns = [pie_col, "count"]
    fig = px.pie(pie_counts, names=pie_col, values="count", title="Pie chart")
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Downloads
# -----------------------------
st.subheader("Export")

csv_buffer = io.StringIO()
working_df.to_csv(csv_buffer, index=False)
st.download_button(
    label="Download filtered data as CSV",
    data=csv_buffer.getvalue(),
    file_name="filtered_data.csv",
    mime="text/csv"
)