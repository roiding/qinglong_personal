import requests
import os
from urllib.parse import quote
from enum import Enum

class BarkNotify:
    '''
        Bark 推送工具类
    '''
    class Level(Enum):
        '''   通知等级
        critical: 重要警告, 在静音模式下也会响铃
        active：默认值，系统会立即亮屏显示通知
        timeSensitive：时效性通知，可在专注状态下显示通知。
        passive：仅将通知添加到通知列表，不会亮屏提醒。
        '''
       
        CRITICAL = 'critical'
        ACTIVE = 'active'
        TIME_SENSITIVE = 'timeSensitive'
        PASSIVE = 'passive'

    @staticmethod
    def send_notify(title, body, group=None,level=Level.ACTIVE, url=None):
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
            'level': level.value,
            'isArchive': 1
        }

        # 可选参数
        if group:
            payload['group'] = group
        if url:
            payload['url'] = url

        result = requests.post(notify_api, json=payload).json()
        return result