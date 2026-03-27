"""
╔══════════════════════════════════════════════════════════════╗
║     STREAMLIT + PANDAS TUTORIAL  —  Global Sales Dashboard  ║
║     Topics: DataFrames · Filtering · Charts · Pivot Tables  ║
╚══════════════════════════════════════════════════════════════╝

Run with:
    pip install streamlit pandas plotly numpy
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib  # required by pandas Styler.background_gradient()

# ─────────────────────────────────────────────
# PAGE CONFIG  (must be the FIRST st.* call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Sales Dashboard Tutorial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
# st.markdown("""
# <style>
#     /* Main background */
#     .main { background-color: #0f1117; }
#     .stApp { background-color: #0f1117; }

#     /* Metric cards */
#     [data-testid="metric-container"] {
#         background: linear-gradient(135deg, #1e2130 0%, #252a3a 100%);
#         border: 1px solid #2e3450;
#         border-radius: 12px;
#         padding: 16px;
#     }

#     /* Section headers */
#     .section-header {
#         font-size: 1.4rem;
#         font-weight: 700;
#         color: #e2e8f0;
#         border-left: 4px solid #6366f1;
#         padding-left: 12px;
#         margin: 24px 0 12px 0;
#     }

#     .tutorial-box {
#         background: #1a1f2e;
#         border: 1px solid #2e3450;
#         border-left: 4px solid #22d3ee;
#         border-radius: 8px;
#         padding: 16px 20px;
#         margin: 12px 0;
#         font-size: 0.88rem;
#         color: #94a3b8;
#         line-height: 1.7;
#     }

#     .tutorial-box code {
#         background: #0d1117;
#         color: #a5f3fc;
#         padding: 2px 6px;
#         border-radius: 4px;
#         font-family: 'Fira Code', monospace;
#     }

#     .tutorial-box b { color: #e2e8f0; }
# </style>
# """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
# ① CSV UPLOAD
# ══════════════════════════════════════════════

@st.cache
def load_csv(file_bytes: bytes) -> pd.DataFrame:
    """
    TUTORIAL NOTE ──────────────────────────────────────────────────────────────
    @st.cache (v1.12) / @st.cache_data (v1.18+) caches by argument value.
    We pass raw bytes (not the UploadedFile object) because bytes are hashable
    — Streamlit needs hashable arguments to cache correctly.
    The CSV is re-parsed only when the uploaded file actually changes.
    ─────────────────────────────────────────────────────────────────────────────
    """
    import io
    df = pd.read_csv(io.BytesIO(file_bytes))
    # Restore derived time columns in case they are missing
    df["Date"] = pd.to_datetime(df["Date"])
    if "Year"     not in df.columns: df["Year"]     = df["Date"].dt.year
    if "MonthNum" not in df.columns: df["MonthNum"]  = df["Date"].dt.month
    if "Month"    not in df.columns: df["Month"]     = df["Date"].dt.strftime("%b")
    if "Quarter"  not in df.columns: df["Quarter"]   = df["Date"].dt.quarter.apply(lambda q: f"Q{q}")
    return df.sort_values("Date").reset_index(drop=True)


# ── Upload dialog ─────────────────────────────────────────────────────────────
st.title("📊 Global Sales Intelligence Dashboard")
st.caption("A hands-on Streamlit + Pandas tutorial")

uploaded_file = st.file_uploader(
    "📂 Upload your CSV file to begin",
    type=["csv"],
    help="Upload the CSV you exported with df_full.to_csv('my_csv_file.csv', index=False)",
)

if uploaded_file is None:
    st.info("👆 Please upload a CSV file to load the dashboard.")
    st.stop()   # halt — nothing below runs until a file is provided

# Load and cache — pass bytes so the result is hashable for @st.cache
df_full = load_csv(uploaded_file.read())
st.success(f"✅ Loaded **{uploaded_file.name}** — {len(df_full):,} rows")


# ══════════════════════════════════════════════
# ② SIDEBAR — INTERACTIVE FILTERS
# ══════════════════════════════════════════════
with st.sidebar:
    st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=40)
    st.title("🎛️ Dashboard Filters")

    st.markdown("""
    <div class='tutorial-box'>
    <b>📘 Tutorial: Sidebar Widgets</b><br>
    <code>st.sidebar</code> is a context manager. Anything inside it renders
    in the collapsible left panel.<br><br>
    Widgets like <code>st.multiselect</code>, <code>st.slider</code>, and
    <code>st.date_input</code> return Python values you can use directly
    to filter your DataFrame.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── TUTORIAL NOTE ─────────────────────────
    # Bi-directional "Select All" pattern:
    # • "All" checked   → multiselect resets to full list (via session_state)
    # • "All" unchecked → multiselect stays populated; user deselects one by one
    # • "All" re-checked → multiselect resets to full list again
    # • Deselecting ANY item in multiselect → "All" checkbox auto-unchecks
    #
    # The trick for auto-unchecking: read the multiselect BEFORE rendering the
    # checkbox by storing its value in session_state, then compare against the
    # full list. If anything is missing, write False into the checkbox's key
    # before it renders — Streamlit picks that up on the same rerun.

    # ── TUTORIAL NOTE ─────────────────────────
    # Bi-directional "Select All" — final pattern:
    #
    # We track a separate "_prev" snapshot of what the multiselect held on the
    # PREVIOUS rerun. On each rerun we compare current vs previous:
    #   - If something was REMOVED and "All" is checked → auto-uncheck "All"
    #   - If "All" was just checked → restore full list into multiselect
    #   - Always update "_prev" to current at the end of the rerun
    #
    # This way re-checking "All" is always possible regardless of the current
    # multiselect state, because the auto-uncheck only reacts to a change in
    # the multiselect (removal of an item), not to its absolute value.

    # ── Year filter ──────────────────────────
    all_years = sorted(df_full["Year"].unique())
    _prev_years = st.session_state.get("ms_years_prev", all_years)
    _cur_years  = st.session_state.get("ms_years", all_years)
    # An item was removed from multiselect → auto-uncheck "All"
    if set(_cur_years) < set(_prev_years) and st.session_state.get("all_years_cb", True):
        st.session_state["all_years_cb"] = False
    all_years_cb = st.checkbox("All Years", value=True, key="all_years_cb")
    if all_years_cb:
        st.session_state["ms_years"] = all_years   # restore full list
    selected_years = st.multiselect(
        "📅 Year", options=all_years, default=all_years, key="ms_years",
    )
    st.session_state["ms_years_prev"] = st.session_state.get("ms_years", all_years)
    selected_years = all_years if all_years_cb else selected_years

    # ── Region filter ─────────────────────────
    all_regions = sorted(df_full["Region"].unique())
    _prev_regions = st.session_state.get("ms_regions_prev", all_regions)
    _cur_regions  = st.session_state.get("ms_regions", all_regions)
    if set(_cur_regions) < set(_prev_regions) and st.session_state.get("all_regions_cb", True):
        st.session_state["all_regions_cb"] = False
    all_regions_cb = st.checkbox("All Regions", value=True, key="all_regions_cb")
    if all_regions_cb:
        st.session_state["ms_regions"] = all_regions
    selected_regions = st.multiselect(
        "🌍 Region", options=all_regions, default=all_regions, key="ms_regions",
    )
    st.session_state["ms_regions_prev"] = st.session_state.get("ms_regions", all_regions)
    selected_regions = all_regions if all_regions_cb else selected_regions

    # ── Category filter ───────────────────────
    all_categories = sorted(df_full["Category"].unique())
    _prev_cats = st.session_state.get("ms_categories_prev", all_categories)
    _cur_cats  = st.session_state.get("ms_categories", all_categories)
    if set(_cur_cats) < set(_prev_cats) and st.session_state.get("all_cats_cb", True):
        st.session_state["all_cats_cb"] = False
    all_cats_cb = st.checkbox("All Categories", value=True, key="all_cats_cb")
    if all_cats_cb:
        st.session_state["ms_categories"] = all_categories
    selected_categories = st.multiselect(
        "🏷️ Category", options=all_categories, default=all_categories, key="ms_categories",
    )
    st.session_state["ms_categories_prev"] = st.session_state.get("ms_categories", all_categories)
    selected_categories = all_categories if all_cats_cb else selected_categories

    # ── Segment filter ────────────────────────
    all_segments = sorted(df_full["Segment"].unique())
    _prev_segs = st.session_state.get("ms_segments_prev", all_segments)
    _cur_segs  = st.session_state.get("ms_segments", all_segments)
    if set(_cur_segs) < set(_prev_segs) and st.session_state.get("all_segs_cb", True):
        st.session_state["all_segs_cb"] = False
    all_segs_cb = st.checkbox("All Segments", value=True, key="all_segs_cb")
    if all_segs_cb:
        st.session_state["ms_segments"] = all_segments
    selected_segments = st.multiselect(
        "🎯 Segment", options=all_segments, default=all_segments, key="ms_segments",
    )
    st.session_state["ms_segments_prev"] = st.session_state.get("ms_segments", all_segments)
    selected_segments = all_segments if all_segs_cb else selected_segments

    # ── Revenue range slider ──────────────────
    st.markdown("---")
    rev_min = float(df_full["Revenue"].min())
    rev_max = float(df_full["Revenue"].max())
    revenue_range = st.slider(
        "💰 Revenue Range ($)",
        min_value=rev_min,
        max_value=rev_max,
        value=(rev_min, rev_max),
        format="$%.0f",
    )

    # ── Won deals toggle ─────────────────────
    st.markdown("---")
    won_only = st.checkbox("🏆 Won Deals Only", value=False)
    st.caption(f"Total raw records: {len(df_full):,}")


# ══════════════════════════════════════════════
# ③ APPLY FILTERS  ← core pandas filtering
# ══════════════════════════════════════════════

"""
TUTORIAL NOTE ──────────────────────────────────────────────────────────────
Pandas boolean indexing: each condition returns a boolean Series.
Chain them with & (AND) / | (OR).  Always wrap conditions in parentheses!

    df[  (df["col"] == value) & (df["other"].isin(list))  ]
─────────────────────────────────────────────────────────────────────────────
"""

df = df_full[
    (df_full["Year"].isin(selected_years))
    & (df_full["Region"].isin(selected_regions))
    & (df_full["Category"].isin(selected_categories))
    & (df_full["Segment"].isin(selected_segments))
    & (df_full["Revenue"].between(*revenue_range))
].copy()   # .copy() ensures df is fully independent from df_full.
           # Without it, df is a view — mutations anywhere (even in a
           # display_df derived from df) can silently corrupt df_full
           # across Streamlit reruns, turning numeric columns into strings.

if won_only:
    df = df[df["Deal_Won"] == True].copy()

# ══════════════════════════════════════════════
# ④ EMPTY FILTER GUARD
# ══════════════════════════════════════════════
if df.empty:
    st.warning("⚠️ No data matches the current filters. Please adjust the sidebar.")
    st.stop()          # ← halts execution of the rest of the script

# ══════════════════════════════════════════════
# ⑤ KPI METRIC CARDS
# ══════════════════════════════════════════════
st.markdown("<div class='section-header'>⚡ Key Performance Indicators</div>", unsafe_allow_html=True)

st.markdown("""
<div class='tutorial-box'>
<b>📘 Tutorial: st.metric()</b><br>
<code>st.metric(label, value, delta)</code> renders a KPI card.
<code>delta</code> shows a green ↑ or red ↓ arrow automatically.
Use <code>st.columns(n)</code> to lay out widgets side-by-side.
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

total_rev    = df["Revenue"].sum()
total_profit = df["Profit"].sum()
avg_margin   = df["Margin_%"].mean()
total_deals  = len(df)
win_rate     = df["Deal_Won"].mean() * 100

# Compare against full dataset for delta
full_rev = df_full["Revenue"].sum()

col1.metric("Total Revenue",  f"${total_rev/1e6:.2f}M",  f"{((total_rev/full_rev)-1)*100:.1f}% of total")
col2.metric("Total Profit",   f"${total_profit/1e6:.2f}M")
col3.metric("Avg Margin",     f"{avg_margin:.1f}%")
col4.metric("Deals",          f"{total_deals:,}")
col5.metric("Win Rate",       f"{win_rate:.1f}%")


# ══════════════════════════════════════════════
# ⑥ DYNAMIC CHARTS  (user-controlled via dropdowns)
# ══════════════════════════════════════════════
st.markdown("<div class='section-header'>📈 Dynamic Charts</div>", unsafe_allow_html=True)

st.markdown("""
<div class='tutorial-box'>
<b>📘 Tutorial: Reactive Widgets</b><br>
Every time a widget changes, Streamlit <b>reruns the entire script</b> top-to-bottom.
The selected widget values are used as variables — no callbacks needed!<br><br>
<code>st.selectbox</code> returns the selected string.
<code>st.radio</code> returns the selected option.
Plotly figures are rendered with <code>st.plotly_chart(fig, use_container_width=True)</code>.
</div>
""", unsafe_allow_html=True)

# ── Row 1: Bar + Line ─────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.subheader("Bar Chart — Revenue Breakdown")
    bar_group = st.selectbox(
        "Group by",
        ["Category", "Region", "Segment", "Channel", "Year", "Quarter"],
        key="bar_group",
    )
    bar_metric = st.radio(
        "Metric",
        ["Revenue", "Profit", "Units"],
        horizontal=True,
        key="bar_metric",
    )
    bar_df = (
        df.groupby(bar_group)[bar_metric]
        .sum()
        .reset_index()
        .sort_values(bar_metric, ascending=False)
        .reset_index(drop=True)   # ← drop the old positional index after sorting;
                                  #   without this, older Plotly reads the stale
                                  #   index (0,1,2…) as the y-axis values instead
                                  #   of the actual metric.
    )
    # Use go.Bar directly with a list of per-bar colors.
    # px.bar(color=bar_group) creates one trace per category which breaks on
    # older Plotly — bars become invisible. go.Bar with marker_color as a list
    # is a single trace and works reliably across all versions.
    _palette = ["#7F3C8D","#11A579","#3969AC","#F2B701","#E73F74",
                "#80BA5A","#E68310","#008695","#CF1C90","#f97b72"]
    _colors = [_palette[i % len(_palette)] for i in range(len(bar_df))]
    bar_orientation = st.radio(
        "Orientation", ["Vertical", "Horizontal"], horizontal=True, key="bar_orient"
    )
    if bar_orientation == "Horizontal":
        # Horizontal: categories on y-axis, values on x-axis.
        # Reverse sort so the largest bar appears at the top.
        bar_df_plot = bar_df.sort_values(bar_metric, ascending=False).reset_index(drop=True)
        _colors_plot = _colors
        _hx_vals = bar_df_plot[bar_metric].tolist()  # pure Python list — no pandas/numpy
        _hy_vals = bar_df_plot[bar_group].tolist()
        fig_bar = go.Figure(go.Bar(
            x=_hx_vals,
            y=_hy_vals,
            orientation="h",
            marker_color=_colors_plot,
            hovertemplate=f"<b>%{{y}}</b><br>{bar_metric}: %{{x:,.0f}}<extra></extra>",
        ))
        fig_bar.update_layout(
            xaxis_title=bar_metric,
            xaxis=dict(
                type="linear",
                range=[0, max(_hx_vals) * 1.15],
                tickformat=",.0f",
            ),
            yaxis_title=bar_group,
            yaxis=dict(type="category"),
        )
    else:
        # Vertical (default): categories on x-axis, values on y-axis.
        _x_vals = bar_df[bar_group].tolist()[::-1]    # reverse so highest bar is leftmost
        _y_vals = bar_df[bar_metric].tolist()[::-1]   # (Plotly renders left-to-right)
        fig_bar = go.Figure(go.Bar(
            x=_x_vals,
            y=_y_vals,
            marker_color=_colors,
            hovertemplate=f"<b>%{{x}}</b><br>{bar_metric}: %{{y:,.0f}}<extra></extra>",
        ))
        fig_bar.update_layout(
            xaxis_title=bar_group,
            xaxis=dict(type="category"),
            yaxis_title=bar_metric,
            yaxis=dict(
                type="linear",
                range=[0, max(_y_vals) * 1.15],  # explicit range — Plotly cannot
                tickformat=",.0f",                # misread scale or collapse to 0-4
            ),
        )
    fig_bar.update_layout(
        title=f"{bar_metric} by {bar_group}",
        template="plotly_dark",
        showlegend=False,
        plot_bgcolor="#1e2130",
        paper_bgcolor="#1e2130",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.subheader("Time-Series Line Chart")
    line_metric = st.selectbox(
        "Metric",
        ["Revenue", "Profit", "Units", "Margin_%"],
        key="line_metric",
    )
    line_color = st.selectbox(
        "Color dimension",
        ["Category", "Region", "Segment", "Channel"],
        key="line_color",
    )
    line_freq = st.radio(
        "Granularity",
        ["Monthly", "Quarterly"],
        horizontal=True,
        key="line_freq",
    )

    freq_col = "Quarter" if line_freq == "Quarterly" else "Month"

    if line_freq == "Monthly":
        # Build a proper sort key: Year-MonthNum
        line_df = (
            df.groupby(["Year", "MonthNum", "Month", line_color])[line_metric]
            .sum()
            .reset_index()
        )
        line_df["Period"] = line_df["Year"].astype(str) + "-" + line_df["MonthNum"].astype(str).str.zfill(2)
        line_df = line_df.sort_values("Period")
    else:
        line_df = (
            df.groupby(["Year", "Quarter", line_color])[line_metric]
            .sum()
            .reset_index()
        )
        line_df["Period"] = line_df["Year"].astype(str) + " " + line_df["Quarter"]
        line_df = line_df.sort_values(["Year", "Quarter"])

    # Use go.Scatter with one trace per group — avoids older Plotly's
    # ordinal-index bug that px.line(color=col) triggers when it creates
    # multiple traces. Each trace gets sorted Period strings on x and
    # plain Python floats on y via .tolist().
    _line_palette = px.colors.qualitative.Vivid
    _line_groups  = sorted(line_df[line_color].unique().tolist())
    fig_line = go.Figure()
    for i, grp in enumerate(_line_groups):
        _grp_df = line_df[line_df[line_color] == grp].sort_values("Period")
        fig_line.add_trace(go.Scatter(
            x=_grp_df["Period"].tolist(),
            y=_grp_df[line_metric].tolist(),
            mode="lines+markers",
            name=str(grp),
            line=dict(color=_line_palette[i % len(_line_palette)], width=2),
            marker=dict(size=5),
            hovertemplate=f"<b>{grp}</b><br>%{{x}}<br>{line_metric}: %{{y:,.1f}}<extra></extra>",
        ))
    fig_line.update_layout(
        title=f"{line_metric} over Time by {line_color}",
        template="plotly_dark",
        plot_bgcolor="#1e2130",
        paper_bgcolor="#1e2130",
        xaxis=dict(type="category", tickangle=-35),
        yaxis=dict(type="linear", tickformat=",.0f"),
        legend=dict(orientation="h", y=-0.25),
        hovermode="x unified",
    )
    st.plotly_chart(fig_line, use_container_width=True)


# ── Row 2: Scatter + Treemap ──────────────────
c3, c4 = st.columns(2)

with c3:
    st.subheader("Scatter Plot — Revenue vs Profit")
    scatter_color = st.selectbox(
        "Color by",
        ["Category", "Segment", "Region", "Channel"],
        key="scatter_color",
    )
    scatter_size = st.selectbox(
        "Bubble size",
        ["Units", "Revenue", "Profit"],
        key="scatter_size",
    )
    # Sample for performance
    scatter_df = df.sample(min(500, len(df)), random_state=1)
    fig_scatter = px.scatter(
        scatter_df,
        x="Revenue",
        y="Profit",
        color=scatter_color,
        size=scatter_size,
        hover_data=["Product", "Country", "Sales_Rep"],
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title=f"Revenue vs Profit  (colored by {scatter_color})",
        opacity=0.75,
    )
    fig_scatter.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130")
    st.plotly_chart(fig_scatter, use_container_width=True)

with c4:
    st.subheader("Treemap — Hierarchical Revenue")
    tree_metric = st.selectbox(
        "Size metric",
        ["Revenue", "Profit", "Units"],
        key="tree_metric",
    )
    fig_tree = px.treemap(
        df,
        path=["Region", "Category", "Segment"],
        values=tree_metric,
        color=tree_metric,
        color_continuous_scale="Tealgrn",
        template="plotly_dark",
        title=f"Treemap: {tree_metric} by Region → Category → Segment",
    )
    fig_tree.update_layout(paper_bgcolor="#1e2130")
    st.plotly_chart(fig_tree, use_container_width=True)


# ── Row 3: Box plot ───────────────────────────
st.subheader("Box Plot — Margin Distribution")
box_x = st.selectbox(
    "X-axis grouping",
    ["Category", "Segment", "Channel", "Region", "Year"],
    key="box_x",
)
fig_box = px.box(
    df,
    x=box_x,
    y="Margin_%",
    color=box_x,
    points="outliers",
    template="plotly_dark",
    color_discrete_sequence=px.colors.qualitative.Antique,
    title=f"Margin % Distribution by {box_x}",
)
fig_box.update_layout(plot_bgcolor="#1e2130", paper_bgcolor="#1e2130", showlegend=False)
st.plotly_chart(fig_box, use_container_width=True)


# ── Row 4: Profit over Time line plot ─────────
st.subheader("📉 Aggregated Profit over Time")

st.markdown("""
<div class='tutorial-box'>
<b>📘 Tutorial: Time-axis aggregation with cumulative option</b><br>
We use <code>df.resample()</code> (after <code>.set_index("Date")</code>) or
<code>df.groupby(pd.Grouper(key="Date", freq=...))</code> to bucket rows into
regular time intervals — daily, weekly, monthly, or quarterly.<br><br>
• <code>pd.Grouper(freq="ME")</code>  — month-end buckets<br>
• <code>pd.Grouper(freq="QE")</code>  — quarter-end buckets<br>
• <code>.cumsum()</code>              — running total over the sorted series<br>
• <code>go.Figure + add_trace()</code> — overlay bars + line on one Plotly figure
</div>
""", unsafe_allow_html=True)

profit_col1, profit_col2, profit_col3 = st.columns(3)

with profit_col1:
    profit_freq = st.radio(
        "Time granularity",
        ["Daily", "Weekly", "Monthly", "Quarterly"],
        index=2,
        horizontal=True,
        key="profit_freq",
    )

with profit_col2:
    profit_breakdown = st.selectbox(
        "Color breakdown (optional)",
        ["None", "Category", "Region", "Segment", "Channel"],
        key="profit_breakdown",
    )

with profit_col3:
    show_cumulative = st.checkbox("Show cumulative profit", value=False, key="profit_cumul")

# Map UI label -> pandas freq alias
freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "ME", "Quarterly": "QE"}
freq_alias = freq_map[profit_freq]

if profit_breakdown == "None":
    # Simple aggregation: resample by chosen frequency
    profit_ts = (
        df.set_index("Date")
        .resample(freq_alias)["Profit"]
        .sum()
        .reset_index()
    )
    profit_ts.columns = ["Date", "Profit"]

    if show_cumulative:
        profit_ts["CumulativeProfit"] = profit_ts["Profit"].cumsum()
        y_col, y_label = "CumulativeProfit", "Cumulative Profit ($)"
    else:
        y_col, y_label = "Profit", "Profit ($)"

    # Overlay: semi-transparent bars for period profit + line for trend/cumulative
    fig_profit = go.Figure()
    fig_profit.add_trace(go.Bar(
        x=profit_ts["Date"],
        y=profit_ts["Profit"],
        name="Period Profit",
        marker_color="#6366f1",
        opacity=0.50,
    ))
    fig_profit.add_trace(go.Scatter(
        x=profit_ts["Date"],
        y=profit_ts[y_col],
        name=y_label,
        mode="lines+markers",
        line=dict(color="#22d3ee", width=2.5),
        marker=dict(size=5),
    ))
    fig_profit.update_layout(
        title=f"{'Cumulative' if show_cumulative else 'Aggregated'} Profit — {profit_freq}",
        xaxis_title="Date",
        yaxis_title="Profit ($)",
        template="plotly_dark",
        plot_bgcolor="#1e2130",
        paper_bgcolor="#1e2130",
        legend=dict(orientation="h", y=1.08),
        hovermode="x unified",
        barmode="overlay",
    )

else:
    # Breakdown by chosen dimension using pd.Grouper
    profit_ts = (
        df.groupby([pd.Grouper(key="Date", freq=freq_alias), profit_breakdown])["Profit"]
        .sum()
        .reset_index()
    )
    if show_cumulative:
        profit_ts = profit_ts.sort_values("Date")
        profit_ts["Profit"] = profit_ts.groupby(profit_breakdown)["Profit"].cumsum()

    fig_profit = px.line(
        profit_ts,
        x="Date",
        y="Profit",
        color=profit_breakdown,
        markers=True,
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Bold,
        title=f"{'Cumulative' if show_cumulative else 'Aggregated'} Profit by {profit_breakdown} — {profit_freq}",
    )
    fig_profit.update_layout(
        plot_bgcolor="#1e2130",
        paper_bgcolor="#1e2130",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08),
    )
    fig_profit.update_traces(line_width=2, marker_size=4)

st.plotly_chart(fig_profit, use_container_width=True)


# ══════════════════════════════════════════════
# ⑦ PIVOT TABLES
# ══════════════════════════════════════════════
st.markdown("<div class='section-header'>🔄 Pivot Tables</div>", unsafe_allow_html=True)

st.markdown("""
<div class='tutorial-box'>
<b>📘 Tutorial: pd.pivot_table()</b><br>
<code>pd.pivot_table(df, values, index, columns, aggfunc)</code><br><br>
• <b>values</b> — the column to aggregate (Revenue, Profit …)<br>
• <b>index</b>  — rows of the pivot<br>
• <b>columns</b> — columns of the pivot<br>
• <b>aggfunc</b> — 'sum', 'mean', 'count', np.median, etc.<br>
• <b>margins=True</b> adds row/column totals automatically<br><br>
<code>st.dataframe()</code> renders an interactive table with sorting.
Use <code>.style.background_gradient()</code> for heatmap colouring.
</div>
""", unsafe_allow_html=True)

pv_col1, pv_col2, pv_col3, pv_col4 = st.columns(4)

with pv_col1:
    pivot_rows = st.selectbox("Pivot Rows",    ["Region", "Category", "Segment", "Channel", "Year", "Quarter"], index=0)
with pv_col2:
    pivot_cols = st.selectbox("Pivot Columns", ["Category", "Region", "Segment", "Channel", "Year", "Quarter"], index=1)
with pv_col3:
    pivot_val  = st.selectbox("Values",        ["Revenue", "Profit", "Units", "Margin_%"], index=0)
with pv_col4:
    pivot_agg  = st.selectbox("Aggregation",   ["sum", "mean", "count", "median", "max"])

agg_fn = {"sum": "sum", "mean": "mean", "count": "count",
           "median": np.median, "max": "max"}[pivot_agg]

if pivot_rows == pivot_cols:
    st.warning("⚠️ Rows and Columns must be different dimensions.")
else:
    pivot_table = pd.pivot_table(
        df,
        values=pivot_val,
        index=pivot_rows,
        columns=pivot_cols,
        aggfunc=agg_fn,
        margins=True,           # adds "All" totals
        margins_name="TOTAL",
        fill_value=0,
    )

    # Round for display
    if pivot_val in ["Revenue", "Profit"]:
        pivot_display = pivot_table.applymap(lambda x: f"${x:,.0f}")
    elif pivot_val == "Margin_%":
        pivot_display = pivot_table.applymap(lambda x: f"{x:.1f}%")
    else:
        pivot_display = pivot_table.applymap(lambda x: f"{int(x):,}")

    # Styled numeric version for gradient (drop TOTAL row/col for the gradient)
    pivot_numeric = pivot_table.iloc[:-1, :-1]  # exclude margins
    styled = (
        pivot_numeric
        .style
        .background_gradient(cmap="YlOrRd", axis=None)
        .format(lambda x: f"${x:,.0f}" if pivot_val in ["Revenue","Profit"]
                          else (f"{x:.1f}%" if pivot_val == "Margin_%" else f"{int(x):,}"))
    )

    st.dataframe(styled)
    st.caption(f"Pivot: {pivot_agg}({pivot_val}) — {pivot_rows} × {pivot_cols} — {len(pivot_table)-1} row groups")


# ── Heatmap version of the pivot ──────────────
st.subheader("Pivot as Plotly Heatmap")

st.markdown("""
<div class='tutorial-box'>
<b>📘 Tutorial: Plotly Heatmap from Pivot</b><br>
Convert a pivot table to a <code>px.imshow()</code> heatmap for richer visuals.
<code>.values</code> extracts the numpy array; row/col labels come from
<code>.index</code> and <code>.columns</code>.
</div>
""", unsafe_allow_html=True)

if pivot_rows != pivot_cols:
    heat_data = pivot_table.iloc[:-1, :-1]   # drop margins
    fig_heat = px.imshow(
        heat_data,
        color_continuous_scale="Viridis",
        template="plotly_dark",
        title=f"Heatmap: {pivot_agg}({pivot_val}) — {pivot_rows} × {pivot_cols}",
        aspect="auto",
        text_auto=True,
    )
    fig_heat.update_layout(paper_bgcolor="#1e2130")
    st.plotly_chart(fig_heat, use_container_width=True)


# ══════════════════════════════════════════════
# ⑧ FILTERED DATA TABLE
# ══════════════════════════════════════════════
st.markdown("<div class='section-header'>🗂️ Filtered Data Explorer</div>", unsafe_allow_html=True)

st.markdown("""
<div class='tutorial-box'>
<b>📘 Tutorial: st.dataframe()</b><br>
• <code>st.dataframe(df)</code>  — read-only, sortable, searchable table<br>
• Pre-format columns in Python before passing to <code>st.dataframe()</code><br>
• In Streamlit ≥1.23 you can use <code>st.column_config</code> for richer formatting<br>
• <code>df.to_csv(index=False).encode()</code> — convert to bytes for download
</div>
""", unsafe_allow_html=True)

display_cols = st.multiselect(
    "Choose columns to display",
    options=df.columns.tolist(),
    default=df.columns.tolist(), # to see all columns by default!
    # default=["Date", "Region", "Country", "Category", "Product",
             # "Segment", "Revenue", "Profit", "Margin_%", "Deal_Won"],
)

n_rows = st.slider("Rows to preview", 10, 200, 50, step=10)

if display_cols:
    # v1.12 compatible: plain st.dataframe — no column_config, no use_container_width
    # Format numeric columns before display for readability
    display_df = df[display_cols].head(n_rows).copy()
    if "Revenue" in display_df.columns:
        display_df["Revenue"] = display_df["Revenue"].apply(lambda x: f"${x:,.0f}")
    if "Profit" in display_df.columns:
        display_df["Profit"] = display_df["Profit"].apply(lambda x: f"${x:,.0f}")
    if "Margin_%" in display_df.columns:
        display_df["Margin_%"] = display_df["Margin_%"].apply(lambda x: f"{x:.1f}%")
    if "Cost" in display_df.columns:
        display_df["Cost"] = display_df["Cost"].apply(lambda x: f"${x:,.0f}")
    if "Date" in display_df.columns:
        display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df)

# ── Download button ───────────────────────────
st.download_button(
    label="⬇️ Download filtered data as CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_sales_data.csv",
    mime="text/csv",
)


# ══════════════════════════════════════════════
# ⑨ SUMMARY STATS EXPANDER
# ══════════════════════════════════════════════
with st.expander("📋 Descriptive Statistics  (df.describe())"):
    st.markdown("""
    <div class='tutorial-box'>
    <b>📘 Tutorial: st.expander()</b><br>
    Wrap any content in <code>with st.expander("title"):</code> to make it
    collapsible. Great for secondary information that clutters the main view.
    </div>
    """, unsafe_allow_html=True)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    st.dataframe(df[numeric_cols].describe().round(2))


# ══════════════════════════════════════════════
# ⑩ FOOTER
# ══════════════════════════════════════════════
st.markdown("---")
st.caption(
    "Tutorial app · Streamlit + Pandas · "
    f"Showing {len(df):,} of {len(df_full):,} records  |  "
    f"Built with ❤️ using streamlit, pandas, plotly, numpy"
)
