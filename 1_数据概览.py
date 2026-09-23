"""
模块一 · 数据概览
==================
标准化商品数据库的全景分析：
    1. 数据清洗漏斗 —— 展示原始数据到标准化数据的四步清洗过程
    2. 核心 KPI 卡片 —— 商品总数、品牌数量、平均糖含量、平均蛋白质
    3. 直方图         —— 五大营养指标的分布情况
    4. 箱线图         —— 五大营养指标的离散程度与异常值
    5. 品牌对比       —— 各品牌平均营养水平对比表与柱状图
"""

import sys
from pathlib import Path

# 把项目根目录加入模块搜索路径，保证能导入 core 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.data_loader import get_clean_data

# ---------- 页面配置 ----------
st.set_page_config(page_title="数据概览 · FoodInsight", layout="wide")

# ---------- 加载数据 ----------
df, clean_log = get_clean_data()

st.title("数据概览")
st.caption("酸奶品类标准化数据库全景分析 ｜ 数据来源：OpenFoodFacts（模拟）")

# ---------- 五大营养指标的统一配置 ----------
# (字段名, 中文名, 单位, 图表颜色)
METRICS = [
    ("sugar", "糖含量", "g/100g", "#F59E0B"),
    ("fat", "脂肪", "g/100g", "#DC2626"),
    ("protein", "蛋白质", "g/100g", "#16A34A"),
    ("sodium", "钠", "mg/100g", "#0EA5E9"),
    ("energy", "能量", "kcal/100g", "#7C3AED"),
]

# ============================================================
# 1. 数据清洗漏斗（展示从原始数据到标准化数据的全过程）
# ============================================================
with st.expander("数据清洗流程：原始数据 → 标准化数据库", expanded=False):
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.metric("原始数据", f"{clean_log['原始数据量']} 条")
    f2.metric("品类筛选后", f"{clean_log['品类筛选后']} 条")
    f3.metric("缺失值删除", f"-{clean_log['缺失值删除']} 条")
    f4.metric("异常值删除", f"-{clean_log['异常值删除']} 条")
    f5.metric("最终入库", f"{clean_log['最终数据量']} 条")
    st.caption(
        "清洗步骤：① 品类筛选（只保留酸奶）→ ② 单位统一（"
        + clean_log["单位统一"]
        + "）→ ③ 缺失值处理 → ④ 异常值过滤"
    )

# ============================================================
# 2. 核心 KPI 卡片
# ============================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("商品总数", f"{len(df)} 款")
c2.metric("品牌数量", f"{df['brand'].nunique()} 个")
c3.metric("平均糖含量", f"{df['sugar'].mean():.1f} g/100g")
c4.metric("平均蛋白质", f"{df['protein'].mean():.1f} g/100g")

st.divider()

# ============================================================
# 3. 直方图：五大营养指标分布
# ============================================================
st.subheader("营养指标分布直方图")

# 前四个指标用 2×2 网格排列
hist_cols = st.columns(2)
for i, (key, name, unit, color) in enumerate(METRICS[:4]):
    with hist_cols[i % 2]:
        fig = px.histogram(
            df,
            x=key,
            nbins=8,  # 分箱数量：数据量不大，8 个箱足够看清分布
            color_discrete_sequence=[color],
        )
        fig.update_layout(
            title=f"{name}分布（{unit}）",
            xaxis_title=name,
            yaxis_title="商品数量",
            height=300,
            margin=dict(t=50, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

# 能量直方图单独占一整行
fig = px.histogram(df, x="energy", nbins=8, color_discrete_sequence=["#7C3AED"])
fig.update_layout(
    title="能量分布（kcal/100g）",
    xaxis_title="能量",
    yaxis_title="商品数量",
    height=300,
    margin=dict(t=50, b=30),
)
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 4. 箱线图：五个指标并排展示（各自独立坐标轴，避免单位混淆）
# ============================================================
st.subheader("五大营养指标箱线图")

fig = make_subplots(
    rows=1,
    cols=5,
    subplot_titles=[f"{name}（{unit}）" for _, name, unit, _ in METRICS],
)
for i, (key, name, unit, color) in enumerate(METRICS, start=1):
    fig.add_trace(
        go.Box(
            y=df[key],
            name=name,
            marker_color=color,
            boxmean=True,  # 显示均值虚线，方便对比均值与中位数
        ),
        row=1,
        col=i,
    )
fig.update_layout(height=380, showlegend=False, margin=dict(t=60, b=30))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ============================================================
# 5. 品牌对比分析
# ============================================================
st.subheader("品牌对比分析")

# 按品牌聚合：商品数量 + 三大核心营养指标均值
brand_stats = (
    df.groupby("brand")
    .agg(
        商品数量=("id", "count"),
        平均糖含量=("sugar", "mean"),
        平均蛋白质=("protein", "mean"),
        平均脂肪=("fat", "mean"),
    )
    .round(1)
    .reset_index()
    .rename(columns={"brand": "品牌"})
    .sort_values("商品数量", ascending=False)
)

tab_table, tab_chart = st.tabs(["对比表格", "对比图表"])

with tab_table:
    st.dataframe(brand_stats, hide_index=True, use_container_width=True)

with tab_chart:
    # 把宽表转成长表（melt），方便 Plotly 画分组柱状图
    melted = brand_stats.melt(
        id_vars="品牌",
        value_vars=["平均糖含量", "平均蛋白质", "平均脂肪"],
        var_name="指标",
        value_name="数值",
    )
    fig = px.bar(
        melted,
        x="品牌",
        y="数值",
        color="指标",
        barmode="group",  # 分组柱状图（并列展示）
        color_discrete_map={
            "平均糖含量": "#F59E0B",
            "平均蛋白质": "#16A34A",
            "平均脂肪": "#DC2626",
        },
    )
    fig.update_layout(
        height=420,
        xaxis_title=None,
        yaxis_title="g/100g",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(t=40, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)
