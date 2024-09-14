import pandas as pd

# 读取CSV文件
df = pd.read_csv(r'F:\owl\Spider\sentiment_regression_project\data\train_score.csv')

# 定义分类标签和对应的分数区间
category = ["绝望、羞愧",  "悲伤、痛苦", "恐惧、焦虑", "愤怒、不满", "警惕、不耐烦", "厌倦、冷淡", "平淡、淡定", "乐观、认可", "坚定、勇气", "幸福、喜悦"]

# 定义函数，根据score值分配类别
def categorize(score):
    if score >= 0 and score <= 10:
        return "绝望、羞愧"
    elif score > 10 and score <= 20:
        return "悲伤、痛苦"
    elif score > 20 and score <= 30:
        return "恐惧、焦虑"
    elif score > 30 and score <= 40:
        return "愤怒、不满"
    elif score > 40 and score <= 50:
        return "警惕、不耐烦"
    elif score > 50 and score <= 60:
        return "厌倦、冷淡"
    elif score > 60 and score <= 70:
        return "平淡、淡定"
    elif score > 70 and score <= 80:
        return "乐观、认可"
    elif score > 80 and score <= 90:
        return "坚定、勇气"
    elif score > 90:
        return "幸福、喜悦"

# 增加新的列，应用分类函数
df['category'] = df['score'].apply(categorize)

# 保存结果到新的CSV文件
df.to_csv('train.csv', index=False,  encoding='utf-8-sig')

# 显示前几行
print(df.head())
