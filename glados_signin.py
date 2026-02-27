'''
name: glados签到
cron: 30 8 * * *
'''
import os
import requests
import json
# glados_token=os.environ.get("glados_token","")
glados_cookies=os.environ.get("glados_cookies","")
# 把字符串转数组 "["",""]"
cookies_list=json.loads(glados_cookies)
for cookie in cookies_list:
    requests.post("https://glados.cloud/api/user/checkin",json={"token":"glados.cloud"},headers={
        # "Authorization" : glados_token,
        "Cookie" : glados_cookies,
        "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    })
    result=requests.get("https://glados.cloud/api/user/status",headers={
        "Cookie" : glados_cookies,
        "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    }).json()
    print(f"{result['email']}签到成功！")
    