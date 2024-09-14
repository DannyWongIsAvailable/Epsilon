import os
import torch
from emotion_analysis.src.model import BERTSentimentClassifier  # 确保这是分类模型的导入
from emotion_analysis.src.data_loader import create_dataloader
from transformers import BertTokenizer
import yaml
import pandas as pd

# 读取配置文件
with open('../configs/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 初始化tokenizer
tokenizer = BertTokenizer.from_pretrained(config['model']['pretrained_model_name'])

# 加载测试集
test_dataloader = create_dataloader(
    config['data']['test_path'],
    tokenizer,
    config['data']['max_seq_length'],
    config['evaluation']['eval_batch_size'],
    is_train=False
)

# 加载分类模型
num_labels = 10  # 根据分类任务中类别数设定
model = BERTSentimentClassifier(config['model']['pretrained_model_name'], num_labels, config['model']['dropout'])
model.load_state_dict(torch.load('../experiments/train/best.pt'))
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)

# 定义类别映射和分数映射
labels = ["绝望、羞愧", "悲伤、痛苦", "恐惧、焦虑", "愤怒、不满", "警惕、不耐烦",
              "厌倦、冷淡", "平淡、淡定", "乐观、认可", "坚定、勇气", "幸福、喜悦"]
scores = ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90"]

# 评估模型
model.eval()
predicted_labels = []
predicted_scores = []
with torch.no_grad():
    for batch in test_dataloader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)

        # 模型输出为类别概率分布，取最大值作为预测类别
        outputs = model(input_ids, attention_mask)
        _, predicted_label_indices = torch.max(outputs, dim=1)

        # 将预测的整数索引映射回类别名称和分数
        predicted_labels.extend([labels[label] for label in predicted_label_indices.cpu().numpy()])
        predicted_scores.extend([scores[label] for label in predicted_label_indices.cpu().numpy()])

# 保存预测结果
test_data = pd.read_csv(config['data']['test_path'])
test_data['predicted_label'] = predicted_labels  # 保存预测的类别名称
test_data['predicted_score'] = predicted_scores  # 保存预测的分数

# 定义保存路径并检查文件是否存在，如果存在则递增序号
base_save_path = '../results/predictions.csv'
save_path = base_save_path

if os.path.exists(save_path):
    i = 1
    while os.path.exists(save_path):
        save_path = f"../results/predictions_{i}.csv"
        i += 1

# 保存预测结果到最终确定的路径
test_data.to_csv(save_path, encoding='utf-8-sig', index=False)
print(f"预测结果已保存到 {save_path}")
