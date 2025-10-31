import requests
import os
from urllib.parse import quote

class BarkNotify:
    @staticmethod
    def send_notify(title, body, group=None, url=None):
        '''
            发送推送（按照官方 POST JSON 格式）
        '''
        notify_api = os.environ.get('NOTIFY_API')
        if not notify_api:
            return

        # 按照官方示例构建 JSON body
        payload = {
            'title': quote(title),
            'body': quote(body),
            'level': 'critical',
            'isArchive': 1
        }

        # 可选参数
        if group:
            payload['group'] = group
        if url:
            payload['url'] = url

        result = requests.post(notify_api, json=payload).json()
        return result