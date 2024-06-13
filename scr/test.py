import requests
# 发送HTTP请求
response = requests.get("https://zhuanlan.zhihu.com/p/372543679")
# 获取响应Cookies
cookies = response.cookies
# 打印Cookies
for cookie in cookies:
    print(cookie.name, ":", cookie.value)