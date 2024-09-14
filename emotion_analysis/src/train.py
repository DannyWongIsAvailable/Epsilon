import torch
import torch.nn as nn
import torch.optim as optim
from transformers import BertTokenizer
from model import BERTSentimentClassifier  # 确保你已将回归模型改为分类模型
from data_loader import create_dataloader
import yaml
import os
from tqdm import tqdm  # 进度条库
import time  # 记录时间
import logging  # 日志模块
from sklearn.metrics import accuracy_score  # 用于计算准确率


# 设置日志记录
def setup_logging(log_file):
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


# 读取配置文件
with open('../configs/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 初始化tokenizer
tokenizer = BertTokenizer.from_pretrained(config['model']['pretrained_model_name'], clean_up_tokenization_spaces=True)

# 创建数据加载器
train_dataloader = create_dataloader(config['data']['train_path'], tokenizer, config['data']['max_seq_length'],
                                     config['training']['batch_size'], is_train=True)
val_dataloader = create_dataloader(config['data']['val_path'], tokenizer, config['data']['max_seq_length'],
                                   config['training']['batch_size'], is_train=True)

# 初始化模型（改为分类模型），并微调指定的最后n层
num_labels = 10  # 假设有 10 个类别
fine_tune_last_n_layers = config['model'].get('freeze_layers', 0)  # 从配置文件中读取微调层数

# 初始化模型并传入微调层数
model = BERTSentimentClassifier(
    config['model']['pretrained_model_name'],
    num_labels,
    config['model']['dropout'],
    fine_tune_last_n_layers=fine_tune_last_n_layers  # 仅微调最后n层
)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = model.to(device)

# 定义损失函数和优化器
loss_fn = nn.CrossEntropyLoss()  # 对于分类任务，使用CrossEntropyLoss
optimizer = optim.AdamW(model.parameters(), lr=config['training']['learning_rate'],
                        weight_decay=config['training']['weight_decay'])


# 设置保存模型路径
def get_experiment_dir(base_dir):
    """自动生成递增的实验文件夹路径"""
    experiment_id = 1
    while True:
        experiment_dir = os.path.join(base_dir, f"experiment_{experiment_id}")
        if not os.path.exists(experiment_dir):
            os.makedirs(experiment_dir, exist_ok=True)
            return experiment_dir
        experiment_id += 1


# 使用函数生成带序号的实验文件夹
base_experiment_dir = '../experiments'
experiment_dir = get_experiment_dir(base_experiment_dir)
best_model_path = os.path.join(experiment_dir, 'best.pt')
log_file = os.path.join(experiment_dir, 'training.log')  # 日志文件路径

# 设置日志记录到文件和控制台
setup_logging(log_file)
logging.info(f"模型和日志将保存到: {experiment_dir}")

# 初始化变量，用于保存最佳模型
best_val_loss = float('inf')

# 记录训练开始时间
start_time = time.time()

total_epochs = config['training']['num_epochs']
# 训练循环
for epoch in range(total_epochs):
    model.train()
    correct_predictions = 0
    total_predictions = 0
    train_loss = 0.0

    # 在每个 epoch 中，使用 tqdm 包装训练数据加载器，显示进度条
    train_progress_bar = tqdm(enumerate(train_dataloader), total=len(train_dataloader),
                              desc=f"Epoch {epoch + 1}/{total_epochs}")

    for step, batch in train_progress_bar:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)  # 分类任务中的标签

        optimizer.zero_grad()
        outputs = model(input_ids, attention_mask)

        # 计算损失
        loss = loss_fn(outputs, labels)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()

        # 计算准确率
        _, preds = torch.max(outputs, dim=1)
        correct_predictions += torch.sum(preds == labels)
        total_predictions += labels.size(0)

        # 更新进度条中的损失值
        train_progress_bar.set_postfix({'Loss': loss.item()})

    train_accuracy = correct_predictions.double() / total_predictions
    avg_train_loss = train_loss / len(train_dataloader)
    logging.info(f"Epoch {epoch + 1}, Train Loss: {avg_train_loss}, Train Accuracy: {train_accuracy:.4f}")

    # 验证集评估
    model.eval()
    total_val_loss = 0
    correct_val_predictions = 0
    total_val_predictions = 0

    with torch.no_grad():
        val_progress_bar = tqdm(enumerate(val_dataloader), total=len(val_dataloader), desc=f"Validation {epoch}")

        for step, batch in val_progress_bar:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)
            outputs = model(input_ids, attention_mask)

            # 计算损失
            loss = loss_fn(outputs, labels)
            total_val_loss += loss.item()

            # 计算验证集准确率
            _, preds = torch.max(outputs, dim=1)
            correct_val_predictions += torch.sum(preds == labels)
            total_val_predictions += labels.size(0)

    avg_val_loss = total_val_loss / len(val_dataloader)
    val_accuracy = correct_val_predictions.double() / total_val_predictions
    logging.info(f"Epoch {epoch + 1}, Validation Loss: {avg_val_loss}, Validation Accuracy: {val_accuracy:.4f}")

    # 如果验证集损失下降，保存模型
    if avg_val_loss < best_val_loss:
        best_val_loss = avg_val_loss
        torch.save(model.state_dict(), best_model_path)
        logging.info(f"Best model saved with Validation Loss: {avg_val_loss}")

# 最终保存模型
final_model_path = os.path.join(experiment_dir, 'final.pt')
torch.save(model.state_dict(), final_model_path)
logging.info(f"Final model saved at {final_model_path}")

# 记录训练结束时间
end_time = time.time()

# 计算并显示训练总时长
total_time = end_time - start_time
hours, rem = divmod(total_time, 3600)
minutes, seconds = divmod(rem, 60)
logging.info(f"Training completed in {int(hours)}h {int(minutes)}m {int(seconds)}s")
