'''
name: AxCNH监控脚本
cron: */10 * * * *
'''

# 监控AxCNH的监管账号的余额变更
from typing import TypedDict
import os
import json
import requests
from notify_utils import BarkNotify
import sys, traceback
class Data(TypedDict):
    """
    数据结构
    """
    AxCNH_supply: str
    AxCNH_bank_balance: str
# 直接使用conflux_web3去跟踪的话有点麻烦，采用confluxscan的API方式
class ConfluxScan:
    def __init__(self):
        self.api= 'https://api.confluxscan.org'
        self.evmapi = 'https://evmapi.confluxscan.org'
    def get_token_supply(self, contract_address):
        """
        获取代币的供应量
        """
        url = self.evmapi + f'/api?module=stats&action=tokensupply&contractaddress={contract_address}'
        return requests.get(url).json().get('result')
    def get_token_banlance(self, contract_address, address):
        """
        获取代币的余额
        """
        url = self.evmapi + f'/api?module=account&action=tokenbalance&contractaddress={contract_address}&address={address}'
        return requests.get(url).json().get('result')
class DataFile:
    def __init__(self):
        self.file_path = '/ql/data/AxCNH_result.json'
    def read(self)->Data:
        # 检查文件是否存在
        if os.path.exists(self.file_path):
            return json.loads(open(self.file_path, 'r', encoding='utf-8').read())
        return None
    def write(self, data: Data):
        # 检查文件是否存在
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
if __name__ == "__main__":
    try:
        AxCNH_contract_address = '0x70bfd7f7eadf9b9827541272589a6b2bb760ae2e'
        bank_address = '0xf8fC002aAE4F42B7aafE9Ef43eCca1C3EDA15D8e'
        api = ConfluxScan()
        # 获取代币供应量
        AxCNH_supply=api.get_token_supply(AxCNH_contract_address)
        print(f"AxCNH代币供应量:{AxCNH_supply}")
        # 获取现存已知的受信账户代币的余额
        AxCNH_bank_balance=api.get_token_banlance(AxCNH_contract_address,bank_address)
        print(f"AxCNH代币收信账户余额:{AxCNH_bank_balance}")
        data_file = DataFile()
        result = data_file.read()
        class Num_Format:
            '''
            数字格式化
            '''
            @staticmethod
            def format_number(num_str):
                '''
                将数字字符串格式化为带单位的显示格式(K, M, B等)
                '''
                try:
                    num = float(num_str)
                    if num >= 1e9:
                        return f"{num/1e9:.2f}B"
                    elif num >= 1e6:
                        return f"{num/1e6:.2f}M"
                    elif num >= 1e3:
                        return f"{num/1e3:.2f}K"
                    else:
                        return str(num)
                except (ValueError, TypeError):
                    return num_str
        
        if result:
            if result.get('AxCNH_supply') != AxCNH_supply:
                old_formatted = Num_Format.format_number(result.get('AxCNH_supply'))
                new_formatted = Num_Format.format_number(AxCNH_supply)
                BarkNotify.send_notify('代币总供应量出现变动', f'从 {old_formatted} 变更为 {new_formatted}',group='AxCNH',url=f'https://evm.confluxscan.org/token/{AxCNH_contract_address}')
            if result.get('AxCNH_bank_balance') != AxCNH_bank_balance:
                old_formatted = Num_Format.format_number(result.get('AxCNH_bank_balance'))
                new_formatted = Num_Format.format_number(AxCNH_bank_balance)
                BarkNotify.send_notify('授权银行余额出现变动',f'从 {old_formatted} 变更为 {new_formatted}',group='AxCNH',url=f'https://evm.confluxscan.org/address/{bank_address}')

        
        file_result = {
            'AxCNH_supply':AxCNH_supply,
            'AxCNH_bank_balance':AxCNH_bank_balance,
        }
        data_file.write(file_result)
    except Exception as e:
        print("脚本执行出错:", e)
        traceback.print_exc(file=sys.stdout)