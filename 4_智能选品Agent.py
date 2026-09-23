"""
模块四 · 智能选品 Agent
========================
模拟产品经理的选品决策全流程：
    1. 选择目标人群（减脂 / 健身 / 儿童 / 控盐）
    2. 系统根据人群动态调整 Health Index 权重
    3. 重新计算 HI 并对商品排序
    4. 为 TOP 1 商品自动生成约 200 字的竞品分析报告（含直播卖点建议）

进阶功能：支持手动微调五个指标的权重（自动归一化），观察排序变化。
"""

import sys
from pathlib import Path

# 把项目根目录加入模块搜索路径，保证能导入 core 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from core.data_loader import get_clean_data
from core.health_index import (
    AUDIENCES,
    WEIGHT_LABELS,
    compute_health_index,
    hi_level,
)
from core.report_generator import generate_report

# ---------- 页面配置 ----------
st.set_page_config(page_title="智能选品 Agent · FoodInsight", layout="wide")

# ---------- 加载数据 ----------
df, _ = get_clean_data()

st.title("智能选品 Agent")
st.caption("规则引擎 + 多指标决策（MCDM）｜ 动态权重 · 可解释评分 · 自动报告")

# ============================================================
# 1. 目标人群选择（四类人群，权重方案各不相同）
# ============================================================
st.subheader("第一步：选择目标人群")

audience_names = list(AUDIENCES.keys())
selected_audience = st.radio(
    "目标人群",
    audience_names,
    horizontal=True,  # 横向排列，四个选项一目了然
    index=1,          # 默认选中"健身人群"（高蛋白权重差异最明显，演示效果好）
)
audience_info = AUDIENCES[selected_audience]
st.info(f"**{selected_audience}**：{audience_info['desc']}")

# 当前生效的权重（先取人群默认方案，若启用自定义则覆盖）
weights = audience_info["weights"]

# ---------- 进阶：手动微调权重 ----------
with st.expander("高级：手动微调权重（可选）"):
    st.caption("拖动滑块自定义各指标权重（0~100），系统会自动归一化使总和为 1")
    w_cols = st.columns(5)
    raw_weights = {}
    for col, (key, label) in zip(w_cols, WEIGHT_LABELS.items()):
        # 滑块初始值 = 当前人群方案的权重（×100 便于拖动）
        raw_weights[key] = col.slider(
            label, 0, 100, int(weights[key] * 100), key=f"weight_{key}"
        )

    total = sum(raw_weights.values())
    if total == 0:
        st.warning("权重总和不能为 0，请至少调高一个滑块")
        st.stop()

    # 归一化：保证五个权重之和为 1
    custom_weights = {k: v / total for k, v in raw_weights.items()}

    use_custom = st.checkbox("启用自定义权重（覆盖人群默认方案）", value=False)
    if use_custom:
        weights = custom_weights
        st.success("已启用自定义权重")

# ============================================================
# 2. 展示当前权重公式（可解释性核心）
# ============================================================
st.subheader("第二步：Health Index 权重公式")

st.latex(r"HI = 100 \times (w_P \cdot P + w_E \cdot E - w_S \cdot S - w_F \cdot F - w_N \cdot N)")

# 用进度条直观展示各指标权重占比
for key, label in WEIGHT_LABELS.items():
    st.progress(weights[key], text=f"{label}：{weights[key] * 100:.0f}%")

# ============================================================
# 3. 重新计算 HI 并排序
# ============================================================
st.subheader("第三步：商品重新排序")

# 用当前权重重新计算全部商品的 HI（权重变化 → 排序变化）
ranked = compute_health_index(df, weights)

top_n = st.slider("显示 TOP N 商品", min_value=5, max_value=len(ranked), value=15)
show_df = ranked.head(top_n)[["name", "brand", "sugar", "protein", "fat", "sodium", "hi"]].copy()
show_df.insert(0, "排名", range(1, len(show_df) + 1))
show_df["等级"] = show_df["hi"].apply(hi_level)

st.dataframe(
    show_df,
    column_config={
        "排名": st.column_config.NumberColumn("排名", width="small"),
        "name": st.column_config.TextColumn("商品名称", width="large"),
        "brand": st.column_config.TextColumn("品牌"),
        "sugar": st.column_config.NumberColumn("糖 (g/100g)", format="%.1f"),
        "protein": st.column_config.NumberColumn("蛋白质 (g/100g)", format="%.1f"),
        "fat": st.column_config.NumberColumn("脂肪 (g/100g)", format="%.1f"),
        "sodium": st.column_config.NumberColumn("钠 (mg/100g)", format="%.0f"),
        "hi": st.column_config.ProgressColumn("HI 健康指数", min_value=0, max_value=100, format="%.1f"),
        "等级": st.column_config.TextColumn("等级"),
    },
    hide_index=True,
    use_container_width=True,
)

# ============================================================
# 4. TOP 1 商品竞品分析报告（模板自动生成，约 200 字）
# ============================================================
st.subheader("第四步：TOP 1 商品竞品分析报告")

top1 = ranked.iloc[0]

# 生成报告（模拟产品经理整理商品资料的过程）
with st.spinner("正在生成竞品分析报告..."):
    report = generate_report(top1, ranked, selected_audience, audience_info)

st.success(report)
st.caption(
    f"报告对象：{top1['name']}（{top1['brand']}）｜ "
    f"HI = {top1['hi']:.1f} ｜ 目标人群：{selected_audience}"
)

# 报告下载按钮（方便产品经理存档或转发）
st.download_button(
    "下载分析报告（Markdown）",
    data=report,
    file_name=f"{top1['name']}_竞品分析报告.md",
    mime="text/markdown",
)
