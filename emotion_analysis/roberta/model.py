import torch
import torch.nn as nn
from transformers import AutoModel

class RoBerta(nn.Module):
    def __init__(self, pretrained_model_name, num_labels, dropout=0.3, fine_tune_last_n_layers=0):
        super(RoBerta, self).__init__()
        self.roberta = AutoModel.from_pretrained(pretrained_model_name)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.roberta.config.hidden_size, num_labels)

        total_layers = len(self.roberta.encoder.layer)
        if fine_tune_last_n_layers >= total_layers:
            print(f"Warning: fine_tune_last_n_layers ({fine_tune_last_n_layers}) 大于 RoBERTa 总层数 ({total_layers})，将只微调最后 {total_layers} 层。")
            fine_tune_last_n_layers = total_layers
        freeze_layers = total_layers - fine_tune_last_n_layers
        for i in range(freeze_layers):
            for param in self.roberta.encoder.layer[i].parameters():
                param.requires_grad = False

    def forward(self, input_ids, attention_mask):
        outputs = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
        last_hidden_state = outputs[0]  # 获取最后一层隐藏状态
        pooled_output = last_hidden_state[:, 0, :]  # 获取 [CLS] token 的表示
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        return logits
