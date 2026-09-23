# FoodInsight · 食品竞品分析与智能选品决策平台

面向**食品产品经理**的竞品调研与选品决策平台。基于 OpenFoodFacts 公开食品数据库（酸奶品类），通过可解释的 **Health Index（食品健康指数）** 对同类商品进行量化评估，模拟食品企业竞品调研与选品决策的完整工作流程。

> 核心思想：**规则引擎 + 多指标决策（Multi-Criteria Decision Making）**，强调可解释性、产品分析能力和数据驱动决策，而非机器学习分类算法。

## 功能模块

| 模块 | 说明 |
|------|------|
| 数据概览 | 品牌/商品数量统计，五大营养指标直方图与箱线图，品牌横向对比 |
| 竞品定位分析 | 糖-蛋白质二维定位矩阵（Plotly 交互散点图），识别"高蛋白低糖""高糖零食型"等市场定位 |
| 商品对比 | 选择 2~5 个商品，生成雷达图与营养成分对比表，突出卖点与短板 |
| 智能选品 Agent | 选择目标人群（减脂/健身/儿童/控盐），动态调整 HI 权重重新排序，自动生成约 200 字竞品分析报告 |

## 核心算法：Health Index

所有营养指标先做 Min-Max 标准化（scikit-learn `MinMaxScaler`，仅用于标准化，不涉及模型训练），再按 WHO 营养健康理念加权：

```
HI = 100 × (0.35P + 0.15E − 0.25S − 0.15F − 0.10N)
```

- P = 标准化蛋白质（正向指标）
- E = 能量合理性（正向指标，越接近理想能量区间得分越高）
- S = 标准化糖（负向指标）
- F = 标准化脂肪（负向指标）
- N = 标准化钠（负向指标）

最终映射为 0~100 分的健康指数，用于同类商品排序。

## 数据处理流程

原始数据（48 条，含脏数据）经过四步清洗：

1. **品类筛选** —— 只保留酸奶品类
2. **单位统一** —— 钠 g→mg、能量 kJ→kcal
3. **缺失值处理** —— 关键营养字段缺失的记录删除
4. **异常值过滤** —— 剔除超出合理范围的样本

清洗后得到 42 条标准化商品数据。

## 快速开始

```bash
# 1. 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
streamlit run app.py
```

浏览器访问 `http://localhost:8501` 即可。

## 项目结构

```
foodinsight/
├── app.py                     # 主入口（项目首页）
├── pages/
│   ├── 1_数据概览.py           # 模块一
│   ├── 2_竞品定位分析.py        # 模块二
│   ├── 3_商品对比.py           # 模块三
│   └── 4_智能选品Agent.py      # 模块四
├── core/
│   ├── data_loader.py         # 数据加载与清洗
│   ├── health_index.py        # HI 计算（权重方案 + 标准化）
│   └── report_generator.py    # 竞品分析报告生成
├── data/
│   └── yogurt_products.csv    # 酸奶商品数据（含演示用脏数据）
├── .streamlit/config.toml     # 主题配置
├── requirements.txt
└── README.md
```

## 技术栈

- **Streamlit** —— Web 前端框架
- **Pandas / NumPy** —— 数据清洗与数值计算
- **Plotly** —— 交互式可视化（散点图、雷达图、直方图、箱线图）
- **Scikit-learn** —— 仅使用 `MinMaxScaler` 做标准化

## 后续扩展

- 替换为 OpenFoodFacts 真实数据（1000~3000 条酸奶商品）
- 增加更多品类（饮料、麦片等）
- 支持导出选品报告为 PDF
