'''
name: E5 存储同步
cron: */5 * * * *
'''

import os
import sys
import asyncio
import traceback
import random
from datetime import datetime
from io import BytesIO
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
        # 使用委托权限，针对特定账号（复用 KEEPER 的配置）
        self.username = os.getenv('E5_KEEPER_USERNAME', '')
        self.password = os.getenv('E5_KEEPER_PASSWORD', '')

    def validate(self) -> bool:
        """验证必要配置是否存在"""
        if not self.tenant_id or not self.client_id or not self.username or not self.password:
            print("错误: 缺少必要的环境变量配置")
            print("请设置: E5_TENANT_ID, E5_CLIENT_ID, E5_KEEPER_USERNAME, E5_KEEPER_PASSWORD")
            return False
        return True


class OneDriveFileManager:
    """OneDrive 文件管��器"""

    def __init__(self, config: E5Config):
        self.config = config
        credential = UsernamePasswordCredential(
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            tenant_id=config.tenant_id
        )
        self.graph_client = GraphServiceClient(credentials=credential)
        self.drive_id = None

    async def ensure_drive_id(self):
        """确保已获取 drive ID"""
        if not self.drive_id:
            drive = await self.graph_client.me.drive.get()
            self.drive_id = drive.id

    async def list_files(self):
        """列出根目录中的文件"""
        try:
            await self.ensure_drive_id()

            # 通过 drive id 访问根目录的 children
            children_result = await self.graph_client.drives.by_drive_id(self.drive_id).items.by_drive_item_id('root').children.get()

            if children_result and children_result.value:
                files = [{'id': item.id, 'name': item.name} for item in children_result.value if item.file]
                return files
            return []

        except Exception as e:
            print(f"✗ 列出文件失败: {e}")
            return []

    async def delete_file(self, file_id: str, file_name: str):
        """删除文件"""
        try:
            await self.ensure_drive_id()
            await self.graph_client.drives.by_drive_id(self.drive_id).items.by_drive_item_id(file_id).delete()
            print(f"  ✓ 删除: {file_name}")
            return True
        except Exception as e:
            print(f"  ✗ 删除失败 {file_name}: {e}")
            return False

    async def upload_image(self, file_name: str):
        """上传随机生成的图片"""
        try:
            await self.ensure_drive_id()
            from PIL import Image, ImageDraw

            # 生成随机彩色图片
            width, height = 800, 600
            img = Image.new('RGB', (width, height), color=(
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255)
            ))

            # 添加一些随机图形
            draw = ImageDraw.Draw(img)
            for _ in range(random.randint(5, 15)):
                x1, y1 = random.randint(0, width), random.randint(0, height)
                x2, y2 = random.randint(0, width), random.randint(0, height)
                # 确保坐标顺序正确
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                shape = random.choice(['rectangle', 'ellipse', 'line'])

                if shape == 'rectangle':
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                elif shape == 'ellipse':
                    draw.ellipse([x1, y1, x2, y2], outline=color, width=3)
                else:
                    draw.line([x1, y1, x2, y2], fill=color, width=3)

            # 添加时间戳文字
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            draw.text((20, 20), f"Generated: {timestamp}", fill=(255, 255, 255))

            # 转换为字节流
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            # 使用 msgraph SDK 上传
            await self.graph_client.drives.by_drive_id(self.drive_id).items.by_drive_item_id('root:/' + file_name + ':').content.put(img_bytes.read())

            print(f"  ✓ 上传图片: {file_name}")
            return True

        except Exception as e:
            print(f"  ✗ 上传图片失败 {file_name}: {e}")
            return False

    async def upload_document(self, file_name: str):
        """上传随机生成的文档"""
        try:
            await self.ensure_drive_id()

            # 生成完全随机的文本内容
            import string

            content = ""
            # 随机生成 20-50 行
            line_count = random.randint(20, 50)

            for _ in range(line_count):
                # 每行随机长度 10-100 个字符
                line_length = random.randint(10, 100)
                # 随机选择字符：字母、数字、空格、标点
                chars = string.ascii_letters + string.digits + ' ' * 5 + string.punctuation
                line = ''.join(random.choice(chars) for _ in range(line_length))
                content += line.strip() + '\n'

            content_bytes = content.encode('utf-8')

            # 使用 msgraph SDK 上传
            result = await self.graph_client.drives.by_drive_id(self.drive_id).items.by_drive_item_id('root:/' + file_name + ':').content.put(content_bytes)

            print(f"  ✓ 上传文档: {file_name}")
            return True

        except Exception as e:
            print(f"  ✗ 上传文档失败 {file_name}: {e}")
            return False


async def main():
    """主函数"""
    try:
        current_time = datetime.now()

        print("=" * 60)
        print(f"E5 存储同步 - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        config = E5Config()
        if not config.validate():
            return

        manager = OneDriveFileManager(config)

        print(f"\n账号: {config.username}")
        print(f"操作位置: OneDrive 根目录")
        print()

        # 列出现有文件
        print("\n正在列出现有文件...")
        files = await manager.list_files()
        print(f"找到 {len(files)} 个文件")

        # 删除文件逻辑：1/20 概率删除所有，19/20 概率删除 6-8 个
        if files:
            # 随机决定删除策略
            delete_all = random.randint(1, 20) == 1  # 1/20 概率

            if delete_all:
                # 删除所有文件
                delete_count = len(files)
                print(f"\n🎲 触发全部删除！准备删除所有 {delete_count} 个文件:")
                files_to_delete = files
            else:
                # 删除 6-8 个文件
                delete_count = random.randint(6, 8)
                delete_count = min(delete_count, len(files))
                print(f"\n准备删除 {delete_count} 个文件:")
                files_to_delete = random.sample(files, delete_count)

            if delete_count > 0:
                deleted = 0
                for file in files_to_delete:
                    if await manager.delete_file(file['id'], file['name']):
                        deleted += 1
                print(f"成功删除 {deleted}/{delete_count} 个文件")

        # 生成并上传 10 个新文件
        print(f"\n准备上传 10 个新文件:")
        uploaded = 0

        # 随机决定图片和文档的比例
        image_count = random.randint(4, 7)
        doc_count = 10 - image_count

        print(f"  图片: {image_count} 个")
        print(f"  文档: {doc_count} 个")
        print()

        # 上传图片 - 使用看起来普通的文件名
        for i in range(image_count):
            # 随机文件名：IMG_{6位随机数}.png
            random_id = random.randint(100000, 999999)
            file_name = f"IMG_{random_id}.png"
            if await manager.upload_image(file_name):
                uploaded += 1

        # 上传文档 - 使用看起来普通的文件名
        for i in range(doc_count):
            # 随机文件名：doc_{6位随机数}.txt 或 note_{6位随机数}.txt
            random_id = random.randint(100000, 999999)
            prefix = random.choice(['doc', 'note', 'memo', 'file'])
            file_name = f"{prefix}_{random_id}.txt"
            if await manager.upload_document(file_name):
                uploaded += 1

        print()
        print("=" * 60)
        print(f"✓ 完成！成功上传 {uploaded}/10 个文件")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 脚本执行出错: {e}")
        traceback.print_exc(file=sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())
