'''
name: E5 闲鱼用户有效期检查
cron: 0 9 * * *
'''

import os
import sys
import asyncio
import traceback
from typing import List, Dict, TypedDict
from datetime import datetime, timedelta, timezone
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient

# 加载 .env 文件（本地开发时使用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 青龙面板环境中可能没有 dotenv，跳过
    pass


class UserExpirationInfo(TypedDict):
    """用户有效期信息数据结构"""
    user_email: str
    user_name: str
    user_id: str
    created_date: datetime
    valid_years: int
    expire_date: datetime
    days_until_expire: int
    status: str  # 'active', 'near_expiry', 'expired'


class E5Config:
    """E5 配置管理"""
    def __init__(self):
        self.tenant_id = os.getenv('E5_TENANT_ID', '')
        self.client_id = os.getenv('E5_CLIENT_ID', '')
        self.client_secret = os.getenv('E5_CLIENT_SECRET', '')
        # 用户前缀筛选，默认为 "Salted Fish"
        self.user_prefix = os.getenv('E5_USER_PREFIX', 'Salted Fish')
        # 提前警告天数，默认 15 天
        self.warning_days = int(os.getenv('E5_WARNING_DAYS', '15'))

    def validate(self) -> bool:
        """验证必要配置是否存在"""
        if not self.tenant_id or not self.client_id or not self.client_secret:
            print("错误: 缺少必要的环境变量配置")
            print("请设置: E5_TENANT_ID, E5_CLIENT_ID, E5_CLIENT_SECRET")
            return False
        return True


class UserExpirationManager:
    """用户有效期管理"""

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
            from msgraph.generated.users.users_request_builder import UsersRequestBuilder

            query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
                select=['id', 'userPrincipalName', 'displayName', 'accountEnabled',
                       'createdDateTime', 'postalCode']
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
                        'accountEnabled': user.account_enabled,
                        'createdDateTime': user.created_date_time,
                        'postalCode': user.postal_code
                    }
                    for user in result.value
                ]
            return []
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []

    async def disable_user(self, user_id: str, user_email: str) -> bool:
        """禁用用户"""
        try:
            from msgraph.generated.models.user import User

            update_user = User()
            update_user.account_enabled = False

            await self.graph_client.users.by_user_id(user_id).patch(update_user)
            print(f"  ✓ 已禁用用户: {user_email}")
            return True
        except Exception as e:
            print(f"  ✗ 禁用用户失败 {user_email}: {e}")
            return False

    async def delete_user(self, user_id: str, user_email: str) -> bool:
        """删除用户"""
        try:
            await self.graph_client.users.by_user_id(user_id).delete()
            print(f"  ✓ 已删除用户: {user_email}")
            return True
        except Exception as e:
            print(f"  ✗ 删除用户失败 {user_email}: {e}")
            return False

    def calculate_expiration(self, users: List[Dict], user_prefix: str) -> List[UserExpirationInfo]:
        """计算用户有效期"""
        result = []
        now = datetime.now(timezone.utc)

        for user in users:
            display_name = user.get('displayName', '')
            user_email = user.get('userPrincipalName', '')

            # 筛选符合前缀的用户
            if not (display_name.startswith(user_prefix) or user_email.startswith(user_prefix)):
                continue

            # 检查是否有 postalCode（有效期年数），默认 1 年
            postal_code = user.get('postalCode')
            if postal_code and postal_code.isdigit():
                valid_years = int(postal_code)
            else:
                valid_years = 1

            created_date = user.get('createdDateTime')

            if not created_date:
                continue

            # 计算过期日期
            expire_date = created_date + timedelta(days=valid_years * 365)
            days_until_expire = (expire_date - now).days

            # 确定状态
            if days_until_expire < 0:
                status = 'expired'
            elif days_until_expire <= self.config.warning_days:
                status = 'near_expiry'
            else:
                status = 'active'

            result.append({
                'user_email': user_email,
                'user_name': display_name,
                'user_id': user.get('id'),
                'created_date': created_date,
                'valid_years': valid_years,
                'expire_date': expire_date,
                'days_until_expire': days_until_expire,
                'status': status,
                'account_enabled': user.get('accountEnabled', True)
            })

        return result

    async def process_expirations(self, users_info: List[UserExpirationInfo]) -> Dict:
        """处理过期用户"""
        stats = {
            'disabled': [],
            'deleted': [],
            'warned': [],
            'failed': []
        }

        for user in users_info:
            if user['status'] == 'expired':
                # 已过期，删除用户
                print(f"\n处理过期用户: {user['user_name']} ({user['user_email']})")
                print(f"  创建时间: {user['created_date'].strftime('%Y-%m-%d')}")
                print(f"  有效期: {user['valid_years']} 年")
                print(f"  已过期: {abs(user['days_until_expire'])} 天")

                success = await self.delete_user(user['user_id'], user['user_email'])
                if success:
                    stats['deleted'].append(user)
                else:
                    stats['failed'].append(user)

            elif user['status'] == 'near_expiry' and user.get('account_enabled', True):
                # 临近过期且未禁用，禁用用户
                print(f"\n处理临近过期用户: {user['user_name']} ({user['user_email']})")
                print(f"  创建时间: {user['created_date'].strftime('%Y-%m-%d')}")
                print(f"  有效期: {user['valid_years']} 年")
                print(f"  距离过期: {user['days_until_expire']} 天")

                success = await self.disable_user(user['user_id'], user['user_email'])
                if success:
                    stats['disabled'].append(user)
                else:
                    stats['failed'].append(user)

            elif user['status'] == 'near_expiry' and not user.get('account_enabled', True):
                # 已经禁用的临近过期用户，只记录
                stats['warned'].append(user)

        return stats


class ReportGenerator:
    """报表生成器"""

    @staticmethod
    def generate_report(stats: Dict, users_info: List[UserExpirationInfo]) -> str:
        """生成报表"""
        report_lines = [
            "📅 E5 用户有效期检查报告",
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ""
        ]

        # 统计信息
        total_managed = len(users_info)
        active_count = len([u for u in users_info if u['status'] == 'active'])

        report_lines.extend([
            f"📊 总管理用户: {total_managed} 个",
            f"🟢 正常用户: {active_count} 个",
            ""
        ])

        # 删除的用户
        if stats['deleted']:
            report_lines.append(f"🗑️ 已删除 {len(stats['deleted'])} 个过期用户:")
            for user in stats['deleted']:
                days_over = abs(user['days_until_expire'])
                report_lines.append(
                    f"  • {user['user_name'].replace('Salted Fish-', '')} (过期{days_over}天)"
                )
            report_lines.append("")

        # 禁用的用户
        if stats['disabled']:
            report_lines.append(f"⚠️ 已禁用 {len(stats['disabled'])} 个临近过期用户:")
            for user in stats['disabled']:
                report_lines.append(
                    f"  • {user['user_name'].replace('Salted Fish-', '')} (剩余{user['days_until_expire']}天)"
                )
            report_lines.append("")

        # 警告的用户（已禁用但未删除）
        if stats['warned']:
            report_lines.append(f"🔴 临近过期用户 {len(stats['warned'])} 个:")
            for user in stats['warned']:
                report_lines.append(
                    f"  • {user['user_name'].replace('Salted Fish-', '')} (剩余{user['days_until_expire']}天,已禁用)"
                )
            report_lines.append("")

        # 失败的操作
        if stats['failed']:
            report_lines.append(f"❌ 操作失败 {len(stats['failed'])} 个:")
            for user in stats['failed']:
                report_lines.append(f"  • {user['user_name']}")
            report_lines.append("")

        return "\n".join(report_lines)


async def main():
    """主函数"""
    try:
        print("=" * 60)
        print("E5 用户有效期检查脚本")
        print("=" * 60)

        config = E5Config()
        if not config.validate():
            return

        print(f"租户ID: {config.tenant_id}")
        print(f"应用ID: {config.client_id}")
        print(f"筛选规则: 只处理以 '{config.user_prefix}' 开头的账号")
        print(f"警告天数: 提前 {config.warning_days} 天禁用")
        print()

        manager = UserExpirationManager(config)

        print("正在获取所有用户列表...")
        all_users = await manager.get_all_users()
        print(f"找到 {len(all_users)} 个用户")

        print("\n计算用户有效期...")
        users_info = manager.calculate_expiration(all_users, config.user_prefix)
        print(f"筛选出 {len(users_info)} 个管理用户")

        if not users_info:
            print("未找到需要管理的用户")
            return

        print("\n开始处理用户有效期...")
        stats = await manager.process_expirations(users_info)

        print()
        print("=" * 60)

        report = ReportGenerator.generate_report(stats, users_info)
        print(report)

        # 发送推送通知（仅在成功禁用或删除用户时发送）
        if stats['deleted'] or stats['disabled']:
            try:
                from utils.notify_utils import BarkNotify
                print("\n正在发送推送通知...")
                result = BarkNotify().send_notify(
                    "E5 用户有效期检查",
                    report,
                    level='timeSensitive',
                    group='microsoft'
                )
                if result and result.get('code') == 200:
                    print("✓ 推送通知已发送")
                else:
                    print(f"✗ 推送通知发送失败: {result}")
            except Exception as e:
                print(f"✗ 推送通知发送失败: {e}")

        print("\n✓ 检查完成")

    except Exception as e:
        print(f"\n✗ 脚本执行出错: {e}")
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())
