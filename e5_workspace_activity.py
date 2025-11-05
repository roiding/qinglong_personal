'''
name: E5 工作区活动
cron: 0 */2 * * *
'''

import os
import sys
import asyncio
import traceback
import random
from datetime import datetime
from azure.identity import UsernamePasswordCredential
from msgraph import GraphServiceClient

# 加载 .env 文件（本地开发时使用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class E5Config:
    """E5 配置管理"""
    def __init__(self):
        self.tenant_id = os.getenv('E5_TENANT_ID', '')
        self.client_id = os.getenv('E5_CLIENT_ID', '')
        # 使用委托权限
        self.username = os.getenv('E5_KEEPER_USERNAME', '')
        self.password = os.getenv('E5_KEEPER_PASSWORD', '')

    def validate(self) -> bool:
        """验证必要配置是否存在"""
        if not self.tenant_id or not self.client_id or not self.username or not self.password:
            print("错误: 缺少必要的环境变量配置")
            print("请设置: E5_TENANT_ID, E5_CLIENT_ID, E5_KEEPER_USERNAME, E5_KEEPER_PASSWORD")
            return False
        return True


class WorkspaceActivityManager:
    """工作区活动管理器"""

    def __init__(self, config: E5Config):
        self.config = config
        self.credential = UsernamePasswordCredential(
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            tenant_id=config.tenant_id
        )
        self.graph_client = GraphServiceClient(credentials=self.credential)

    # 统一的主题列表（用于邮件、日历、任务、OneNote）
    UNIFIED_TOPICS = [
        'Project Management Review',
        'Cloud Computing Strategy',
        'Data Analysis Report',
        'Security Best Practices',
        'Team Collaboration Plan',
        'Workflow Automation',
        'API Integration Guidelines',
        'Technical Documentation',
        'Meeting Notes Summary',
        'Quarterly Business Report',
        'Product Development Roadmap',
        'Customer Feedback Analysis',
        'Marketing Campaign Ideas',
        'Budget Planning Discussion',
        'Performance Metrics Review',
        'Infrastructure Upgrade Plan',
        'Code Review Standards',
        'Database Optimization',
        'System Architecture Design',
        'User Experience Research',
        'Quality Assurance Process',
        'Deployment Strategy',
        'Risk Management Assessment',
        'Training Materials',
        'Innovation Proposals',
    ]

    # 搜索关键词列表
    SEARCH_KEYWORDS = [
        'Project',
        'Cloud',
        'Data',
        'Security',
        'Team',
        'Workflow',
        'API',
        'Documentation',
        'Meeting',
        'Report',
        'Development',
        'Feedback',
        'Marketing',
        'Budget',
        'Performance',
    ]

    async def send_email_to_self(self, subject: str) -> dict:
        """发送邮件给自己"""
        try:
            from msgraph.generated.models.message import Message
            from msgraph.generated.models.item_body import ItemBody
            from msgraph.generated.models.recipient import Recipient
            from msgraph.generated.models.email_address import EmailAddress

            message = Message()
            message.subject = subject

            # 创建邮件正文
            body = ItemBody()
            body.content_type = "Text"
            body.content = f"Email sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            body.content += f"Random content: {random.randint(100000, 999999)}\n"
            message.body = body

            # 收件人设置为自己
            to_recipient = Recipient()
            email_address = EmailAddress()
            email_address.address = self.config.username
            to_recipient.email_address = email_address
            message.to_recipients = [to_recipient]

            # 先创建草稿
            draft = await self.graph_client.me.messages.post(message)

            # 然后发送
            await self.graph_client.me.messages.by_message_id(draft.id).send.post()

            return {
                'success': True,
                'subject': subject,
                'result': 'sent'
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'subject': subject,
                'error': error_msg
            }

    async def create_calendar_event(self, title: str) -> dict:
        """创建日历事件"""
        try:
            from msgraph.generated.models.event import Event
            from msgraph.generated.models.item_body import ItemBody
            from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
            from datetime import timedelta

            event = Event()
            event.subject = title

            # 事件正文
            body = ItemBody()
            body.content_type = "Text"
            body.content = f"Event created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            event.body = body

            # 设置事件时间（1小时后开始，持续1小时）
            start_time = datetime.now() + timedelta(hours=1)
            end_time = start_time + timedelta(hours=1)

            start = DateTimeTimeZone()
            start.date_time = start_time.strftime('%Y-%m-%dT%H:%M:%S')
            start.time_zone = "UTC"
            event.start = start

            end = DateTimeTimeZone()
            end.date_time = end_time.strftime('%Y-%m-%dT%H:%M:%S')
            end.time_zone = "UTC"
            event.end = end

            await self.graph_client.me.events.post(event)

            return {
                'success': True,
                'title': title,
                'result': 'created'
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'title': title,
                'error': error_msg
            }

    async def create_onenote_notebook(self, name: str) -> dict:
        """创建 OneNote 笔记本"""
        try:
            from msgraph.generated.models.notebook import Notebook

            notebook = Notebook()
            notebook.display_name = name

            result = await self.graph_client.me.onenote.notebooks.post(notebook)

            return {
                'success': True,
                'name': name,
                'id': result.id if result else None
            }

        except Exception as e:
            return {
                'success': False,
                'name': name,
                'error': str(e)[:100]
            }

    async def create_onenote_section(self, notebook_id: str, name: str) -> dict:
        """创建 OneNote 分区"""
        try:
            from msgraph.generated.models.onenote_section import OnenoteSection

            section = OnenoteSection()
            section.display_name = name

            result = await self.graph_client.me.onenote.notebooks.by_notebook_id(notebook_id).sections.post(section)

            return {
                'success': True,
                'name': name,
                'id': result.id if result else None
            }

        except Exception as e:
            return {
                'success': False,
                'name': name,
                'error': str(e)[:100]
            }

    async def create_onenote_page(self, title: str) -> dict:
        """创建 OneNote 页面（自动创建笔记本和分区，或使用现有的）"""
        try:
            # 获取笔记本列表
            notebooks = await self.graph_client.me.onenote.notebooks.get()

            # 查找名为 "Work Notes" 的笔记本（脚本专用）
            target_notebook = None
            if notebooks and notebooks.value:
                for nb in notebooks.value:
                    if hasattr(nb, 'display_name') and nb.display_name == 'Work Notes':
                        target_notebook = nb
                        break

            # 如果没有找到，创建新笔记本
            if not target_notebook:
                nb_result = await self.create_onenote_notebook('Work Notes')
                if not nb_result['success']:
                    return {
                        'success': False,
                        'title': title,
                        'error': f"创建笔记本失败: {nb_result.get('error', '')}"
                    }
                # 等待创建完成并重新获取
                await asyncio.sleep(2)
                notebooks = await self.graph_client.me.onenote.notebooks.get()
                if notebooks and notebooks.value:
                    for nb in notebooks.value:
                        if hasattr(nb, 'display_name') and nb.display_name == 'Work Notes':
                            target_notebook = nb
                            break

            if not target_notebook:
                return {
                    'success': False,
                    'title': title,
                    'error': 'Failed to create or find notebook'
                }

            notebook = target_notebook

            # 获取分区列表
            sections = await self.graph_client.me.onenote.notebooks.by_notebook_id(notebook.id).sections.get()

            # 查找名为 "Activity Log" 的分区（脚本专用）
            target_section = None
            if sections and sections.value:
                for sec in sections.value:
                    if hasattr(sec, 'display_name') and sec.display_name == 'Activity Log':
                        target_section = sec
                        break

            # 如果没有找到，创建新分区
            if not target_section:
                sec_result = await self.create_onenote_section(notebook.id, 'Activity Log')
                if not sec_result['success']:
                    return {
                        'success': False,
                        'title': title,
                        'error': f"创建分区失败: {sec_result.get('error', '')}"
                    }
                # 等待创建完成并重新获取
                await asyncio.sleep(2)
                sections = await self.graph_client.me.onenote.notebooks.by_notebook_id(notebook.id).sections.get()
                if sections and sections.value:
                    for sec in sections.value:
                        if hasattr(sec, 'display_name') and sec.display_name == 'Activity Log':
                            target_section = sec
                            break

            if not target_section:
                return {
                    'success': False,
                    'title': title,
                    'error': 'Failed to create or find section'
                }

            section = target_section

            # 转义 HTML 特殊字符
            import html
            safe_title = html.escape(title)

            # OneNote API 需要 well-formed XHTML
            html_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{safe_title}</title>
</head>
<body>
<h1>{safe_title}</h1>
<p>Created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>Random content: {random.randint(100000, 999999)}</p>
</body>
</html>'''

            # msgraph SDK 不支持 OneNote 页面创建，使用底层 HTTP 客户端
            http_client = self.graph_client.request_adapter._http_client
            token = self.credential.get_token("https://graph.microsoft.com/.default")

            try:
                response = await http_client.post(
                    f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section.id}/pages",
                    headers={
                        "Authorization": f"Bearer {token.token}",
                        "Content-Type": "application/xhtml+xml"
                    },
                    content=html_content.encode('utf-8')
                )

                if response.status_code in [200, 201]:
                    # 解析响应获取页面 ID
                    try:
                        import json
                        result_data = json.loads(response.content.decode('utf-8'))
                        page_id = result_data.get('id', 'unknown')
                        page_url = result_data.get('links', {}).get('oneNoteWebUrl', {}).get('href', '')
                        return {
                            'success': True,
                            'title': title,
                            'result': 'created',
                            'page_id': page_id,
                            'notebook': notebook.display_name if hasattr(notebook, 'display_name') else notebook.id,
                            'section': section.display_name if hasattr(section, 'display_name') else section.id,
                            'url': page_url  # 显示完整 URL
                        }
                    except:
                        return {
                            'success': True,
                            'title': title,
                            'result': 'created'
                        }
                else:
                    # 获取完整的错误响应
                    error_text = response.text if hasattr(response, 'text') else str(response.content)
                    return {
                        'success': False,
                        'title': title,
                        'error': f'HTTP {response.status_code}: {error_text[:200]}'
                    }
            except Exception as http_error:
                # httpx 可能在非 2xx 响应时抛出异常
                error_detail = str(http_error)
                if hasattr(http_error, 'response'):
                    try:
                        resp = http_error.response
                        if hasattr(resp, 'text'):
                            error_detail = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        elif hasattr(resp, 'content'):
                            error_detail = f"HTTP {resp.status_code}: {resp.content.decode('utf-8', errors='ignore')[:200]}"
                    except:
                        pass
                return {
                    'success': False,
                    'title': title,
                    'error': error_detail
                }

        except Exception as e:
            error_msg = str(e)
            # 如果是 API 错误，尝试获取更多细节
            if hasattr(e, 'response'):
                try:
                    error_msg += f" | Response: {e.response.text if hasattr(e.response, 'text') else str(e.response)}"
                except:
                    pass
            return {
                'success': False,
                'title': title,
                'error': error_msg[:300]
            }

    async def upload_sharepoint_file(self, file_name: str) -> dict:
        """上传文件到 OneDrive（SharePoint）"""
        try:
            # 创建简单的文本文件
            content = f"SharePoint file created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            content += f"Random data: {random.randint(100000, 999999)}\n"
            content_bytes = content.encode('utf-8')

            # 获取 drive ID
            drive = await self.graph_client.me.drive.get()
            drive_id = drive.id

            # 上传到 OneDrive 根目录
            await self.graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id('root:/' + file_name + ':').content.put(content_bytes)

            return {
                'success': True,
                'file': file_name,
                'result': 'uploaded'
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'file': file_name,
                'error': error_msg
            }

    async def search_content(self, keyword: str) -> dict:
        """搜索邮件内容"""
        try:
            # 简单调用：直接获取邮件列表，然后在本地过滤
            result = await self.graph_client.me.messages.get()

            # 简单的本地关键词匹配
            message_count = 0
            if result and result.value:
                keyword_lower = keyword.lower()
                for msg in result.value[:20]:  # 只检查前20封
                    subject = (msg.subject or "").lower()
                    if keyword_lower in subject:
                        message_count += 1

            return {
                'success': True,
                'keyword': keyword,
                'count': message_count
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'keyword': keyword,
                'error': error_msg
            }

    async def create_planner_task(self, title: str) -> dict:
        """创建 Planner 任务"""
        try:
            # 首先获取用户的 Planner
            plans = await self.graph_client.me.planner.plans.get()

            if plans and plans.value and len(plans.value) > 0:
                # 使用第一个计划
                plan = plans.value[0]

                # 获取该计划的 buckets
                buckets = await self.graph_client.planner.plans.by_planner_plan_id(plan.id).buckets.get()

                if buckets and buckets.value and len(buckets.value) > 0:
                    bucket = buckets.value[0]

                    # 创建任务
                    from msgraph.generated.models.planner_task import PlannerTask

                    task = PlannerTask()
                    task.plan_id = plan.id
                    task.bucket_id = bucket.id
                    task.title = title

                    await self.graph_client.planner.tasks.post(task)

                    return {
                        'success': True,
                        'task': title,
                        'result': 'created'
                    }

            return {
                'success': False,
                'task': title,
                'error': 'No planner found'
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'task': title,
                'error': error_msg
            }

    async def access_todo_lists(self) -> dict:
        """访问 To Do 列表"""
        try:
            # 获取 To Do 列表
            result = await self.graph_client.me.todo.lists.get()

            list_count = len(result.value) if result and result.value else 0

            # 如果有列表，读取第一个列表的任务
            if result and result.value and len(result.value) > 0:
                todo_list = result.value[0]
                tasks = await self.graph_client.me.todo.lists.by_todo_task_list_id(todo_list.id).tasks.get()
                task_count = len(tasks.value) if tasks and tasks.value else 0

                return {
                    'success': True,
                    'lists': list_count,
                    'tasks': task_count
                }

            return {
                'success': True,
                'lists': list_count,
                'tasks': 0
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def create_todo_task(self, title: str) -> dict:
        """创建 To Do 任务"""
        try:
            # 获取第一个列表
            lists = await self.graph_client.me.todo.lists.get()

            if lists and lists.value and len(lists.value) > 0:
                todo_list = lists.value[0]

                # 创建任务
                from msgraph.generated.models.todo_task import TodoTask
                from msgraph.generated.models.item_body import ItemBody

                task = TodoTask()
                task.title = title

                # 使用正确的 ItemBody 模型
                body = ItemBody()
                body.content = f"Created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                body.content_type = "text"
                task.body = body

                await self.graph_client.me.todo.lists.by_todo_task_list_id(todo_list.id).tasks.post(task)

                return {
                    'success': True,
                    'task': title,
                    'result': 'created'
                }

            return {
                'success': False,
                'task': title,
                'error': 'No todo list found'
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'task': title,
                'error': error_msg
            }

    async def access_calendar_events(self) -> dict:
        """访问日历事件"""
        try:
            # 直接获取事件列表
            result = await self.graph_client.me.events.get()

            # 统计事件数量
            event_count = 0
            if result and result.value:
                for event in result.value[:20]:  # 只检查前20个事件
                    if event.start and event.start.date_time:
                        # 简单检查，只要有事件就计数
                        event_count += 1

            return {
                'success': True,
                'events': event_count
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def access_onenote(self) -> dict:
        """访问 OneNote 笔记本"""
        try:
            # 获取笔记本列表
            notebooks = await self.graph_client.me.onenote.notebooks.get()

            notebook_count = len(notebooks.value) if notebooks and notebooks.value else 0

            return {
                'success': True,
                'notebooks': notebook_count
            }

        except Exception as e:
            error_msg = str(e)
            # 如果是 API 错误，尝试获取更多细节
            if hasattr(e, 'response'):
                try:
                    resp = e.response
                    if hasattr(resp, 'text'):
                        error_msg = f"{error_msg} | Response: {resp.text[:200]}"
                    elif hasattr(resp, 'content'):
                        error_msg = f"{error_msg} | Response: {resp.content.decode('utf-8', errors='ignore')[:200]}"
                except:
                    pass
            return {
                'success': False,
                'error': error_msg[:300]
            }

    async def delete_old_emails(self, count: int = 5) -> dict:
        """删除旧邮件（发件人是自己的）"""
        try:
            # 获取发件人是自己的邮件
            messages = await self.graph_client.me.messages.get()

            deleted = 0
            if messages and messages.value:
                for msg in messages.value[:count]:
                    # 检查是否是自己发的
                    if msg.from_ and msg.from_.email_address and msg.from_.email_address.address == self.config.username:
                        await self.graph_client.me.messages.by_message_id(msg.id).delete()
                        deleted += 1

            return {
                'success': True,
                'deleted': deleted
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def delete_old_events(self, count: int = 3) -> dict:
        """删除旧的日历事件"""
        try:
            events = await self.graph_client.me.events.get()

            deleted = 0
            if events and events.value:
                for event in events.value[:count]:
                    await self.graph_client.me.events.by_event_id(event.id).delete()
                    deleted += 1

            return {
                'success': True,
                'deleted': deleted
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def delete_completed_tasks(self) -> dict:
        """删除已完成的 To Do 任务"""
        try:
            lists = await self.graph_client.me.todo.lists.get()

            deleted = 0
            if lists and lists.value and len(lists.value) > 0:
                todo_list = lists.value[0]
                tasks = await self.graph_client.me.todo.lists.by_todo_task_list_id(todo_list.id).tasks.get()

                if tasks and tasks.value:
                    for task in tasks.value:
                        # 删除已完成的任务或随机删除一些
                        if task.status == "completed" or random.choice([True, False, False]):
                            await self.graph_client.me.todo.lists.by_todo_task_list_id(todo_list.id).tasks.by_todo_task_id(task.id).delete()
                            deleted += 1
                            if deleted >= 3:  # 最多删除3个
                                break

            return {
                'success': True,
                'deleted': deleted
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def delete_onenote_pages(self, count: int = 3) -> dict:
        """删除 OneNote 页面（仅删除 Work Notes 笔记本中的页面）"""
        try:
            # 获取笔记本
            notebooks = await self.graph_client.me.onenote.notebooks.get()

            deleted = 0
            if notebooks and notebooks.value:
                # 查找 "Work Notes" 笔记本
                target_notebook = None
                for nb in notebooks.value:
                    if hasattr(nb, 'display_name') and nb.display_name == 'Work Notes':
                        target_notebook = nb
                        break

                if target_notebook:
                    sections = await self.graph_client.me.onenote.notebooks.by_notebook_id(target_notebook.id).sections.get()

                    if sections and sections.value:
                        # 查找 "Activity Log" 分区
                        target_section = None
                        for sec in sections.value:
                            if hasattr(sec, 'display_name') and sec.display_name == 'Activity Log':
                                target_section = sec
                                break

                        if target_section:
                            pages = await self.graph_client.me.onenote.sections.by_onenote_section_id(target_section.id).pages.get()

                            if pages and pages.value:
                                for page in pages.value[:count]:
                                    await self.graph_client.me.onenote.pages.by_onenote_page_id(page.id).delete()
                                    deleted += 1

            return {
                'success': True,
                'deleted': deleted
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def delete_old_files(self, count: int = 3) -> dict:
        """删除旧文件"""
        try:
            # 获取 drive ID
            drive = await self.graph_client.me.drive.get()
            drive_id = drive.id

            # 获取根目录下的文件
            items = await self.graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id('root').children.get()

            deleted = 0
            if items and items.value:
                # 只删除文件名匹配 doc_*.txt 的文件（脚本创建的）
                for item in items.value:
                    if item.name and item.name.startswith('doc_') and item.name.endswith('.txt'):
                        await self.graph_client.drives.by_drive_id(drive_id).items.by_drive_item_id(item.id).delete()
                        deleted += 1
                        if deleted >= count:
                            break

            return {
                'success': True,
                'deleted': deleted
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def access_sharepoint_sites(self) -> dict:
        """访问 SharePoint 站点"""
        try:
            site_count = 0

            # 方式1：访问用户的 OneDrive 站点（个人 SharePoint 站点）
            try:
                drive = await self.graph_client.me.drive.get()
                if drive and hasattr(drive, 'id') and drive.id:
                    site_count += 1
            except:
                pass

            # 方式2：尝试获取根站点
            if site_count == 0:
                try:
                    root_site = await self.graph_client.sites.root.get()
                    if root_site and hasattr(root_site, 'id') and root_site.id:
                        site_count += 1
                except:
                    pass

            # 方式3：尝试获取关注的站点
            if site_count == 0:
                try:
                    sites = await self.graph_client.me.followed_sites.get()
                    if sites and sites.value:
                        site_count = len(sites.value)
                except:
                    pass

            return {
                'success': True,
                'sites': site_count
            }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'error': error_msg
            }

    async def perform_random_activities(self):
        """执行随机活动"""
        print("\n开始执行随机活动...")

        results = {
            'emails_created': 0,
            'emails_deleted': 0,
            'search': 0,
            'events_created': 0,
            'events_deleted': 0,
            'calendar': 0,
            'todo': 0,
            'tasks_created': 0,
            'tasks_deleted': 0,
            'onenote_pages': 0,
            'onenote_pages_deleted': 0,
            'onenote': 0,
            'sharepoint_files': 0,
            'files_deleted': 0,
            'sharepoint': 0,
            'failed': 0
        }

        # 1. 发送邮件给自己（70% 概率，2-3 封）
        if random.randint(1, 10) <= 7:
            email_count = random.randint(2, 3)
            print(f"\n[1/10] 发送邮件给自己（{email_count} 封）")
            for i in range(email_count):
                subject = random.choice(self.UNIFIED_TOPICS)
                result = await self.send_email_to_self(subject)
                if result['success']:
                    results['emails_created'] += 1
                    print(f"  ✓ 邮件 {i+1}/{email_count} 发送成功: {subject}")
                else:
                    results['failed'] += 1
                    print(f"  ✗ 邮件 {i+1}/{email_count} 发送失败: {result.get('error', '')[:50]}")
                await asyncio.sleep(random.uniform(1, 2))
        else:
            print(f"\n[1/10] 跳过邮件发送")

        # 2. 搜索邮件（80% 概率，3-5 个关键词）
        if random.randint(1, 10) <= 8:
            search_count = random.randint(3, 5)
            print(f"\n[2/10] 搜索内容（{search_count} 个关键词）")
            keywords = random.sample(self.SEARCH_KEYWORDS, search_count)
            for keyword in keywords:
                print(f"  搜索: {keyword}")
                result = await self.search_content(keyword)
                if result['success']:
                    results['search'] += 1
                    print(f"    ✓ 找到 {result.get('count', 0)} 封邮件")
                else:
                    results['failed'] += 1
                    print(f"    ✗ 搜索失败: {result.get('error', '')[:50]}")
                await asyncio.sleep(random.uniform(1, 2))
        else:
            print(f"\n[2/10] 跳过搜索")

        # 3. 创建日历事件（60% 概率，1-2 个）
        if random.randint(1, 10) <= 6:
            event_count = random.randint(1, 2)
            print(f"\n[3/10] 创建日历事件（{event_count} 个）")
            for i in range(event_count):
                title = random.choice(self.UNIFIED_TOPICS)
                result = await self.create_calendar_event(title)
                if result['success']:
                    results['events_created'] += 1
                    print(f"  ✓ 事件 {i+1}/{event_count} 创建成功: {title}")
                else:
                    results['failed'] += 1
                    print(f"  ✗ 事件 {i+1}/{event_count} 创建失败: {result.get('error', '')[:50]}")
                await asyncio.sleep(random.uniform(1, 2))
        else:
            print(f"\n[3/10] 跳过日历事件创建")

        # 4. 访问日历事件
        print(f"\n[4/10] 访问日历事件")
        result = await self.access_calendar_events()
        if result['success']:
            results['calendar'] += 1
            print(f"  ✓ 成功访问，有 {result.get('events', 0)} 个事件")
        else:
            results['failed'] += 1
            print(f"  ✗ 访问失败: {result.get('error', '')[:50]}")

        # 5. 访问 To Do 列表
        print(f"\n[5/10] 访问 To Do 列表")
        result = await self.access_todo_lists()
        if result['success']:
            results['todo'] += 1
            print(f"  ✓ 成功访问 {result.get('lists', 0)} 个列表，{result.get('tasks', 0)} 个任务")
        else:
            results['failed'] += 1
            print(f"  ✗ 访问失败: {result.get('error', '')[:50]}")

        # 6. 创建 To Do 任务（60% 概率，1-2 个）
        if random.randint(1, 10) <= 6:
            task_count = random.randint(1, 2)
            print(f"\n[6/10] 创建 To Do 任务（{task_count} 个）")
            for i in range(task_count):
                task_title = random.choice(self.UNIFIED_TOPICS)
                result = await self.create_todo_task(task_title)
                if result['success']:
                    results['tasks_created'] += 1
                    print(f"  ✓ 任务 {i+1}/{task_count} 创建成功: {task_title}")
                else:
                    results['failed'] += 1
                    print(f"  ✗ 任务 {i+1}/{task_count} 创建失败: {result.get('error', '')[:50]}")
                await asyncio.sleep(random.uniform(1, 2))
        else:
            print(f"\n[6/10] 跳过 To Do 任务创建")

        # 7. 创建 OneNote 页面（60% 概率，1-2 个）
        if random.randint(1, 10) <= 6:
            page_count = random.randint(1, 2)
            print(f"\n[7/10] 创建 OneNote 页面（{page_count} 个）")
            for i in range(page_count):
                page_title = random.choice(self.UNIFIED_TOPICS)
                result = await self.create_onenote_page(page_title)
                if result['success']:
                    results['onenote_pages'] += 1
                    print(f"  ✓ 页面 {i+1}/{page_count} 创建成功: {page_title}")
                    if 'notebook' in result:
                        print(f"    笔记本: {result['notebook']}")
                    if 'section' in result:
                        print(f"    分区: {result['section']}")
                else:
                    results['failed'] += 1
                    print(f"  ✗ 页面 {i+1}/{page_count} 创建失败: {result.get('error', '')[:50]}")
                await asyncio.sleep(random.uniform(1, 2))
        else:
            print(f"\n[7/10] 跳过 OneNote 页面创建")

        # 8. 访问 OneNote
        print(f"\n[8/10] 访问 OneNote")
        result = await self.access_onenote()
        if result['success']:
            results['onenote'] += 1
            print(f"  ✓ 成功访问 {result.get('notebooks', 0)} 个笔记本")
        else:
            results['failed'] += 1
            print(f"  ✗ 访问失败: {result.get('error', '')[:50]}")

        # 9. 上传 SharePoint 文件（60% 概率，1-2 个）
        if random.randint(1, 10) <= 6:
            file_count = random.randint(1, 2)
            print(f"\n[9/10] 上传 SharePoint 文件（{file_count} 个）")
            for i in range(file_count):
                file_name = f"doc_{random.randint(100000, 999999)}.txt"
                result = await self.upload_sharepoint_file(file_name)
                if result['success']:
                    results['sharepoint_files'] += 1
                    print(f"  ✓ 文件 {i+1}/{file_count} 上传成功: {file_name}")
                else:
                    results['failed'] += 1
                    print(f"  ✗ 文件 {i+1}/{file_count} 上传失败: {result.get('error', '')[:50]}")
                await asyncio.sleep(random.uniform(1, 2))
        else:
            print(f"\n[9/10] 跳过文件上传")

        # 10. 访问 SharePoint 站点
        print(f"\n[10/10] 访问 SharePoint 站点")
        result = await self.access_sharepoint_sites()
        if result['success']:
            results['sharepoint'] += 1
            print(f"  ✓ 成功访问 {result.get('sites', 0)} 个站点")
        else:
            results['failed'] += 1
            print(f"  ✗ 访问失败: {result.get('error', '')[:50]}")

        # 清理步骤（30% 概率执行）
        if random.randint(1, 10) <= 3:
            print(f"\n[清理] 开始清理旧数据...")

            # 清理邮件
            result = await self.delete_old_emails(8)
            if result['success'] and result['deleted'] > 0:
                results['emails_deleted'] = result['deleted']
                print(f"  ✓ 删除邮件: {result['deleted']} 封")

            await asyncio.sleep(random.uniform(1, 2))

            # 清理日历事件
            result = await self.delete_old_events(5)
            if result['success'] and result['deleted'] > 0:
                results['events_deleted'] = result['deleted']
                print(f"  ✓ 删除事件: {result['deleted']} 个")

            await asyncio.sleep(random.uniform(1, 2))

            # 清理任务
            result = await self.delete_completed_tasks()
            if result['success'] and result['deleted'] > 0:
                results['tasks_deleted'] = result['deleted']
                print(f"  ✓ 删除任务: {result['deleted']} 个")

            await asyncio.sleep(random.uniform(1, 2))

            # 清理 OneNote 页面
            result = await self.delete_onenote_pages(5)
            if result['success'] and result['deleted'] > 0:
                results['onenote_pages_deleted'] = result['deleted']
                print(f"  ✓ 删除 OneNote 页面: {result['deleted']} 个")

            await asyncio.sleep(random.uniform(1, 2))

            # 清理文件
            result = await self.delete_old_files(5)
            if result['success'] and result['deleted'] > 0:
                results['files_deleted'] = result['deleted']
                print(f"  ✓ 删除文件: {result['deleted']} 个")

        return results


async def main():
    """主函数"""
    try:
        current_time = datetime.now()

        print("=" * 60)
        print(f"E5 工作区活动 - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        config = E5Config()
        if not config.validate():
            return

        manager = WorkspaceActivityManager(config)

        print(f"\n账号: {config.username}")

        # 执行随机活动
        results = await manager.perform_random_activities()

        print()
        print("=" * 60)
        print(f"✓ 完成！")
        print(f"  邮件: {results['emails_created']} 封发送, {results['emails_deleted']} 封删除")
        print(f"  搜索: {results['search']} 次")
        print(f"  日历事件: {results['events_created']} 个创建, {results['events_deleted']} 个删除, {results['calendar']} 次访问")
        print(f"  To Do: {results['tasks_created']} 个创建, {results['tasks_deleted']} 个删除, {results['todo']} 次访问")
        print(f"  OneNote: {results['onenote_pages']} 个页面创建, {results['onenote_pages_deleted']} 个页面删除, {results['onenote']} 次访问")
        print(f"  文件: {results['sharepoint_files']} 个上传, {results['files_deleted']} 个删除, {results['sharepoint']} 次访问")
        if results['failed'] > 0:
            print(f"  失败: {results['failed']} 次")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 脚本执行出错: {e}")
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())
