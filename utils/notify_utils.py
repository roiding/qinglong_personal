import requests
import os
from urllib.parse import quote

class BarkNotify:
    @staticmethod
    def send_notify(title, body, group=None, url=None):
        '''
            发送推送
        '''
        notify_api = os.environ.get('NOTIFY_API')
        if not notify_api:
            return

        # 构建 URL 路径（GET 方式）
        api_url = f"{notify_api}/{quote(title)}/{quote(body)}"

        # 添加查询参数
        params = {
            'level': 'critical',
            'isArchive': '1'
        }
        if group:
            params['group'] = group
        if url:
            params['url'] = url

        result = requests.get(api_url, params=params).json()
        return result