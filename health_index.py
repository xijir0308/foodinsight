"""
health_index.py · 食品健康指数（Health Index, HI）计算模块
============================================================
核心思想：规则引擎 + 多指标决策（Multi-Criteria Decision Making），
强调可解释性，而不是机器学习黑盒模型。

计算公式（依据 WHO 营养健康理念设置权重）：
    HI = 100 × (wP×P + wE×E − wS×S − wF×F − wN×N)

指标说明：
    P = 标准化蛋白质   （正向指标：蛋白质越高越健康）
    E = 能量合理性     （正向指标：能量越接近理想区间得分越高）
    S = 标准化糖       （负向指标：糖越高扣分越多）
    F = 标准化脂肪     （负向指标）
    N = 标准化钠       （负向指标）

标准化方法：Min-Max 归一化
（使用 scikit-learn 的 MinMaxScaler 实现 —— 这是项目中唯一用到 sklearn 的地方，
  不涉及任何机器学习模型训练）

最终 HI 线性映射到 0~100 分，分数越高代表越健康。
"""

import numpy as np
from sklearn.preprocessing import MinMaxScaler

# ---------- 权重方案 ----------

# WHO 默认权重（通用人群）：蛋白质权重最高，糖次之
DEFAULT_WEIGHTS = {"p": 0.35, "e": 0.15, "s": 0.25, "f": 0.15, "n": 0.10}

# 四类目标人群的权重方案（每套权重之和均为 1）
# 设计逻辑：
#   减脂人群 —— 糖和脂肪的惩罚权重调高（控糖控脂是核心诉求）
#   健身人群 —— 蛋白质权重调到 0.45（高蛋白补充是第一优先级）
#   儿童人群 —— 能量合理性权重调高（儿童需要适量能量支持发育）
#   控盐人群 —— 钠的惩罚权重翻倍（严格控钠保护心血管）
AUDIENCES = {
    "减脂人群": {
        "desc": "控糖控脂，追求低热量高蛋白",
        "weights": {"p": 0.25, "e": 0.10, "s": 0.30, "f": 0.25, "n": 0.10},
        "hint": "减脂人群关注低糖低脂高蛋白，推荐选择蛋白质含量高且糖分较低的产品作为代餐或加餐。",
        "selling_points": ["低热量控糖", "饱腹代餐", "低脂配方"],
    },
    "健身人群": {
        "desc": "高蛋白补充，控制糖分摄入",
        "weights": {"p": 0.45, "e": 0.15, "s": 0.20, "f": 0.10, "n": 0.10},
        "hint": "健身人群需要高蛋白质补充以支持肌肉恢复，优先选择希腊式高蛋白酸奶。",
        "selling_points": ["高蛋白补充", "运动后恢复", "低糖配方"],
    },
    "儿童人群": {
        "desc": "均衡营养，适量能量摄入",
        "weights": {"p": 0.30, "e": 0.25, "s": 0.20, "f": 0.15, "n": 0.10},
        "hint": "儿童人群需要均衡的营养摄入和适量能量，避免高糖产品影响饮食习惯。",
        "selling_points": ["天然原料", "均衡营养", "口感友好"],
    },
    "控盐人群": {
        "desc": "严格控钠，关注心血管健康",
        "weights": {"p": 0.30, "e": 0.15, "s": 0.20, "f": 0.15, "n": 0.20},
        "hint": "控盐人群需要严格限制钠摄入，选择低钠低糖的天然发酵酸奶更为适宜。",
        "selling_points": ["低钠健康", "心血管友好", "天然发酵"],
    },
}

# 权重键 → 中文名称映射（前端展示用）
WEIGHT_LABELS = {
    "p": "蛋白质 P（正向）",
    "e": "能量合理性 E（正向）",
    "s": "糖 S（负向）",
    "f": "脂肪 F（负向）",
    "n": "钠 N（负向）",
}


def min_max_normalize(values):
    """
    Min-Max 标准化：把数据线性映射到 [0, 1] 区间。
    公式：x_norm = (x - min) / (max - min)

    使用 sklearn 的 MinMaxScaler 实现（项目唯一用到 scikit-learn 的地方）。

    参数:
        values: 一列原始数值（list / Series / ndarray 均可）
    返回:
        np.ndarray: 标准化后的数组，范围 [0, 1]
    """
    scaler = MinMaxScaler()
    arr = np.asarray(values, dtype=float).reshape(-1, 1)  # MinMaxScaler 要求二维输入
    return scaler.fit_transform(arr).flatten()


def energy_reasonableness(energy, ideal=85.0, tolerance=60.0):
    """
    能量合理性 E：不是简单的"越低越好"，而是"越接近理想区间越好"。

    原因：能量过低的酸奶可能营养不足，过高则热量超标；
    对于日常乳制品，85 kcal/100g 左右是较理想的能量水平。
    偏离理想值超过 60 kcal 记 0 分，完全吻合记 1 分。

    参数:
        energy: 能量列 (kcal/100g)
        ideal: 理想能量值，默认 85
        tolerance: 最大容忍偏差，默认 60
    返回:
        np.ndarray: [0, 1] 之间的得分数组
    """
    energy = np.asarray(energy, dtype=float)
    distance = np.abs(energy - ideal)
    return np.clip(1 - distance / tolerance, 0, 1)


def compute_health_index(df, weights=None):
    """
    为每个商品计算 HI 健康指数（核心函数）。

    参数:
        df: 清洗后的商品 DataFrame（必须含 sugar/fat/protein/sodium/energy 列）
        weights: 权重字典 {"p":..,"e":..,"s":..,"f":..,"n":..}，
                 不传则使用 WHO 默认权重
    返回:
        新的 DataFrame（按 HI 降序排列），新增列：
            hi           —— 健康指数（0~100）
            norm_protein —— 蛋白质标准化分量（供解释与调试）
            norm_sugar   —— 糖标准化分量
            norm_fat     —— 脂肪标准化分量
            norm_sodium  —— 钠标准化分量
            norm_energy  —— 能量合理性分量
    """
    w = weights or DEFAULT_WEIGHTS

    # 第 1 步：各指标标准化到 [0, 1]
    p = min_max_normalize(df["protein"])
    s = min_max_normalize(df["sugar"])
    f = min_max_normalize(df["fat"])
    n = min_max_normalize(df["sodium"])
    e = energy_reasonableness(df["energy"])

    # 第 2 步：加权合成（正向指标加分，负向指标扣分）
    raw = 100 * (w["p"] * p + w["e"] * e - w["s"] * s - w["f"] * f - w["n"] * n)

    # 第 3 步：把原始得分线性映射到 0~100
    # （raw 可能为负数，先平移到非负区间再缩放）
    hi_min, hi_max = raw.min(), raw.max()
    hi = (raw - hi_min) / (hi_max - hi_min) * 100

    # 第 4 步：结果写回 DataFrame，并保留各分量便于解释
    out = df.copy()
    out["hi"] = hi.round(1)
    out["norm_protein"] = p.round(3)
    out["norm_sugar"] = s.round(3)
    out["norm_fat"] = f.round(3)
    out["norm_sodium"] = n.round(3)
    out["norm_energy"] = e.round(3)

    # 按 HI 降序排列：排最前面的就是最健康的产品
    return out.sort_values("hi", ascending=False).reset_index(drop=True)


def hi_level(hi):
    """
    HI 分数 → 健康等级（用于前端颜色标注）。
        ≥70 优秀 / ≥40 中等 / 其余 偏低
    """
    if hi >= 70:
        return "优秀"
    if hi >= 40:
        return "中等"
    return "偏低"
