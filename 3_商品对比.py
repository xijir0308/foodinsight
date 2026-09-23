"""
模块三 · 商品对比
==================
支持选择 2~5 个商品进行横向对比：
    1. 雷达图       —— 五大营养指标归一化后的多维对比（覆盖面积越大越均衡）
    2. HI 得分柱状图 —— 健康指数直观排序
    3. 营养成分对比表 —— 最优值绿色高亮、最差值红色标注
    4. 卖点与短板解读 —— 每个商品相对行业均值的优势与不足
"""

import sys
from pathlib import Path

# 把项目根目录加入模块搜索路径，保证能导入 core 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.data_loader import get_clean_data
from core.health_index import compute_health_index, hi_level

# ---------- 页面配置 ----------
st.set_page_config(page_title="商品对比 · FoodInsight", layout="wide")

# ---------- 加载数据并计算 HI ----------
df, _ = get_clean_data()
hi_df = compute_health_index(df)

st.title("商品对比")
st.caption("选择 2~5 个商品，生成雷达图与营养成分对比表，突出各产品卖点与短板")

# ============================================================
# 1. 商品选择器（2~5 个）
# ============================================================
# 下拉选项格式："商品名（品牌）"，并建立 选项文字 → 商品 id 的映射
label_to_id = {
    f"{row['name']}（{row['brand']}）": row["id"]
    for _, row in hi_df.iterrows()
}

# 默认选中三个有代表性的商品：低糖款、希腊高蛋白款、健身款
default_names = ["简爱0%蔗糖酸奶", "乐纯希腊酸奶原味", "乐纯FIT0蔗糖酸奶"]
default_labels = [
    label for label in label_to_id
    if any(name in label for name in default_names)
]

selected_labels = st.multiselect(
    "选择对比商品（2~5 个）",
    list(label_to_id.keys()),
    default=default_labels,
)

# 数量校验：少于 2 个无法对比，超过 5 个图表会过于拥挤
if len(selected_labels) < 2:
    st.info("请至少选择 2 个商品进行对比")
    st.stop()
if len(selected_labels) > 5:
    st.warning("最多支持同时对比 5 个商品，请减少选择")
    st.stop()

selected_ids = [label_to_id[label] for label in selected_labels]
selected = hi_df[hi_df["id"].isin(selected_ids)].copy()

# ============================================================
# 2. 雷达图（五大营养指标归一化到 0~100）
# ============================================================
st.subheader("营养雷达图")

# 雷达图的五个维度
RADAR_METRICS = [
    ("sugar", "糖含量"),
    ("fat", "脂肪"),
    ("protein", "蛋白质"),
    ("sodium", "钠"),
    ("energy", "能量"),
]


def norm01(col_name, value):
    """
    基于全量数据做 Min-Max 归一化并放大到 0~100。
    注意：用全量数据的 min/max 而不是所选商品的，
    保证不同选择组合之间得分可比。
    """
    col = hi_df[col_name]
    if col.max() == col.min():
        return 50.0
    return (value - col.min()) / (col.max() - col.min()) * 100


fig = go.Figure()
for _, product in selected.iterrows():
    values = [norm01(key, product[key]) for key, _ in RADAR_METRICS]
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],  # 首尾相连闭合多边形
            theta=[name for _, name in RADAR_METRICS] + [RADAR_METRICS[0][1]],
            name=product["name"],
            fill="toself",   # 填充多边形内部，直观对比覆盖面积
            opacity=0.45,
            line=dict(width=2),
        )
    )
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100], title="归一化得分 (0-100)")),
    height=480,
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0.5, xanchor="center"),
    margin=dict(t=50, b=80),
)
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 3. HI 得分柱状图
# ============================================================
st.subheader("HI 健康指数对比")

selected["等级"] = selected["hi"].apply(hi_level)
sorted_selected = selected.sort_values("hi")  # 升序排列让最高分显示在顶部
fig = px.bar(
    sorted_selected,
    x="hi",
    y="name",
    orientation="h",  # 横向柱状图，商品名更易读
    color="等级",
    color_discrete_map={"优秀": "#16A34A", "中等": "#F59E0B", "偏低": "#DC2626"},
    text="hi",  # 柱状图末端显示 HI 数值（与排序后的数据对齐）
    labels={"hi": "HI 健康指数", "name": None},
    height=60 * len(selected) + 120,
)
fig.update_layout(
    xaxis=dict(range=[0, 105], title="HI (0-100)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(t=40, b=30),
)
fig.update_traces(textposition="outside")
st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 4. 营养成分对比表（最优值绿色 / 最差值红色）
# ============================================================
st.subheader("营养成分对比表")

# 对比表的行定义：(显示名, 字段名, 指标方向)
# 负向指标 = 数值越低越好（糖/脂肪/钠/能量）；正向指标 = 数值越高越好（蛋白质/HI）
ROWS_DEF = [
    ("糖 (g/100g)", "sugar", "negative"),
    ("脂肪 (g/100g)", "fat", "negative"),
    ("蛋白质 (g/100g)", "protein", "positive"),
    ("钠 (mg/100g)", "sodium", "negative"),
    ("能量 (kcal)", "energy", "negative"),
    ("HI 健康指数", "hi", "positive"),
]

# 组装对比表：第一列为指标名，其余列为各商品的数值
compare_table = pd.DataFrame({"营养指标": [row[0] for row in ROWS_DEF]})
for _, product in selected.iterrows():
    compare_table[product["name"]] = [product[key] for _, key, _ in ROWS_DEF]


def build_styles(table):
    """
    生成与对比表同形状的样式 DataFrame：
    每一行中，最优值标绿色背景，最差值标红色背景。
    """
    styles = pd.DataFrame("", index=table.index, columns=table.columns)
    product_cols = table.columns[1:]  # 跳过"营养指标"列
    for i, (_, _, direction) in enumerate(ROWS_DEF):
        row_values = table.loc[i, list(product_cols)].astype(float)
        if row_values.max() == row_values.min():
            continue  # 所有商品数值相同，无需标注
        if direction == "negative":
            best, worst = row_values.idxmin(), row_values.idxmax()
        else:
            best, worst = row_values.idxmax(), row_values.idxmin()
        styles.loc[i, best] = "background-color:#DCFCE7;color:#16A34A;font-weight:600"
        styles.loc[i, worst] = "background-color:#FEE2E2;color:#DC2626"
    return styles


st.dataframe(
    compare_table.style.apply(lambda _: build_styles(compare_table), axis=None),
    hide_index=True,
    use_container_width=True,
)
st.caption("绿色 = 该指标表现最优 ｜ 红色 = 该指标表现最差（负向指标数值越低越好）")

# ============================================================
# 5. 卖点与短板解读（相对行业均值）
# ============================================================
st.subheader("卖点与短板解读")

# 行业均值基准
avg_sugar = hi_df["sugar"].mean()
avg_protein = hi_df["protein"].mean()
avg_fat = hi_df["fat"].mean()
avg_sodium = hi_df["sodium"].mean()

cols = st.columns(len(selected))
for col, (_, product) in zip(cols, selected.iterrows()):
    # 相对行业均值识别卖点
    strengths = []
    if product["protein"] >= avg_protein:
        strengths.append("蛋白质丰富")
    if product["sugar"] <= avg_sugar:
        strengths.append("低糖")
    if product["fat"] <= avg_fat:
        strengths.append("低脂")
    if product["sodium"] <= avg_sodium:
        strengths.append("低钠")

    # 相对行业均值识别短板
    weaknesses = []
    if product["sugar"] > avg_sugar:
        weaknesses.append("糖偏高")
    if product["protein"] < avg_protein:
        weaknesses.append("蛋白质偏低")
    if product["fat"] > avg_fat:
        weaknesses.append("脂肪偏高")

    with col:
        st.markdown(f"**{product['name']}**")
        st.caption(f"{product['brand']} ｜ HI {product['hi']:.1f}")
        st.success("卖点：" + ("、".join(strengths) if strengths else "营养均衡"))
        st.warning("短板：" + ("、".join(weaknesses) if weaknesses else "无明显短板"))
