import yaml
from scr.wechat import WeChatPyQReader

def load_config(config_file):
    with open(config_file, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == '__main__':
    config = load_config('config.yaml')
    save_path = config['wechat_save_path']
    wechat = WeChatPyQReader()
    df = wechat.get_pyq_data()
    print(df)
    wechat.save_to_excel(df, save_path)
print("done")