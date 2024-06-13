import pandas as pd

class ExcelProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.header_dict = None
        self.data = None

    def read_excel(self):
        # 读取前四行，生成字典
        df_header = pd.read_excel(self.file_path, header=None, nrows=3)
        self.header_dict = {df_header.iloc[i, 0]: df_header.iloc[i, 1] for i in range(3)}

        # 检查'学校编号', '年级', '班级'是否为空
        required_keys = ['学校编号', '年级', '班级']
        for key in required_keys:
            if pd.isna(self.header_dict.get(key)):
                raise ValueError(f"'{key}' 不能为空")

        # 读取第5行之后的数据为DataFrame，并设置第5行作为列名
        dtype_spec = {
            "学号": str,
            "姓名": str,
            "性别": str,
            "年龄": str,
            "微信朋友圈": str,
            "qq空间": str,
            "微博": str

        }
        self.data = pd.read_excel(self.file_path, header=3, dtype=dtype_spec)

    def get_header_dict(self):
        return self.header_dict

    def get_data(self):
        return self.data

if __name__ == '__main__':
    # 使用示例
    file_path = '../example.xlsx'  # 请将路径替换为您的文件路径
    processor = ExcelProcessor(file_path)
    processor.read_excel()

    header_dict = processor.get_header_dict()
    data = processor.get_data()

    print("字典变量：", header_dict)
    print("DataFrame：")
    print(data)
