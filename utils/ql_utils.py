import requests
import os
import json
import inspect

class QLUtils:
    # 青龙面板默认配置
    _QL_HOST = "http://127.0.0.1:5700/open"
    _CONFIG_PATH = "/ql/data/config/auth.json"

    @staticmethod
    def disable_self(script_name=None):
        """对外接口：禁用自身脚本"""
        # 自动获取调用者文件名
        if not script_name:
            caller_frame = inspect.stack()[1]
            script_name = os.path.basename(caller_frame.filename)
        
        # 调用内部方法链
        token = QLUtils._get_local_token()
        if not token:
            return {"code": -1, "message": "获取令牌失败"}
        
        script_id = QLUtils._get_script_id(token, script_name)
        if not script_id:
            return {"code": -1, "message": f"未找到脚本 {script_name} 的ID"}
        
        return QLUtils._disable_script(token, script_id)

    @staticmethod
    def _get_local_token():
        """内部方法：获取本地令牌"""
        try:
            with open(QLUtils._CONFIG_PATH, 'r') as f:
                auth_data = json.load(f)
                return auth_data.get("token")
        except Exception as e:
            print(f"[内部错误] 获取令牌失败: {e}")
            return None

    @staticmethod
    def _get_script_id(token, script_name):
        """内部方法：获取脚本ID"""
        try:
            url = f"{QLUtils._QL_HOST}/crons"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response = requests.get(url, headers=headers)
            crons = response.json().get("data", []).get("data", [])

            for cron in crons:
                if os.path.basename(cron.get("command", "")) == script_name:
                    return cron.get("id")
            return None
        except Exception as e:
            print(f"[内部错误] 获取脚本ID失败: {e}")
            return None

    @staticmethod
    def _disable_script(token, script_id):
        """内部方法：禁用脚本"""
        try:
            url = f"{QLUtils._QL_HOST}/api/crons/disable/{script_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response = requests.put(url, headers=headers)
            return response.json()
        except Exception as e:
            return {"code": -1, "message": f"禁用失败: {str(e)}"}

    @staticmethod
    def set_config(host=None, path=None):
        """对外接口：修改配置（如非默认路径）"""
        if host:
            QLUtils._QL_HOST = host
        if path:
            QLUtils._CONFIG_PATH = path

# 测试用例
if __name__ == "__main__":
    # 如需修改配置，可在调用前设置
    # QLUtils.set_config(host="http://127.0.0.1:5701")
    
    result = QLUtils.disable_self()
    print(result)
