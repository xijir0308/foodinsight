"""
app.py · FoodInsight 主入口（项目首页）
=========================================
食品竞品分析与智能选品决策平台 —— 面向食品产品经理的竞品调研与选品决策工具。

运行方式（在项目根目录下执行）：
    streamlit run app.py

页面结构（Streamlit 多页面应用，pages/ 目录会被自动识别并显示在左侧导航栏）：
    app.py                    → 项目首页（当前页）
    pages/1_数据概览.py        → 模块一：数据库全景与营养分布
    pages/2_竞品定位分析.py     → 模块二：糖-蛋白质二维定位矩阵
    pages/3_商品对比.py        → 模块三：多商品雷达图对比
    pages/4_智能选品Agent.py   → 模块四：目标人群智能选品与报告生成
"""

import pandas as pd
import streamlit as st

from core.data_loader import get_clean_data
from core.health_index import DEFAULT_WEIGHTS, WEIGHT_LABELS, compute_health_index

# ---------- 全局页面配置（必须是第一个 Streamlit 命令） ----------
st.set_page_config(
    page_title="FoodInsight · 食品竞品分析与智能选品决策平台",
    layout="wide",  # 宽屏布局，适合数据分析平台
)

# ---------- 加载数据（带缓存，只清洗一次） ----------
df, clean_log = get_clean_data()
hi_df = compute_health_index(df)  # 使用 WHO 默认权重计算 HI

# ---------- 侧边栏：项目信息 ----------
with st.sidebar:
    st.markdown("### FoodInsight")
    st.caption("食品竞品分析与智能选品决策平台")
    st.divider()
    st.markdown("**数据概况**")
    st.caption(f"商品：{len(df)} 款 ｜ 品牌：{df['brand'].nunique()} 个")
    st.caption("品类：酸奶 ｜ 来源：OpenFoodFacts（模拟）")
    st.divider()
    st.markdown("**技术栈**")
    st.caption("Streamlit · Pandas · NumPy · Plotly · Scikit-learn")
    st.divider()
    st.caption("核心方法：规则引擎 + 多指标决策（MCDM），强调可解释性")

# ---------- 首页标题与简介 ----------
st.title("FoodInsight · 食品竞品分析与智能选品决策平台")
st.markdown(
    "面向**食品产品经理**的竞品调研与选品决策工具：基于 OpenFoodFacts 公开食品数据库，"
    "通过可解释的 **Health Index（食品健康指数）** 对同类商品进行量化评估，"
    "覆盖数据概览、竞品定位、商品对比、智能选品四大分析场景。"
)

# ---------- 四大功能模块导航 ----------
st.subheader("功能模块")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**① 数据概览**")
    st.caption("品牌/商品统计，营养指标直方图与箱线图")
    st.page_link("pages/1_数据概览.py", label="进入模块", use_container_width=True)
with col2:
    st.markdown("**② 竞品定位分析**")
    st.caption("糖-蛋白质二维定位矩阵，识别市场定位")
    st.page_link("pages/2_竞品定位分析.py", label="进入模块", use_container_width=True)
with col3:
    st.markdown("**③ 商品对比**")
    st.caption("2~5 个商品雷达图与营养成分对比表")
    st.page_link("pages/3_商品对比.py", label="进入模块", use_container_width=True)
with col4:
    st.markdown("**④ 智能选品 Agent**")
    st.caption("目标人群动态权重选品 + 自动分析报告")
    st.page_link("pages/4_智能选品Agent.py", label="进入模块", use_container_width=True)

st.divider()

# ---------- Health Index 核心公式说明 ----------
st.subheader("核心算法：Health Index 食品健康指数")

formula_col, explain_col = st.columns([1, 1])

with formula_col:
    # 默认权重下的公式（LaTeX 渲染）
    st.latex(
        r"HI = 100 \times (0.35\,P + 0.15\,E - 0.25\,S - 0.15\,F - 0.10\,N)"
    )
    st.caption("P=蛋白质（正向） E=能量合理性（正向） S=糖（负向） F=脂肪（负向） N=钠（负向）")

with explain_col:
    st.markdown(
        """
**计算流程（完全可解释，非机器学习黑盒）：**

1. 所有营养指标先做 **Min-Max 标准化**（映射到 0~1）
2. 糖、钠、脂肪为**负向指标**（扣分），蛋白质为**正向指标**（加分）
3. 依据 **WHO 营养健康理念**设置权重并加权合成
4. 最终映射为 **0~100 分**的健康指数，用于同类商品排序
"""
    )

# 权重明细表
weight_table = pd.DataFrame(
    {
        "指标": list(WEIGHT_LABELS.values()),
        "默认权重": [f"{DEFAULT_WEIGHTS[k] * 100:.0f}%" for k in WEIGHT_LABELS],
        "方向": ["正向加分" if k in ("p", "e") else "负向扣分" for k in WEIGHT_LABELS],
    }
)
st.dataframe(weight_table, hide_index=True, use_container_width=True)

st.divider()

# ---------- 数据预览 ----------
st.subheader("标准化商品数据库预览（按 HI 降序）")
st.caption(f"共 {len(hi_df)} 款商品 ｜ 原始数据 {clean_log['原始数据量']} 条，"
           f"经品类筛选、单位统一、缺失值与异常值清洗后入库")

preview = hi_df[["name", "brand", "sugar", "fat", "protein", "sodium", "energy", "hi"]].copy()
st.dataframe(
    preview.head(15),
    column_config={
        "name": st.column_config.TextColumn("商品名称", width="large"),
        "brand": st.column_config.TextColumn("品牌"),
        "sugar": st.column_config.NumberColumn("糖 (g/100g)", format="%.1f"),
        "fat": st.column_config.NumberColumn("脂肪 (g/100g)", format="%.1f"),
        "protein": st.column_config.NumberColumn("蛋白质 (g/100g)", format="%.1f"),
        "sodium": st.column_config.NumberColumn("钠 (mg/100g)", format="%.0f"),
        "energy": st.column_config.NumberColumn("能量 (kcal)", format="%.1f"),
        "hi": st.column_config.ProgressColumn("HI 健康指数", min_value=0, max_value=100, format="%.1f"),
    },
    hide_index=True,
    use_container_width=True,
)

st.caption("提示：左侧导航栏可切换四大功能模块。")
