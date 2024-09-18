import os

import torch
from emotion_analysis.src.model import BERTSentimentClassifier
from transformers import BertTokenizer
import yaml


class ModelInference:
    def __init__(self, config_path='./_internal/emotion_analysis/configs/config.yaml',
                 model_path='./_internal/emotion_analysis/experiments/train/best.pt'):
        # 检测绝对路径
        abs_path = os.path.abspath("./")

        # 输出绝对路径，帮助调试
        print(f"文件路径: {abs_path}")

        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 初始化tokenizer
        self.tokenizer = BertTokenizer.from_pretrained(self.config['model']['pretrained_model_name'])

        # 加载模型
        num_labels = 10  # 类别数
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = BERTSentimentClassifier(self.config['model']['pretrained_model_name'], num_labels,
                                             self.config['model']['dropout'])
        self.model.load_state_dict(torch.load(model_path, weights_only=True))
        self.model = self.model.to(self.device)
        self.model.eval()

        # 类别映射和分数映射
        self.labels = ["绝望、羞愧", "悲伤、痛苦", "恐惧、焦虑", "愤怒、不满", "警惕、不耐烦",
                       "厌倦、冷淡", "平淡、淡定", "乐观、认可", "坚定、勇气", "幸福、喜悦"]
        self.scores = ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90"]

    def preprocess(self, text):
        # 将文本编码为模型输入格式
        inputs = self.tokenizer(
            text,
            max_length=self.config['data']['max_seq_length'],
            padding='max_length',
            truncation=True,
            return_tensors="pt",
        )
        return inputs

    def predict(self, text):
        # 预处理输入文本
        inputs = self.preprocess(text)
        input_ids = inputs['input_ids'].to(self.device)
        attention_mask = inputs['attention_mask'].to(self.device)

        # 模型推理
        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask)
            _, predicted_label_index = torch.max(outputs, dim=1)

        # 映射预测结果
        predicted_label = self.labels[predicted_label_index.item()]
        predicted_score = self.scores[predicted_label_index.item()]

        return predicted_label, predicted_score


# 示例使用：
if __name__ == "__main__":
    model_inference = ModelInference()
    text = "??我你妈的，我真是服了。人生还有什么意义？死了算了！"
    label, score = model_inference.predict(text)
    print(f"预测类别: {label}, 预测分数: {score}")
