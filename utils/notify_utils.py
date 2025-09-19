import requests
import os
class BarkNotify:
    @staticmethod
    def send_notify(title, body, group=None,url=None):
        '''
            发送推送
        '''
        data = {
            'title': title,
            'body': body,
            'level' : 'critical',
            'isArchive' : 1,
        }
        if group:
            data['group'] = group
        if url:
            data['url'] = url
        requests.post(os.environ.get('NOTIFY_API'), data=data)