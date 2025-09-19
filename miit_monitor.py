'''
name: 工信部入网证书监测
cron: 0 8-21 * * *
'''

from utils.ql_utils import QLUtils
import os
import requests
from  utils.notify_utils import BarkNotify
def miit_monitor(model): 
    url=f'https://jwxk.miit.gov.cn/dev-api-20/internetService/CertificateQuery?equipmentModel={model}&sort=desc&pageNo=1&pageSize=10&isphoto=1&licenseNo=&equipmentCategory=&applyOrg=&manufacturingEnterpriseCname=&equipmentName=&startDate=&endDate='
    result=requests.get(url).json()
    if result.get('code') == 200:
        print(f'{model}入网证书信息如下：')
        for i in result.get('data').get('records'):
            licenseNo = i.get('licenseNo')
            acceptId = i.get('acceptId')
            print(f'设备{model}已获取入网证书：{licenseNo},批准编号为：{acceptId}')
            BarkNotify().send_notify(f'{model}已获取入网证书',f'设备{model}已获取入网证书：{licenseNo},批准编号为：{acceptId}',group='miit_monitor',url=f'https://jwxk.miit.gov.cn/showPhotos?lic={licenseNo}&acceptId={acceptId}')
        QLUtils.disable_self()

if __name__ == '__main__':
    miit_model=os.environ.get("miit_model")
    if miit_model is None:
        QLUtils.disable_self()
    else:
        miit_monitor(miit_model)
    
