'''
name: E5 个人账号监控
cron: */10 8-22 * * *
'''

import os
import sys
import asyncio
import traceback
from datetime import datetime
from azure.identity import UsernamePasswordCredential
from msgraph import GraphServiceClient

# 加载 .env 文件（本地开发时使用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 青龙面板环境中可能没有 dotenv，跳过
    pass


class E5Config:
    """E5 配置管理"""
    def __init__(self):
        self.tenant_id = os.getenv('E5_TENANT_ID', '')
        self.client_id = os.getenv('E5_CLIENT_ID', '')
        # 使用委托权限，需要用户名密码
        self.username = os.getenv('E5_KEEPER_USERNAME', '')
        self.password = os.getenv('E5_KEEPER_PASSWORD', '')

    def validate(self) -> bool:
        """验证必要配置是否存在"""
        if not self.tenant_id or not self.client_id or not self.username or not self.password:
            print("错误: 缺少必要的环境变量配置")
            print("请设置: E5_TENANT_ID, E5_CLIENT_ID, E5_KEEPER_USERNAME, E5_KEEPER_PASSWORD")
            return False
        return True


class E5ActivityKeeper:
    """E5 活跃保持器（使用委托权限）"""

    def __init__(self, config: E5Config):
        self.config = config
        # 使用用户名密码认证（委托权限）
        credential = UsernamePasswordCredential(
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            tenant_id=config.tenant_id
        )
        self.graph_client = GraphServiceClient(credentials=credential)

    async def read_my_mail(self):
        """读取我的邮件"""
        try:
            # 直接读取邮件，不使用复杂的 query_params
            result = await self.graph_client.me.messages.get()

            mail_count = len(result.value) if result and result.value else 0
            return mail_count

        except Exception as e:
            print(f"    邮件读取失败: {e}")
            return -1

    async def read_my_todo(self):
        """读取我的 To Do 列表"""
        try:
            # 直接读取 To Do 列表
            result = await self.graph_client.me.todo.lists.get()

            todo_count = len(result.value) if result and result.value else 0
            return todo_count

        except Exception as e:
            print(f"    To Do 读取失败: {e}")
            return -1

    async def read_my_calendar(self):
        """读取我的日历"""
        try:
            # 直接读取日历事件
            result = await self.graph_client.me.events.get()

            event_count = len(result.value) if result and result.value else 0
            return event_count

        except Exception as e:
            print(f"    日历读取失败: {e}")
            return -1

    async def keep_active(self):
        """保持账号活跃"""
        print(f"  账号: {self.config.username}")

        # 读取邮件
        mail_count = await self.read_my_mail()
        if mail_count >= 0:
            print(f"    ✓ 邮件: {mail_count} 封")

        # 读取 To Do
        todo_count = await self.read_my_todo()
        if todo_count >= 0:
            print(f"    ✓ To Do: {todo_count} 个列表")

        # 读取日历
        event_count = await self.read_my_calendar()
        if event_count >= 0:
            print(f"    ✓ 日历: {event_count} 个事件")

        # 只要有一个成功就算成功
        return mail_count >= 0 or todo_count >= 0 or event_count >= 0


async def main():
    """主函数"""
    try:
        current_time = datetime.now()
        hour = current_time.hour

        # 检查是否在活跃时间段内（8:00-22:00）
        if hour < 8 or hour >= 22:
            print(f"当前时间 {current_time.strftime('%H:%M')} 不在活跃时间段内 (08:00-22:00)")
            return

        print("=" * 60)
        print(f"E5 API 活跃保持 - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        config = E5Config()
        if not config.validate():
            return

        keeper = E5ActivityKeeper(config)

        print("\n正在调用 Graph API 保持活跃...")
        success = await keeper.keep_active()

        print()
        print("=" * 60)
        if success:
            print("✓ 活跃保持成功")
        else:
            print("✗ 活跃保持失败")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 脚本执行出错: {e}")
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())


