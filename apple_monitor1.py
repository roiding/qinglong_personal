'''
name: 苹果ESIM说明页面更新监测
cron: */10 8-24 * * *
'''
import requests
from utils.notify_utils import BarkNotify
from utils.ql_utils import QLUtils
import datetime
import os
import sys
import traceback
match_data = [{
    "name": "苹果大陆ESIM中文说明页面",
    "url": "https://support.apple.com/zh-cn/123879",
    "etag": "a56T1AULltDRsAug28JD4Z110--gzip",
    "last-modified": "Tue, 09 Sep 2025 18:25:13 GMT"
}, {
    "name": "苹果大陆ESIM英文说明页面",
    "url": "https://support.apple.com/en-us/123879",
    "etag": "a56T1AULltDRsAug28JD4Z110--gzip",
    "last-modified": "Fri, 12 Sep 2025 00:06:12 GMT"
}]
if __name__ == '__main__':
    try:
        # 部署有前缀的话，需要适配
        if os.environ.get("QlBaseUrl") is not None:
            QLUtils.set_config(
                host=f'http://127.0.0.1:5700{os.environ.get("QlBaseUrl")}/open')
        for item in match_data:
            headers = {
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "If-None-Match": item["etag"],
                "If-Modified-Since": item["last-modified"]
            }
            response = requests.get(item["url"], headers=headers)
            if response.status_code == 200:
                last_modified = response.headers.get("Last-Modified")
                # 把last_modified的GMT时间转成本地时间和现在进行比较，1小时内才提示
                if (datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT") - datetime.now()).total_seconds() > 60 * 60:
                    print(f"{item['name']}已更新")
                    BarkNotify().send_notify(
                        f"{item['name']}已更新", f"{item['name']}已更新", 'applestore', item['url'])
                    QLUtils.disable_self()
    except Exception as e:
        print("脚本执行出错:", e)
        traceback.print_exc(file=sys.stdout)
