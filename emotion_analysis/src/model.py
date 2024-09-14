import torch
import torch.nn as nn
from transformers import BertModel


class BERTSentimentClassifier(nn.Module):
    def __init__(self, pretrained_model_name, num_labels, dropout=0.3, fine_tune_last_n_layers=0):
        """
        初始化BERT情感分类模型
        :param pretrained_model_name: 预训练模型的名称
        :param num_labels: 分类任务的类别数
        :param dropout: dropout 概率
        :param fine_tune_last_n_layers: 微调BERT的最后n层（0表示不微调任何层）
        """
        super(BERTSentimentClassifier, self).__init__()
        self.bert = BertModel.from_pretrained(pretrained_model_name)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(768, num_labels)  # 输出类别数

        # 获取 BERT 模型的总层数
        total_layers = len(self.bert.encoder.layer)

        # 检查传入的fine_tune_last_n_layers是否大于总层数
        if fine_tune_last_n_layers >= total_layers:
            print(f"Warning: fine_tune_last_n_layers ({fine_tune_last_n_layers}) 大于 BERT 总层数 ({total_layers})，将只微调最后 {total_layers} 层。")
            fine_tune_last_n_layers = total_layers  # 限制微调的层数为最大值

        # 冻结除最后 n 层以外的所有层
        freeze_layers = total_layers - fine_tune_last_n_layers

        for i in range(freeze_layers):
            for param in self.bert.encoder.layer[i].parameters():
                param.requires_grad = False

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs[1]  # [CLS] token
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        return logits
