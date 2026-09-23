"""
data_loader.py · 数据加载与清洗模块
====================================
模拟真实食品数据库（如 OpenFoodFacts）的原始数据清洗流程。

清洗流水线（四步）：
    1. 品类筛选   —— 只保留"酸奶"品类，剔除乳酸菌饮料、奶酪等其他品类
    2. 单位统一   —— 钠: g/100g → mg/100g（×1000）；能量: kJ → kcal（÷4.184）
    3. 缺失值处理 —— 五个关键营养字段任一缺失的记录整条删除
    4. 异常值过滤 —— 剔除指标超出合理范围的样本（如糖 95g/100g 明显是录入错误）

数据源: data/yogurt_products.csv（48 条原始记录，其中包含少量"脏数据"用于演示清洗过程）
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# ---------- 路径与常量定义 ----------

# 原始数据文件路径：从本文件位置向上两级到项目根目录，再进入 data/ 目录
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "yogurt_products.csv"

# 各营养指标的合理范围（下限, 上限），用于第 4 步异常值过滤
# 依据：市售酸奶产品常见营养标签范围
VALID_RANGES = {
    "sugar": (0, 30),     # 糖 (g/100g)：酸奶含糖量一般在 0~20，超过 30 视为异常
    "fat": (0, 15),       # 脂肪 (g/100g)
    "protein": (0, 15),   # 蛋白质 (g/100g)：正常酸奶 1~10，超过 15 疑似录入错误
    "sodium": (0, 500),   # 钠 (mg/100g)
    "energy": (20, 300),  # 能量 (kcal/100g)
}

# 关键营养字段：任一缺失则整条记录不可用，直接删除
KEY_COLS = ["sugar", "fat", "protein", "sodium", "energy"]

# 目标品类：本项目只研究酸奶
TARGET_CATEGORY = "酸奶"


def load_raw_data(path=None):
    """
    加载原始 CSV 数据（未做任何清洗）。

    参数:
        path: 可选，自定义 CSV 路径（方便以后替换成 OpenFoodFacts 真实数据）
    返回:
        pd.DataFrame: 原始数据（48 条）
    """
    csv_path = path or DATA_PATH
    return pd.read_csv(csv_path)


def clean_data(df):
    """
    对原始数据执行标准四步清洗流程。

    参数:
        df: 原始 DataFrame
    返回:
        (clean_df, log):
            clean_df —— 清洗后的标准化数据
            log      —— 清洗日志字典，记录每一步的数量变化（前端展示"清洗漏斗"用）
    """
    log = {}
    log["原始数据量"] = len(df)

    # ---------- 第 1 步：品类筛选 ----------
    # 只保留目标品类（酸奶），其他品类（乳酸菌饮料、奶酪等）全部剔除
    df = df[df["category"] == TARGET_CATEGORY].copy()
    log["品类筛选后"] = len(df)

    # ---------- 第 2 步：单位统一 ----------
    # 部分数据源的钠用 g/100g 标注，统一换算为 mg/100g（1g = 1000mg）
    sodium_in_g = df["sodium_unit"] == "g"
    df.loc[sodium_in_g, "sodium"] = df.loc[sodium_in_g, "sodium"] * 1000

    # 部分数据源的能量用 kJ 标注，换算为 kcal（1 kcal = 4.184 kJ）
    # 先把 energy 列转为 float，避免 kJ÷4.184 得到小数后无法写回 int64 列
    # （pandas 3.x 不再静默向上转型，会抛 LossySetitemError/TypeError）
    df["energy"] = df["energy"].astype("float64")
    energy_in_kj = df["energy_unit"] == "kJ"
    df.loc[energy_in_kj, "energy"] = df.loc[energy_in_kj, "energy"] / 4.184

    log["单位统一"] = (
        f"钠 g→mg：{int(sodium_in_g.sum())} 条；能量 kJ→kcal：{int(energy_in_kj.sum())} 条"
    )

    # ---------- 第 3 步：缺失值处理 ----------
    # 关键营养字段任一缺失的记录直接删除（样本量足够时这是最简单有效的策略）
    before = len(df)
    df = df.dropna(subset=KEY_COLS)
    log["缺失值删除"] = before - len(df)

    # ---------- 第 4 步：异常值过滤 ----------
    # 逐个指标按合理范围过滤，超出范围视为录入错误
    before = len(df)
    for col, (low, high) in VALID_RANGES.items():
        df = df[(df[col] >= low) & (df[col] <= high)]
    log["异常值删除"] = before - len(df)

    log["最终数据量"] = len(df)

    # ---------- 整理输出 ----------
    df = df.reset_index(drop=True)
    df["sodium"] = df["sodium"].round(0)   # 钠取整（mg 精度足够）
    df["energy"] = df["energy"].round(1)   # 能量保留 1 位小数

    return df, log


@st.cache_data(show_spinner="正在加载并清洗数据...")
def get_clean_data():
    """
    带缓存的数据加载入口。

    使用 Streamlit 的 @st.cache_data 装饰器：
    CSV 只会在第一次运行时被读取和清洗，之后的页面切换直接复用缓存结果，速度更快。

    返回:
        (clean_df, log): 清洗后的数据 + 清洗日志
    """
    raw = load_raw_data()
    return clean_data(raw)
