import pandas as pd

# 读取CSV文件
df = pd.read_csv('data_clear.csv')  # 将 'your_file.csv' 替换为你的文件名

# 删除“text”列中重复的行，保留最前的一条
df_unique = df.drop_duplicates(subset='text', keep='first')

# 将结果保存回CSV文件（可选）
df_unique.to_csv('data_clear1.csv', index=False, encoding='utf-8-sig')

print("去重后的数据已保存到新文件中。")
