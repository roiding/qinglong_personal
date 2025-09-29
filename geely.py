'''
name: 吉利自动签到脚本
cron: 0 8 * * *
'''
import os
from utils.geely.geely_panda_utils import GeelyUser

if __name__ == '__main__':
    # 获取环境变量
    user_cookie = os.environ.get("jlyh")
    
    if not user_cookie:
        print("未找到CK，请检查环境变量设置")
        exit(1)
    
    # 创建用户实例并执行签到
    user = GeelyUser(user_cookie)
    user.do_sign()
    