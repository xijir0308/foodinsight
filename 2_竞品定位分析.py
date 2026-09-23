"""
模块二 · 竞品定位分析
======================
建立二维产品定位矩阵（X 轴：糖含量；Y 轴：蛋白质）：
    1. 交互散点图 —— 每个点代表一个商品，点大小 = HI 健康指数，颜色 = 品牌
    2. 四象限划分 —— 以糖/蛋白质中位数为分界线，识别四类市场定位：
         左上：高蛋白低糖 · 健康定位
         右上：高蛋白高糖 · 运动型
         左下：低蛋白低糖 · 基础款
         右下：高糖低蛋白 · 零食型
    3. 品牌筛选   —— 支持按品牌过滤查看
    4. TOP 5 榜单 —— 高蛋白低糖象限中的最优商品
"""

import sys
from pathlib import Path

# 把项目根目录加入模块搜索路径，保证能导入 core 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st

from core.data_loader import get_clean_data
from core.health_index import compute_health_index

# ---------- 页面配置 ----------
st.set_page_config(page_title="竞品定位分析 · FoodInsight", layout="wide")

# ---------- 加载数据并计算 HI ----------
df, _ = get_clean_data()
hi_df = compute_health_index(df)

st.title("竞品定位分析")
st.caption("糖含量 vs 蛋白质 二维产品定位矩阵 ｜ 点大小 = HI 健康指数 ｜ 颜色 = 品牌")

# ============================================================
# 1. 品牌筛选器
# ============================================================
all_brands = sorted(hi_df["brand"].unique())
selected_brands = st.multiselect(
    "品牌筛选（可多选，默认全部）",
    all_brands,
    default=all_brands,
)
filtered = hi_df[hi_df["brand"].isin(selected_brands)]

if filtered.empty:
    st.warning("请至少选择一个品牌")
    st.stop()

# ============================================================
# 2. 定位矩阵散点图
# ============================================================
# 中位数参考线基于全量数据计算（保证切换品牌筛选时象限位置稳定）
sugar_median = hi_df["sugar"].median()
protein_median = hi_df["protein"].median()

fig = px.scatter(
    filtered,
    x="sugar",
    y="protein",
    color="brand",
    size="hi",          # 点大小映射 HI：越健康点越大
    size_max=38,
    hover_data={
        "id": False,
        "name": True,
        "sugar": ":.1f",
        "protein": ":.1f",
        "fat": ":.1f",
        "sodium": ":.0f",
        "energy": ":.0f",
        "hi": ":.1f",
    },
    labels={"sugar": "糖含量 (g/100g)", "protein": "蛋白质 (g/100g)"},
    height=560,
)

# 中位数分界线（虚线）：把平面切成四个象限
fig.add_vline(
    x=sugar_median, line_dash="dash", line_color="#94A3B8",
    annotation_text=f"糖中位数 {sugar_median:.1f}",
    annotation_position="bottom right",
)
fig.add_hline(
    y=protein_median, line_dash="dash", line_color="#94A3B8",
    annotation_text=f"蛋白质中位数 {protein_median:.1f}",
    annotation_position="top left",
)

# 四象限标注（放在各象限中心附近）
x_min, x_max = filtered["sugar"].min(), filtered["sugar"].max()
y_min, y_max = filtered["protein"].min(), filtered["protein"].max()
quadrant_annotations = [
    # (x, y, 文字, 颜色)
    ((x_min + sugar_median) / 2, (protein_median + y_max) / 2, "高蛋白低糖 · 健康定位", "#16A34A"),
    ((sugar_median + x_max) / 2, (protein_median + y_max) / 2, "高蛋白高糖 · 运动型", "#0EA5E9"),
    ((x_min + sugar_median) / 2, (y_min + protein_median) / 2, "低蛋白低糖 · 基础款", "#64748B"),
    ((sugar_median + x_max) / 2, (y_min + protein_median) / 2, "高糖低蛋白 · 零食型", "#DC2626"),
]
for qx, qy, text, color in quadrant_annotations:
    fig.add_annotation(
        x=qx, y=qy, text=text,
        showarrow=False,
        font=dict(size=13, color=color),
        opacity=0.85,
    )

fig.update_layout(
    legend=dict(title="品牌", orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    margin=dict(t=30, b=40, r=120),
)
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 3. 四象限商品数量统计
# ============================================================
st.subheader("市场定位分布")


def classify_quadrant(row):
    """根据糖/蛋白质与中位数的关系，把商品归入四个象限之一"""
    high_protein = row["protein"] >= protein_median
    low_sugar = row["sugar"] < sugar_median
    if high_protein and low_sugar:
        return "高蛋白低糖"
    if high_protein and not low_sugar:
        return "高蛋白高糖"
    if not high_protein and low_sugar:
        return "低蛋白低糖"
    return "高糖低蛋白"


filtered = filtered.copy()
filtered["象限"] = filtered.apply(classify_quadrant, axis=1)
quadrant_counts = filtered["象限"].value_counts()

q1, q2, q3, q4 = st.columns(4)
q1.metric("高蛋白低糖 · 健康定位", f"{quadrant_counts.get('高蛋白低糖', 0)} 款")
q2.metric("高蛋白高糖 · 运动型", f"{quadrant_counts.get('高蛋白高糖', 0)} 款")
q3.metric("低蛋白低糖 · 基础款", f"{quadrant_counts.get('低蛋白低糖', 0)} 款")
q4.metric("高糖低蛋白 · 零食型", f"{quadrant_counts.get('高糖低蛋白', 0)} 款")

# ============================================================
# 4. 高蛋白低糖象限 TOP 5
# ============================================================
st.subheader("高蛋白低糖象限 TOP 5（按 HI 排序）")
top5 = (
    filtered[filtered["象限"] == "高蛋白低糖"]
    .sort_values("hi", ascending=False)
    .head(5)
)

if top5.empty:
    st.info("当前筛选条件下没有商品落在高蛋白低糖象限")
else:
    st.dataframe(
        top5[["name", "brand", "sugar", "protein", "hi"]],
        column_config={
            "name": st.column_config.TextColumn("商品名称", width="large"),
            "brand": st.column_config.TextColumn("品牌"),
            "sugar": st.column_config.NumberColumn("糖 (g/100g)", format="%.1f"),
            "protein": st.column_config.NumberColumn("蛋白质 (g/100g)", format="%.1f"),
            "hi": st.column_config.ProgressColumn("HI 健康指数", min_value=0, max_value=100, format="%.1f"),
        },
        hide_index=True,
        use_container_width=True,
    )
