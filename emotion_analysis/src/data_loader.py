import pandas as pd
import torch
from transformers import BertTokenizer
from torch.utils.data import Dataset, DataLoader

categories = ["绝望、羞愧",  "悲伤、痛苦", "恐惧、焦虑","愤怒、不满", "警惕、不耐烦", "厌倦、冷淡", "平淡、淡定", "乐观、认可", "坚定、勇气", "幸福、喜悦"]

class SentimentDataset(Dataset):
    def __init__(self, file_path, tokenizer, max_length, is_train=True):
        self.data = pd.read_csv(file_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.is_train = is_train
        # 创建类别到索引的映射
        self.label_map = {category: idx for idx, category in enumerate(categories)}

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        text = self.data.iloc[idx]['text']

        # 确保 text 是字符串类型，如果不是则转换为字符串
        if not isinstance(text, str):
            text = str(text)  # 将非字符串类型的文本转换为字符串

        # 对文本进行编码
        inputs = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors="pt"
        )

        if self.is_train:
            category = self.data.iloc[idx]['category']
            if category not in self.label_map:
                raise KeyError(f"类别 '{category}' 不在预定义的 categories 列表中，请检查数据集中的类别拼写。")

            label = self.label_map[category]

            return {
                'input_ids': inputs['input_ids'].squeeze(0),
                'attention_mask': inputs['attention_mask'].squeeze(0),
                'label': torch.tensor(label, dtype=torch.long)
            }
        else:
            return {
                'input_ids': inputs['input_ids'].squeeze(0),
                'attention_mask': inputs['attention_mask'].squeeze(0)
            }


def create_dataloader(file_path, tokenizer, max_length, batch_size, is_train=True):
    """
    创建数据加载器，处理分类任务
    :param file_path: 数据集文件路径
    :param tokenizer: 用于BERT的tokenizer
    :param max_length: 序列的最大长度
    :param batch_size: 批量大小
    :param is_train: 是否是训练集。训练集需要category，测试集不需要
    :return: DataLoader 对象
    """
    dataset = SentimentDataset(file_path, tokenizer, max_length, is_train=is_train)
    return DataLoader(dataset, batch_size=batch_size, shuffle=is_train)
