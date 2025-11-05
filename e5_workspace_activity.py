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
        credential = UsernamePasswordCredential(
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            tenant_id=config.tenant_id
        )
        self.graph_client = GraphServiceClient(credentials=credential)

    # 搜索关键词列表
    SEARCH_KEYWORDS = [
        'project management',
        'cloud computing',
        'data analysis',
        'security best practices',
        'team collaboration',
        'workflow automation',
        'API integration',
        'documentation',
        'meeting notes',
        'quarterly report',
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

    async def create_onenote_page(self, title: str) -> dict:
        """创建 OneNote 页面"""
        try:
            # 获取笔记本列表
            notebooks = await self.graph_client.me.onenote.notebooks.get()

            if not notebooks or not hasattr(notebooks, 'value') or not notebooks.value or len(notebooks.value) == 0:
                return {
                    'success': False,
                    'title': title,
                    'error': 'No notebook found'
                }

            notebook = notebooks.value[0]

            # 获取分区列表
            sections = await self.graph_client.me.onenote.notebooks.by_notebook_id(notebook.id).sections.get()

            if not sections or not hasattr(sections, 'value') or not sections.value or len(sections.value) == 0:
                return {
                    'success': False,
                    'title': title,
                    'error': 'No section found'
                }

            section = sections.value[0]

            # 创建 HTML 内容（简化格式）
            html_content = f'''<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<p>Created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>Random content: {random.randint(100000, 999999)}</p>
</body>
</html>'''

            # 使用 httpx 直接发送请求
            import httpx

            # 获取访问令牌
            from azure.identity import UsernamePasswordCredential
            credential = UsernamePasswordCredential(
                client_id=self.config.client_id,
                username=self.config.username,
                password=self.config.password,
                tenant_id=self.config.tenant_id
            )
            token = credential.get_token("https://graph.microsoft.com/.default")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section.id}/pages",
                    headers={
                        "Authorization": f"Bearer {token.token}",
                        "Content-Type": "text/html"
                    },
                    content=html_content.encode('utf-8'),
                    timeout=30.0
                )

                if response.status_code in [200, 201]:
                    return {
                        'success': True,
                        'title': title,
                        'result': 'created'
                    }
                else:
                    return {
                        'success': False,
                        'title': title,
                        'error': f'HTTP {response.status_code}: {response.text[:50]}'
                    }

        except Exception as e:
            error_msg = str(e)
            return {
                'success': False,
                'title': title,
                'error': error_msg[:100]
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
            return {
                'success': False,
                'error': error_msg
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

    async def delete_onenote_pages(self, count: int = 2) -> dict:
        """删除 OneNote 页面"""
        try:
            # 获取笔记本
            notebooks = await self.graph_client.me.onenote.notebooks.get()

            deleted = 0
            if notebooks and notebooks.value and len(notebooks.value) > 0:
                notebook = notebooks.value[0]
                sections = await self.graph_client.me.onenote.notebooks.by_notebook_id(notebook.id).sections.get()

                if sections and sections.value and len(sections.value) > 0:
                    section = sections.value[0]
                    pages = await self.graph_client.me.onenote.sections.by_onenote_section_id(section.id).pages.get()

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

            # 方式1：尝试获取根站点
            try:
                root_site = await self.graph_client.sites.root.get()
                if root_site and hasattr(root_site, 'id') and root_site.id:
                    site_count += 1
            except:
                pass

            # 方式2：尝试列出所有站点（使用 search）
            try:
                # 搜索所有站点
                from kiota_abstractions.request_information import RequestInformation
                request_info = RequestInformation()
                request_info.http_method = "GET"
                request_info.url_template = "{+baseurl}/sites?search=*"

                sites_result = await self.graph_client.request_adapter.send_primitive_async(request_info, dict, {})

                if sites_result and 'value' in sites_result:
                    site_count = len(sites_result['value'])
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

        # 1. 发送邮件给自己（50% 概率）
        if random.choice([True, False]):
            print(f"\n[1/10] 发送邮件给自己")
            email_subjects = [
                'Project update',
                'Meeting follow-up',
                'Weekly summary',
                'Task reminder',
                'Documentation review'
            ]
            subject = random.choice(email_subjects)
            result = await self.send_email_to_self(subject)
            if result['success']:
                results['emails_created'] += 1
                print(f"  ✓ 邮件发送成功: {subject}")
            else:
                results['failed'] += 1
                print(f"  ✗ 邮件发送失败: {result.get('error', '')[:50]}")
            await asyncio.sleep(random.uniform(1, 3))
        else:
            print(f"\n[1/10] 跳过邮件发送")

        # 2. 搜索邮件（2-3 个关键词）
        search_count = random.randint(2, 3)
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
            await asyncio.sleep(random.uniform(1, 3))

        # 3. 创建日历事件（50% 概率）
        if random.choice([True, False]):
            print(f"\n[3/10] 创建日历事件")
            event_titles = [
                'Team meeting',
                'Project review',
                'Training session',
                'Planning meeting',
                'Status update'
            ]
            title = random.choice(event_titles)
            result = await self.create_calendar_event(title)
            if result['success']:
                results['events_created'] += 1
                print(f"  ✓ 事件创建成功: {title}")
            else:
                results['failed'] += 1
                print(f"  ✗ 事件创建失败: {result.get('error', '')[:50]}")
            await asyncio.sleep(random.uniform(1, 3))
        else:
            print(f"\n[3/10] 跳过事件创建")

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

        # 6. 创建 To Do 任务（50% 概率）
        if random.choice([True, False]):
            print(f"\n[6/10] 创建 To Do 任务")
            task_titles = [
                'Review documentation',
                'Check system status',
                'Update project notes',
                'Prepare weekly report',
                'Schedule team meeting'
            ]
            task_title = random.choice(task_titles)
            result = await self.create_todo_task(task_title)
            if result['success']:
                results['tasks_created'] += 1
                print(f"  ✓ 任务创建成功: {task_title}")
            else:
                results['failed'] += 1
                print(f"  ✗ 任务创建失败: {result.get('error', '')[:50]}")
            await asyncio.sleep(random.uniform(1, 3))
        else:
            print(f"\n[6/10] 跳过任务创建")

        # 7. 创建 OneNote 页面（50% 概率）
        if random.choice([True, False]):
            print(f"\n[7/10] 创建 OneNote 页面")
            page_titles = [
                'Meeting notes',
                'Project ideas',
                'Research notes',
                'Task list',
                'Weekly summary'
            ]
            page_title = random.choice(page_titles)
            result = await self.create_onenote_page(page_title)
            if result['success']:
                results['onenote_pages'] += 1
                print(f"  ✓ 页面创建成功: {page_title}")
            else:
                results['failed'] += 1
                print(f"  ✗ 页面创建失败: {result.get('error', '')[:50]}")
            await asyncio.sleep(random.uniform(1, 3))
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

        # 9. 上传 SharePoint 文件（50% 概率）
        if random.choice([True, False]):
            print(f"\n[9/10] 上传 SharePoint 文件")
            file_name = f"doc_{random.randint(100000, 999999)}.txt"
            result = await self.upload_sharepoint_file(file_name)
            if result['success']:
                results['sharepoint_files'] += 1
                print(f"  ✓ 文件上传成功: {file_name}")
            else:
                results['failed'] += 1
                print(f"  ✗ 文件上传失败: {result.get('error', '')[:50]}")
            await asyncio.sleep(random.uniform(1, 3))
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
            result = await self.delete_old_emails(5)
            if result['success'] and result['deleted'] > 0:
                results['emails_deleted'] = result['deleted']
                print(f"  ✓ 删除邮件: {result['deleted']} 封")

            await asyncio.sleep(random.uniform(1, 2))

            # 清理日历事件
            result = await self.delete_old_events(3)
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
            result = await self.delete_onenote_pages(2)
            if result['success'] and result['deleted'] > 0:
                results['onenote_pages_deleted'] = result['deleted']
                print(f"  ✓ 删除页面: {result['deleted']} 个")

            await asyncio.sleep(random.uniform(1, 2))

            # 清理文件
            result = await self.delete_old_files(3)
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
