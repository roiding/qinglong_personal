'''
name: 国行苹果Air购买界面监测
cron: */5 * * * *
'''
import requests
from utils.notify_utils import BarkNotify
from utils.ql_utils import QLUtils
import os
import sys
import traceback


def extract_final_buyability(data):
    """
    提取 stores、sticky、regular 三个字段的 buyability.isBuyable 最终结果
    :param data: dict 或 list
    :return: dict，形如 { "stores": True, "sticky": False, "regular": True }
    """
    sources = ["stores", "sticky", "regular"]
    result = {src: None for src in sources}  # 先设为空

    def recursive_scan(sub_data, current_source=None):
        if isinstance(sub_data, dict):
            for k, v in sub_data.items():
                if k in sources:
                    recursive_scan(v, current_source=k)
                elif k == "buyability" and isinstance(v, dict) and "isBuyable" in v:
                    if current_source and result[current_source] is None:  # 只取第一个结果
                        result[current_source] = v["isBuyable"]
                else:
                    recursive_scan(v, current_source)
        elif isinstance(sub_data, list):
            for item in sub_data:
                recursive_scan(item, current_source)

    recursive_scan(data)

    # 如果有的来源没有找到，默认设为 False
    for src in sources:
        if result[src] is None:
            result[src] = False

    return result


if __name__ == '__main__':
    try:
        # 部署有前缀的话，需要适配
        if os.environ.get("QlBaseUrl") is not None:
            QLUtils.set_config(
                host=f'http://127.0.0.1:5700{os.environ.get("QlBaseUrl")}/open')
        # 下面是对国行air购买界面直接监控
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        }
        result = requests.get(
            'https://www.apple.com.cn/shop/buyability-message?parts.0=MG3C4CH/A', headers=headers).json()
        buyabilityMessage = result.get('body').get(
            'content').get('buyabilityMessage')
        if ('sth' in buyabilityMessage and buyabilityMessage.get('sth').get('MG3C4CH/A').get('isBuyable')) or ('apu' in buyabilityMessage and buyabilityMessage.get('apu').get('MG3C4CH/A').get('isBuyable')):
            BarkNotify().send_notify(f'国行Air已开启官网购买', f'国行Air已开启官网购买', 'applestore',
                                     'https://www.apple.com.cn/shop/buy-iphone/iphone-air/MG3C4CH/A')
            QLUtils.disable_self()

        response = requests.get(
            "https://www.apple.com.cn/shop/fulfillment-messages?fae=true&little=false&parts.0=MG3C4CH/A&mts.0=regular&mts.1=sticky&fts=true", headers=headers).json()
        result = final_result = extract_final_buyability(response)
        if result.get('stores') or result.get('sticky') or result.get('regular'):
            BarkNotify().send_notify(f'国行Air已开启官网购买', f'国行Air已开启官网购买', 'applestore',
                                     'https://www.apple.com.cn/shop/buy-iphone/iphone-air/MG3C4CH/A')
            QLUtils.disable_self()

    except Exception as e:
        print("脚本执行出错:", e)
        traceback.print_exc(file=sys.stdout)
