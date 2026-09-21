#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：微信小程序"幸运咖"抓包后，提取 Access-Token（请求头中）
变量：ONESIGN_XYK_TOKEN（Access-Token，多账号用 # 分隔）

签名算法：收集所有参数按 key 字母排序 → 拼接为 k1=v1&k2=v2 → RSA-SHA256(PKCS1v15) → URL-safe Base64

cron: 0 8 * * *
new Env('幸运咖');
"""
import json
import os
import sys
import time
import base64

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_der_private_key
from cryptography.hazmat.backends import default_backend
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 随机延迟 1~30 分钟
import random
_delay = random.randint(60, 1800)
print(f"【幸运咖】随机延迟 {_delay // 60} 分 {_delay % 60} 秒")
time.sleep(_delay)

BASE_URL = "https://xyk.mxbc.net"
APP_ID = "fae0d199f50c8c88a742809706dbbbe6"

PRIVATE_KEY_B64 = """MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCsLXAB3UQmNw4l
IbF/cq+JV/PvfVeoZrAGd3+HCxnACG0K7tN1/APm1QaVF70ZUM0Nrq+JTBn9JHfR
MDz710nZy6SxMLsN7YM3iD0899EflraBjKHNR52SfmeMGtEoCwC/fU2HwLlu7ZTb
z5QlmFcxcmMSHCVr6X3nnN+liAbznBkwKui8cLtkenacDhWA3EwH4aCYBdB/v5HQ
mx9zuTSDuoOiYM1LnGDRrZFymteWRiXStyxpUWqvwKEzjmS+sMVpnbiWqFuc8Nhm
0rTGLdt82gp0zYkX++pRUAlC4k9kIZg6t9h6/q9aBYLXBDL3Z75T6FDQzuCkhtrp
2eE+0GrLAgMBAAECggEAANPbFPc2S6S6Ga2Wx9EKTPOyRXVpxXJw6CcM4t5Hymd/
9qx9MbT7Y9GkTXUmwIdl5OnxCAzolxHkzYmY0XEQds6GxR9B1uhMWCj8el2KkMdN
q0O8x1rPxBN9devvE20yHLmCdOOVQJY9v+y4fpHD4YX2OfEOsP0XUNStMoN73RHh
+xaKr/SyvzWtyJgjO4uywBSIvORFSHVS9TjBi9vxc6+ussz58ZtGgb0X4qA7cCp3
s5CsI9Do9+DfN+qfuZxbTlPPjVdCxR+2DImcFNKfYYXBfwgsg64C4G1Sn2JKabt6
6Lf8MfeNYtUuu7Pv9hMKpKDG6XA8BxnBw+YFt7Q8GQKBgQDhuo2OFHkBopS3iUET
HvCRi/KVvjeFeu94OCMGsZqgkV9aoUAEiWma7bGyKTlE0eEWoMaGCzuiKGHRpEFi
n9N9zgthj00/yr7o5Pq0Gf5tRTnQtaDEOvdZNrl4hZ/U2vnwYChjcN0D9iuZdia6
+tMD02oW6I56Rk/M0SuyK+S+1wKBgQDDRG2WZDNLTiX0fVQO1JFHQtBOxXtBfJlP
mlO2vAhh3E3YJ5bVSb2m/yC/0dGsczOXs6r/XgtkvSNntNAk4DhenrpClor3v+y3
OpqMGvPwIZJk/gVQxDWwcWKDKWtHUSpinOGcFob4SJHvKQ6A6rMHKgFxzvBgaCR4
1wZEbSs5LQKBgBiqIreIoyQ7mJZpZ/Pn6I9uxEX6b+Sk5y+yqpkbpPKwj8O+ZNla
DnEAUe9Os9RCPp8TWD3jUlPIp8+ZbA+TuS9A6VtyphU3WR7njkFJqdRUwRl+DyAB
9W8JHMD/kNRYTQEn8KHU/kFlj6QIFflOWOpNGoWASbkwn52YqXahdzAnAoGBALRg
9crDbQ7XdgBP9eJtQnbNpZfenWl1LDp4mXRoZmXgGJjgmVkV8XfeneYUcNgY40Pz
2LZlrai1f4tBYDVwWyItBmqUnnMWfBkWrcVW8JiWqqFYdpiRZ/dCBnqbPFp5A+ps
eYyy0qNwhj6jcp5sME0h5Iu5Whv0mBx4pXV4U0FRAoGBAKF7tGCKId600S8uvBpy
7xIYRJ+rK3WU0UliO5iWWB6LfRp6qIrBMzuVeSVbQQYkwccAGUgBVTpHlz0GVKX+
cyI1+bnvZzjx+zGz7+tIUP0bYgd18vMsDHA/bBQHJdybAXDuQEUNZQipnweVO43H
D81lAQXDlWOU+9wTRuVvEtR0"""

SUCCESS = True

def Log(cont=''):
    print(cont)


class Signer:
    """幸运咖签名生成器"""

    def __init__(self):
        key_der = base64.b64decode(PRIVATE_KEY_B64)
        self._private_key = load_der_private_key(key_der, password=None, backend=default_backend())

    def sign(self, data: str) -> str:
        """对输入字符串进行 RSA-SHA256 签名，返回 URL-safe Base64"""
        sig = self._private_key.sign(
            data.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.urlsafe_b64encode(sig).decode()

    def sign_get(self, t: str) -> str:
        """GET 请求签名: 对 sorted query string 签名"""
        raw = f"appId={APP_ID}&t={t}"
        return self.sign(raw)

    def sign_post(self, t: str, body_params: dict = None) -> str:
        """POST 请求签名: 合并所有参数，按 key 字母排序后签名"""
        params = {"appId": APP_ID, "t": t}
        if body_params:
            params.update(body_params)
        raw = "&".join(f"{k}={params[k]}" for k in sorted(params.keys()))
        return self.sign(raw)


signer = Signer()


class XingYunKa:
    """幸运咖签到"""

    def __init__(self, token, index):
        global SUCCESS
        self.token = token.strip()
        self.index = index + 1

        self.customer_id = ''
        try:
            parts = self.token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload).decode('utf-8')
                data = json.loads(decoded)
                self.customer_id = str(data.get('sub', ''))
        except Exception:
            pass

        self.s = requests.session()
        self.s.verify = False
        self.base_headers = {
            'version': '3.0.18',
            'content-type': 'application/json',
            'charset': 'utf-8',
            'Access-Token': self.token,
            'x-ssos-cid': self.customer_id,
            'Host': 'xyk.mxbc.net',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; RMX5062 Build/UKQ1.231108.001; wv) AppleWebKit/537.36',
            'Referer': 'https://servicewechat.com/wx060ecb4f74eac0da/166/page-frame.html',
        }

        Log(f"\n{'='*50}")
        Log(f"第{self.index}个账号 - 用户ID: {self.customer_id}")
        Log(f"{'='*50}")

    def _get(self, path, params=None):
        try:
            url = f'{BASE_URL}{path}'
            resp = self.s.get(url, params=params, headers=self.base_headers, timeout=15)
            return resp.json()
        except Exception as e:
            Log(f"  请求错误: {e}")
            return None

    def _post(self, path, data=None):
        try:
            url = f'{BASE_URL}{path}'
            resp = self.s.post(url, json=data, headers=self.base_headers, timeout=15)
            return resp.json()
        except Exception as e:
            Log(f"  请求错误: {e}")
            return None

    def get_user_info(self):
        now_ts = str(int(time.time() * 1000))
        params = {
            't': now_ts,
            'appId': APP_ID,
            'sign': signer.sign_get(now_ts),
        }
        resp = self._get('/api/v1/customer/info', params=params)
        if resp and resp.get('code') == 0:
            info = resp.get('data', {})
            Log(f"  昵称: {info.get('nickname', 'N/A')}")
            Log(f"  积分: {info.get('customerPoint')}, 成长值: {info.get('customerGrowth')}")
            return info
        else:
            code = resp.get('code', -1) if resp else -1
            msg = resp.get('msg', '') if resp else ''
            Log(f"  ❌ 查询用户信息失败: code={code}, msg={msg}")
            return None

    def do_signin(self):
        now_ts = str(int(time.time() * 1000))
        params = {
            't': now_ts,
            'appId': APP_ID,
            'sign': signer.sign_get(now_ts),
        }
        resp = self._get('/api/v1/customer/signin', params=params)
        if resp and resp.get('code') == 0:
            data = resp.get('data', {})
            growth = data.get('ruleValueGrowth', 0)
            point = data.get('ruleValuePoint', 0)
            Log(f"  ✅ 签到成功！成长值 +{growth}, 积分 +{point}")
            return True
        else:
            code = resp.get('code', -1) if resp else -1
            msg = resp.get('msg', '') if resp else ''
            Log(f"  ❌ 签到失败: code={code}, msg={msg}")
            return False

    def run(self):
        Log("\n📋 查询用户信息...")
        info = self.get_user_info()
        if info is None:
            return
        is_signed = info.get('isSignin', 0)
        if is_signed == 1:
            Log("  ⚠️ 今天已经签到过了，跳过")
            return

        time.sleep(1)
        Log("\n📋 执行签到...")
        self.do_signin()


def main():
    global SUCCESS
    token_raw = os.environ.get('ONESIGN_XYK_TOKEN', '')
    if not token_raw:
        Log("❌ 未设置环境变量 ONESIGN_XYK_TOKEN，请设置后重试")
        Log("   变量值为抓包中任意请求的 Access-Token 头，多账号用 # 分隔")
        SUCCESS = False
        sys.exit(1)

    tokens = token_raw.split('#')
    Log(f"幸运咖签到 - 共 {len(tokens)} 个账号")

    for i, token in enumerate(tokens):
        if not token.strip():
            continue
        xyk = XingYunKa(token, i)
        try:
            xyk.run()
            time.sleep(2)
        except Exception as e:
            Log(f"❌ 账号{i+1}异常: {e}")
            SUCCESS = False

    if not SUCCESS:
        sys.exit(1)


if __name__ == '__main__':
    main()