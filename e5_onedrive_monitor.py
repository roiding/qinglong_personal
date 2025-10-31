'''
name: E5 OneDrive使用情况监控
cron: 0 9 * * *
'''

import os
import sys
import json
import traceback
from typing import List, Dict, TypedDict, Optional
from datetime import datetime
from azure.identity import UsernamePasswordCredential
from msgraph.core import GraphClient


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
        self.username = os.getenv('E5_USERNAME', '')
        self.password = os.getenv('E5_PASSWORD', '')

    def validate(self) -> bool:
        """验证必要配置是否存在"""
        if not self.tenant_id or not self.client_id or not self.username or not self.password:
            print("错误: 缺少必要的环境变量配置")
            print("请设置: E5_TENANT_ID, E5_CLIENT_ID, E5_USERNAME, E5_PASSWORD")
            return False
        return True


class OneDriveMonitor:
    """OneDrive 使用情况监控"""

    def __init__(self, config: E5Config):
        self.config = config
        credential = UsernamePasswordCredential(
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            tenant_id=config.tenant_id
        )
        self.graph_client = GraphClient(credential=credential)

    def get_all_users(self) -> List[Dict]:
        """获取所有用户列表"""
        try:
            result = self.graph_client.get('/users?$select=id,userPrincipalName,displayName,accountEnabled')
            if result and result.status_code == 200:
                data = result.json()
                return [user for user in data.get('value', []) if user.get('accountEnabled', False)]
            return []
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """根据邮箱获取用户信息"""
        try:
            result = self.graph_client.get(f'/users/{email}?$select=id,userPrincipalName,displayName,accountEnabled')
            if result and result.status_code == 200:
                return result.json()
            return None
        except Exception as e:
            print(f"获取用户 {email} 失败: {e}")
            return None

    def get_user_drive_info(self, user_id: str) -> Optional[Dict]:
        """获取用户的 OneDrive 信息"""
        try:
            result = self.graph_client.get(f'/users/{user_id}/drive')
            if result and result.status_code == 200:
                return result.json()
            return None
        except Exception as e:
            print(f"获取用户 Drive 信息失败: {e}")
            return None

    def get_user_onedrive_usage(self, user_info: Dict) -> Optional[UserOneDriveInfo]:
        """获取单个用户的 OneDrive 使用情况"""
        try:
            user_id = user_info.get('id')
            user_email = user_info.get('userPrincipalName', 'Unknown')
            user_name = user_info.get('displayName', 'Unknown')

            drive_info = self.get_user_drive_info(user_id)
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

    def get_all_users_usage(self) -> List[UserOneDriveInfo]:
        """获取所有 Salted-Fish 开头的用户的 OneDrive 使用情况"""
        results = []

        print("正在获取所有用户列表...")
        all_users = self.get_all_users()
        print(f"找到 {len(all_users)} 个启用的用户")

        # 筛选以 Salted-Fish 开头的用户
        target_users = []
        for user in all_users:
            display_name = user.get('displayName', '')
            user_email = user.get('userPrincipalName', '')

            # 检查显示名称或邮箱是否以 Salted-Fish 开头
            if display_name.startswith('Salted-Fish') or user_email.startswith('Salted-Fish'):
                target_users.append(user)

        print(f"筛选出 {len(target_users)} 个 Salted-Fish 开头的用户")

        for user in target_users:
            email = user.get('userPrincipalName', 'Unknown')
            display_name = user.get('displayName', 'Unknown')
            print(f"  查询用户: {display_name} ({email})")
            usage = self.get_user_onedrive_usage(user)
            if usage:
                results.append(usage)

        return results


class ReportGenerator:
    """报表生成器"""

    @staticmethod
    def generate_text_report(users_data: List[UserOneDriveInfo]) -> str:
        """生成文本格式报表"""
        if not users_data:
            return "无数据可生成报表"

        report_lines = [
            "=" * 80,
            f"E5 OneDrive 使用情况报表",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"用户数量: {len(users_data)}",
            "=" * 80,
            ""
        ]

        # 按使用率排序
        sorted_data = sorted(users_data, key=lambda x: x['usage_percentage'], reverse=True)

        for idx, user in enumerate(sorted_data, 1):
            report_lines.extend([
                f"{idx}. {user['user_name']} ({user['user_email']})",
                f"   已用: {user['used_gb']:.2f} GB / {user['total_gb']:.2f} GB ({user['usage_percentage']:.2f}%)",
                f"   剩余: {user['remaining_gb']:.2f} GB",
                f"   最后活动: {user['last_activity'] or 'N/A'}",
                ""
            ])

        # 统计信息
        total_used = sum(u['used_gb'] for u in users_data)
        total_capacity = sum(u['total_gb'] for u in users_data)
        avg_usage = sum(u['usage_percentage'] for u in users_data) / len(users_data)

        report_lines.extend([
            "=" * 80,
            "统计摘要:",
            f"  总使用量: {total_used:.2f} GB",
            f"  总容量: {total_capacity:.2f} GB",
            f"  平均使用率: {avg_usage:.2f}%",
            "=" * 80
        ])

        return "\n".join(report_lines)

    @staticmethod
    def save_json_report(users_data: List[UserOneDriveInfo], filepath: str):
        """保存 JSON 格式报表"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_users': len(users_data),
            'users': users_data
        }

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"✓ JSON 报表已保存到: {filepath}")


def main():
    """主函数"""
    try:
        print("=" * 60)
        print("E5 OneDrive 使用情况监控脚本")
        print("=" * 60)

        config = E5Config()
        if not config.validate():
            return

        print(f"租户ID: {config.tenant_id}")
        print(f"登录用户: {config.username}")
        print(f"筛选规则: 只查询以 'Salted-Fish' 开头的账号")
        print()

        monitor = OneDriveMonitor(config)
        users_data = monitor.get_all_users_usage()

        if not users_data:
            print("未获取到任何用户数据")
            return

        print()
        print("=" * 60)

        report = ReportGenerator.generate_text_report(users_data)
        print(report)

        json_path = '/ql/data/e5_onedrive_report.json'
        ReportGenerator.save_json_report(users_data, json_path)

        print("\n✓ 监控完成")

    except Exception as e:
        print(f"\n✗ 脚本执行出错: {e}")
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    main()
