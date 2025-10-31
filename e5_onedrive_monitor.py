'''
name: E5 OneDrive使用情况监控
cron: 0 9 * * *
'''

import os
import sys
import asyncio
import traceback
from typing import List, Dict, TypedDict, Optional
from datetime import datetime
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

# 加载 .env 文件（本地开发时使用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 青龙面板环境中可能没有 dotenv，跳过
    pass


class UserOneDriveInfo(TypedDict):
    """OneDrive使用信息数据结构"""
    user_email: str
    user_name: str
    used_gb: float
    total_gb: float
    usage_percentage: float
    remaining_gb: float
    last_activity: Optional[str]


class E5Config:
    """E5 配置管理"""
    def __init__(self):
        self.tenant_id = os.getenv('E5_TENANT_ID', '')
        self.client_id = os.getenv('E5_CLIENT_ID', '')
        self.client_secret = os.getenv('E5_CLIENT_SECRET', '')
        # 用户前缀筛选，默认为 "Salted Fish"
        self.user_prefix = os.getenv('E5_USER_PREFIX', 'Salted Fish')

    def validate(self) -> bool:
        """验证必要配置是否存在"""
        if not self.tenant_id or not self.client_id or not self.client_secret:
            print("错误: 缺少必要的环境变量配置")
            print("请设置: E5_TENANT_ID, E5_CLIENT_ID, E5_CLIENT_SECRET")
            return False
        return True


class OneDriveMonitor:
    """OneDrive 使用情况监控"""

    def __init__(self, config: E5Config):
        self.config = config
        credential = ClientSecretCredential(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=config.client_secret
        )
        self.graph_client = GraphServiceClient(credentials=credential)

    async def get_all_users(self) -> List[Dict]:
        """获取所有用户列表"""
        try:
            # 使用 query_parameters 明确指定要返回的字段
            from msgraph.generated.users.users_request_builder import UsersRequestBuilder

            query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
                select=['id', 'userPrincipalName', 'displayName', 'accountEnabled']
            )
            request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
                query_parameters=query_params
            )

            result = await self.graph_client.users.get(request_configuration=request_config)
            if result and result.value:
                return [
                    {
                        'id': user.id,
                        'userPrincipalName': user.user_principal_name,
                        'displayName': user.display_name,
                        'accountEnabled': user.account_enabled
                    }
                    for user in result.value
                ]
            return []
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """根据邮箱获取用户信息"""
        try:
            from msgraph.generated.users.item.user_item_request_builder import UserItemRequestBuilder

            query_params = UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
                select=['id', 'userPrincipalName', 'displayName', 'accountEnabled']
            )
            request_config = UserItemRequestBuilder.UserItemRequestBuilderGetRequestConfiguration(
                query_parameters=query_params
            )

            user = await self.graph_client.users.by_user_id(email).get(request_configuration=request_config)
            if user:
                return {
                    'id': user.id,
                    'userPrincipalName': user.user_principal_name,
                    'displayName': user.display_name,
                    'accountEnabled': user.account_enabled
                }
            return None
        except Exception as e:
            print(f"获取用户 {email} 失败: {e}")
            return None

    async def get_user_drive_info(self, user_id: str) -> Optional[Dict]:
        """获取用户的 OneDrive 信息"""
        try:
            drive = await self.graph_client.users.by_user_id(user_id).drive.get()
            if drive:
                return {
                    'quota': {
                        'total': drive.quota.total if drive.quota else 0,
                        'used': drive.quota.used if drive.quota else 0
                    },
                    'lastModifiedDateTime': str(drive.last_modified_date_time) if drive.last_modified_date_time else None
                }
            return None
        except Exception as e:
            print(f"获取用户 Drive 信息失败: {e}")
            return None

    async def get_user_onedrive_usage(self, user_info: Dict) -> Optional[UserOneDriveInfo]:
        """获取单个用户的 OneDrive 使用情况"""
        try:
            user_id = user_info.get('id')
            user_email = user_info.get('userPrincipalName', 'Unknown')
            user_name = user_info.get('displayName', 'Unknown')

            drive_info = await self.get_user_drive_info(user_id)
            if not drive_info:
                print(f"  ✗ 无法获取 {user_email} 的 OneDrive 信息")
                return None

            quota = drive_info.get('quota', {})
            total = quota.get('total', 0)
            used = quota.get('used', 0)

            # 转换为 GB
            total_gb = total / (1024 ** 3)
            used_gb = used / (1024 ** 3)
            remaining_gb = total_gb - used_gb
            usage_percentage = (used / total * 100) if total > 0 else 0

            last_activity = drive_info.get('lastModifiedDateTime', None)

            return UserOneDriveInfo(
                user_email=user_email,
                user_name=user_name,
                used_gb=round(used_gb, 2),
                total_gb=round(total_gb, 2),
                usage_percentage=round(usage_percentage, 2),
                remaining_gb=round(remaining_gb, 2),
                last_activity=last_activity
            )
        except Exception as e:
            print(f"  ✗ 获取用户 OneDrive 使用情况时出错: {e}")
            return None

    async def get_all_users_usage(self) -> List[UserOneDriveInfo]:
        """获取所有指定前缀开头的用户的 OneDrive 使用情况"""
        results = []
        user_prefix = self.config.user_prefix

        print("正在获取所有用户列表...")
        all_users = await self.get_all_users()
        print(f"找到 {len(all_users)} 个用户")

        if len(all_users) == 0:
            print("没有获取到任何用户")
            return []

        # 先过滤启用的用户
        enabled_users = [u for u in all_users if u.get('accountEnabled') is True]
        print(f"其中 {len(enabled_users)} 个用户已启用")

        # 筛选以指定前缀开头的用户
        target_users = []
        for user in enabled_users:
            display_name = user.get('displayName', '')
            user_email = user.get('userPrincipalName', '')

            # 检查显示名称或邮箱是否以指定前缀开头
            if display_name.startswith(user_prefix) or user_email.startswith(user_prefix):
                target_users.append(user)

        print(f"筛选出 {len(target_users)} 个以 '{user_prefix}' 开头的用户\n")

        for user in target_users:
            email = user.get('userPrincipalName', 'Unknown')
            display_name = user.get('displayName', 'Unknown')
            print(f"  查询用户: {display_name} ({email})")
            usage = await self.get_user_onedrive_usage(user)
            if usage:
                results.append(usage)

        return results


class ReportGenerator:
    """报表生成器"""

    @staticmethod
    def generate_push_report(users_data: List[UserOneDriveInfo]) -> str:
        """生成适合推送的简洁文本格式报表"""
        if not users_data:
            return "📊 E5 OneDrive 监控\n\n无数据"

        # 统计信息
        total_used = sum(u['used_gb'] for u in users_data)
        total_capacity = sum(u['total_gb'] for u in users_data)
        avg_usage = sum(u['usage_percentage'] for u in users_data) / len(users_data)

        report_lines = [
            "📊 E5 OneDrive 使用报告",
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"📈 统计: {len(users_data)}个用户",
            f"💾 总用量: {total_used:.1f}/{total_capacity:.0f} GB",
            f"📊 平均: {avg_usage:.1f}%",
            "",
            "👤 用户详情:"
        ]

        # 按使用率排序
        sorted_data = sorted(users_data, key=lambda x: x['usage_percentage'], reverse=True)

        for _, user in enumerate(sorted_data, 1):
            # 使用率状态
            if user['usage_percentage'] > 80:
                status = "🔴"
            elif user['usage_percentage'] > 50:
                status = "🟡"
            else:
                status = "🟢"

            # 简化用户名显示
            name = user['user_name'].replace('Salted Fish-', '')

            report_lines.append(
                f"{status} {name}: {user['used_gb']:.1f}GB ({user['usage_percentage']:.1f}%) "
                f"剩余{user['remaining_gb']:.1f}GB"
            )

        return "\n".join(report_lines)


async def main():
    """主函数"""
    try:
        print("=" * 60)
        print("E5 OneDrive 使用情况监控脚本")
        print("=" * 60)

        config = E5Config()
        if not config.validate():
            return

        print(f"租户ID: {config.tenant_id}")
        print(f"应用ID: {config.client_id}")
        print(f"筛选规则: 只查询以 '{config.user_prefix}' 开头的账号")
        print()

        monitor = OneDriveMonitor(config)
        users_data = await monitor.get_all_users_usage()

        if not users_data:
            print("未获取到任何用户数据")
            return

        print()
        print("=" * 60)

        report = ReportGenerator.generate_push_report(users_data)
        print(report)

        # 发送推送通知
        try:
            from utils.notify_utils import BarkNotify
            print("\n正在发送推送通知...")
            result = BarkNotify().send_notify("E5 OneDrive 监控报告", report, 'microsoft')
            if result:
                print(f"✓ 推送通知已发送，响应: {result}")
            else:
                print("✓ 推送通知请求已发送")
        except Exception as e:
            print(f"✗ 推送通知发送失败: {e}")

        print("\n✓ 监控完成")

    except Exception as e:
        print(f"\n✗ 脚本执行出错: {e}")
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())
