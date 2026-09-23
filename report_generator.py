"""
report_generator.py · 竞品分析报告生成模块
============================================
模拟产品经理日常工作中"整理商品资料、撰写卖点分析"的流程：
基于固定模板 + 真实数据，自动生成约 200 字的竞品分析报告。

报告结构（五段式）：
    1. 总体评价   —— HI 得分与健康等级
    2. 行业对比   —— 糖/蛋白质/脂肪与行业均值的比较
    3. 优势与短板 —— 根据各项指标与均值的相对位置自动识别
    4. 人群匹配   —— 目标人群的需求描述与匹配建议
    5. 卖点建议   —— 可直接用于直播/详情页的宣传话术
"""

from core.health_index import hi_level


def generate_report(product, df, audience_name=None, audience_info=None):
    """
    生成一份竞品分析报告（Markdown 格式文本）。

    参数:
        product: pd.Series，目标商品（必须已包含 hi 字段）
        df: pd.DataFrame，全部商品数据（用于计算行业均值）
        audience_name: str，目标人群名称（可选，默认"通用人群"）
        audience_info: dict，人群配置（含 hint 与 selling_points，可选）
    返回:
        str: Markdown 格式的报告文本（约 200 字）
    """
    # ---------- 行业均值（对比基准） ----------
    avg_sugar = df["sugar"].mean()
    avg_protein = df["protein"].mean()
    avg_fat = df["fat"].mean()
    avg_sodium = df["sodium"].mean()

    # ---------- 与行业均值的相对位置 ----------
    sugar_cmp = "低于" if product["sugar"] < avg_sugar else "高于"
    protein_cmp = "高于" if product["protein"] > avg_protein else "低于"
    fat_cmp = "低于" if product["fat"] < avg_fat else "高于"

    # ---------- 自动识别卖点（优势） ----------
    strengths = []
    if product["protein"] >= avg_protein:
        strengths.append("蛋白质含量丰富")
    if product["sugar"] <= avg_sugar:
        strengths.append("糖含量较低")
    if product["fat"] <= avg_fat:
        strengths.append("脂肪含量适中")
    if product["sodium"] <= avg_sodium:
        strengths.append("钠含量低")

    # ---------- 自动识别短板 ----------
    weaknesses = []
    if product["sugar"] > avg_sugar:
        weaknesses.append("糖含量偏高")
    if product["protein"] < avg_protein:
        weaknesses.append("蛋白质偏低")
    if product["fat"] > avg_fat:
        weaknesses.append("脂肪偏高")

    strength_text = "、".join(strengths) if strengths else "营养均衡"
    weakness_text = "、".join(weaknesses) if weaknesses else "无明显短板"

    # ---------- 目标人群匹配信息 ----------
    audience_name = audience_name or "通用人群"
    hint = audience_info["hint"] if audience_info else ""
    selling_points = (
        audience_info["selling_points"]
        if audience_info
        else ["营养均衡", "品质保证", "日常推荐"]
    )

    level = hi_level(product["hi"])

    # ---------- 模板拼装（约 200 字） ----------
    report = (
        f"**{product['name']}**（{product['brand']}）在「{audience_name}」维度下的健康指数为 "
        f"**{product['hi']:.1f} 分**（{level}）。"
        f"该产品糖含量 {product['sugar']}g/100g，{sugar_cmp}行业均值（{avg_sugar:.1f}g）；"
        f"蛋白质 {product['protein']}g/100g，{protein_cmp}行业均值（{avg_protein:.1f}g）；"
        f"脂肪 {product['fat']}g/100g，{fat_cmp}行业均值（{avg_fat:.1f}g）。"
        f"产品核心优势：{strength_text}；需关注：{weakness_text}。"
        f"{hint}"
        f"建议直播卖点：{'、'.join(selling_points)}。"
        f"产品经理可据此确定「{strength_text}」的核心宣传方向，"
        f"结合{audience_name}需求优化包装与话术。"
    )
    return report
