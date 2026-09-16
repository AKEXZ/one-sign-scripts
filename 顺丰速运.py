#!/usr/bin/python3
# -- coding: utf-8 --
"""
ONESIGN_SFSY_TOKEN 支持两种模式：
  mode 1: activityRedirect 完整 URL（推荐，可自动建立新会话）
    抓包方法: 顺丰速运小程序 → 我的 → 积分 → 筛选 activityRedirect → 复制完整 URL
    多账号用 # 分割
  mode 2: linkCode 短码
    从小程序分享链接中提取 linkCode 参数值（如 SFAC20230803190840424）
    脚本会自动构造页面 URL 尝试建立会话
    注意: linkCode 模式仍需在小程序内完成一次微信授权后 cookie 才能生效

Cookie 持久化:
  首次登录成功后 cookie 保存到 local.nosync/.sfsy_cookies.json（gitignore 安全），
  之后运行优先使用已保存的 cookie。
"""
import hashlib
import json
import os
import random
import time
import sys
import requests
from urllib.parse import urlparse, quote, urlunparse
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "顺丰速运"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == 'scripts' else SCRIPT_DIR
# Cookie 文件存到 local.nosync/（已在 .gitignore 中），防止公开仓库泄露
NOSYNC_DIR = os.path.join(COOKIE_DIR, 'local.nosync')
if os.path.exists(NOSYNC_DIR):
    COOKIE_FILE = os.path.join(NOSYNC_DIR, '.sfsy_cookies.json')
else:
    COOKIE_FILE = os.path.join(os.path.expanduser('~'), '.onesign_sfsy_cookies.json')

UA = 'Mozilla/5.0 (Linux; Android 15; RMX5062 Build/UKQ1.231108.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.189 Mobile Safari/537.36 XWEB/1500135 MMWEBSDK/20260502 MMWEBID/784 MicroMessenger/8.0.76.3141(0x28004C54) WeChat/arm64 Weixin NetType/VPN:com.network.proxy Language/zh_CN ABI/arm64 miniProgram/wxd4185d00bf7e08ac'


def Log(cont=''):
    print(cont)


inviteId = [
    '8C3950A023D942FD93BE9218F5BFB34B',
    'EF94619ED9C84E968C7A88CFB5E0B5DC',
    '9C92BD3D672D4B6EBB7F4A488D020C79',
    '803CF9D1E0734327BDF67CDAE1442B0E',
    '00C81F67BE374041A692FA034847F503',
]


def load_cookies():
    """加载所有账号的持久化 cookie。返回 list[dict] 或空列表。"""
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, IOError) as e:
        Log(f"[Cookie] 读取 cookie 文件失败: {e}")
    return []


def save_cookies(all_cookies):
    """保存所有账号的 cookie 到文件。"""
    try:
        with open(COOKIE_FILE, 'w') as f:
            json.dump(all_cookies, f, ensure_ascii=False, indent=2)
        Log(f"[Cookie] 已保存 {len(all_cookies)} 个账号的 cookie")
    except IOError as e:
        Log(f"[Cookie] 保存 cookie 失败: {e}")


class RUN:
    def __init__(self, info, index, saved_cookies=None):
        self.index = index + 1
        self.redirect_url = info.strip()
        Log(f"\n---------开始执行第{self.index}个账号>>>>>")
        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            'Host': 'mcs-mimp-web.sf-express.com',
            'user-agent': UA,
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'application/json',
            'platform': 'MINI_PROGRAM',
            'channel': 'mypoint',
            'origin': 'https://mcs-mimp-web.sf-express.com',
            'x-requested-with': 'com.tencent.mm',
        }

        self.phone = ''
        self.login_res = False

        # 1) 优先尝试已保存的 cookie
        if saved_cookies and self._try_cookie_login(saved_cookies):
            self.login_res = True
        else:
            # 2) cookie 过期，用 redirect URL 重新登录
            self.login_res = self._login_with_redirect()

    def get_deviceId(self, characters='abcdef0123456789'):
        result = ''
        for char in 'xxxxxxxx-xxxx-xxxx':
            if char == 'x':
                result += random.choice(characters)
            elif char == 'X':
                result += random.choice(characters).upper()
            else:
                result += char
        return result

    def _try_cookie_login(self, saved_cookies):
        """尝试用已保存的 cookie 恢复会话，返回 True 表示 cookie 有效。"""
        for cookie in saved_cookies:
            self.s.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))

        # 从已保存的元数据恢复 phone
        if saved_cookies:
            self.user_id = saved_cookies[0].get('_login_user_id_', '')
            self.phone = saved_cookies[0].get('_login_mobile_', '')
        self.mobile = self.phone[:3] + "*" * 4 + self.phone[7:] if len(self.phone) >= 11 else self.phone

        Log(f'尝试使用已保存的 cookie 恢复会话...')

        self.getSign()
        try:
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralSignV2Service~getTodaySign'
            resp = self.s.post(url, headers=self.headers, json={})
            res = resp.json()
            if res.get('success') == True:
                day_count = res.get('obj', {}).get('dayCount', 0)
                if self.phone:
                    Log(f'✅ Cookie 有效，用户:【{self.mobile}】连续签到{day_count}天')
                else:
                    Log(f'✅ Cookie 有效，连续签到{day_count}天')
                return True
            else:
                error_msg = res.get('errorMessage', '未知错误')
                Log(f'⚠️ Cookie 已过期 ({error_msg})')
                return False
        except Exception as e:
            Log(f'⚠️ Cookie 验证失败: {e}')
            return False

    def get_cookies_for_save(self):
        """导出当前 session 的 cookie 用于持久化保存。"""
        cookies = []
        for cookie in self.s.cookies:
            cookies.append({
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
            })
        if cookies:
            cookies[0]['_login_user_id_'] = getattr(self, 'user_id', '')
            cookies[0]['_login_mobile_'] = getattr(self, 'phone', '')
        return cookies

    def _fix_url_encoding(self, url):
        """修复 URL query string 中的 + / = 等字符编码"""
        parsed = urlparse(url)
        if not parsed.query:
            return url
        pairs = []
        for pair in parsed.query.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                v = quote(v, safe='%')
                pairs.append(f'{k}={v}')
            else:
                pairs.append(pair)
        return urlunparse(parsed._replace(query='&'.join(pairs)))

    def _login_with_redirect(self):
        """用 redirect URL 或 linkCode 建立会话"""
        if not self.redirect_url:
            Log('❌ 无 redirect URL，无法重新登录（纯 cookie 模式需要重新抓包并设置 ONESIGN_SFSY_TOKEN）')
            return False

        # 判断输入类型: linkCode 短码 vs 完整 URL
        is_linkcode = not self.redirect_url.startswith('http')
        if is_linkcode:
            link_code = self.redirect_url.strip()
            page_url = (
                f'https://mcs-mimp-web.sf-express.com/up-member/newPoints'
                f'?linkCode={link_code}&from=mypoint&supportShare=YES'
            )
            Log(f'[linkCode 模式] {link_code}')
        else:
            page_url = self.redirect_url
            Log(f'[redirect URL 模式]')

        # 修复 URL 编码：抓包工具可能不编码 + / = 等字符，
        # 但 requests 库会把 + 当空格发送，导致 base64 参数校验失败
        page_url = self._fix_url_encoding(page_url)

        Log(f'发起请求建立会话...')
        try:
            # 先不跟随重定向，捕获服务器返回的初始 cookie
            ress = self.s.get(page_url, headers=self.headers, allow_redirects=False, timeout=15)

            # 逐跳跟随重定向（手动跟随以捕获每一跳的 cookie）
            redirect_count = 0
            while ress.status_code in (301, 302, 303, 307, 308) and redirect_count < 5:
                location = ress.headers.get('Location', '')
                if not location:
                    break
                redirect_count += 1
                Log(f'  第{redirect_count}跳: {location[:80]}...')
                ress = self.s.get(location, headers=self.headers, allow_redirects=False, timeout=15)

            # 尝试提取用户 cookie
            cookie_dict = self.s.cookies.get_dict()
            self.user_id = cookie_dict.get('_login_user_id_', '')
            self.phone = cookie_dict.get('_login_mobile_', '')
            self.mobile = self.phone[:3] + "*" * 4 + self.phone[7:] if len(self.phone) >= 11 else self.phone
            jsessionid = cookie_dict.get('JSESSIONID', '')

            if self.phone:
                Log(f'✅ 登录成功，用户:【{self.mobile}】')
                return True

            # 无用户认证信息
            if is_linkcode:
                Log(f'⚠️ linkCode 方式未获取到用户认证')
                Log(f'   需要在微信中打开该小程序链接完成授权后，cookie 才能生效')
                if jsessionid:
                    Log(f'   当前获得 JSESSIONID={jsessionid[:16]}...（待授权）')
            else:
                if jsessionid:
                    Log(f'❌ Redirect URL 已失效（session 存在但无用户信息，OAuth code 已过期）')
                else:
                    Log(f'❌ Redirect URL 已失效，未能建立会话')

            return False
        except requests.RequestException as e:
            Log(f'❌ 登录请求失败: {e}')
            return False

    def getSign(self):
        timestamp = str(int(round(time.time() * 1000)))
        token = 'wwesldfs29aniversaryvdld29'
        sysCode = 'MCS-MIMP-CORE'
        data = f'token={token}&timestamp={timestamp}&sysCode={sysCode}'
        signature = hashlib.md5(data.encode()).hexdigest()
        data = {
            'sysCode': sysCode,
            'timestamp': timestamp,
            'signature': signature
        }
        self.headers.update(data)
        return data

    def do_request(self, url, data=None, req_type='post'):
        self.getSign()
        try:
            if req_type.lower() == 'get':
                response = self.s.get(url, headers=self.headers)
            elif req_type.lower() == 'post':
                response = self.s.post(url, headers=self.headers, json=data or {})
            else:
                raise ValueError('Invalid req_type: %s' % req_type)
            res = response.json()
            return res
        except requests.exceptions.RequestException as e:
            print('Request failed:', e)
            return None
        except json.JSONDecodeError as e:
            print('JSON decoding failed:', e)
            return None

    def sign(self):
        print(f'>>>>>>开始执行签到')
        # V2: 先查今日签到状态
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralSignV2Service~getTodaySign'
        response = self.do_request(url, data={})
        if response and response.get('success') == True:
            obj = response.get('obj', {})
            if obj.get('signed'):
                day_count = obj.get('dayCount', 0)
                bubble_text = obj.get('bubbleText', '')
                Log(f'今日已签到，连续签到{day_count}天（{bubble_text}）')
            else:
                # 未签到，执行签到
                sign_url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralSignV2Service~signAwardPool'
                sign_resp = self.do_request(sign_url, data={})
                if sign_resp and sign_resp.get('success') == True:
                    gifts = sign_resp.get('obj', [])
                    if gifts:
                        gift_names = ', '.join([g.get('giftBagName', '未知') for g in gifts])
                        Log(f'签到成功！获得: {gift_names}')
                    else:
                        Log(f'签到成功！')
                else:
                    error_message = sign_resp.get('errorMessage') if sign_resp else '无返回'
                    print(f'签到失败: {error_message}')
        else:
            error_message = response.get('errorMessage') if response else '无返回'
            print(f'签到状态查询失败: {error_message}')

    def get_SignTaskList(self, END=False):
        if not END:
            print(f'>>>开始获取签到任务列表')
        json_data = {
            'channelType': '3',
            'deviceId': self.get_deviceId(),
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~queryPointTaskAndSignFromES'
        response = self.do_request(url, data=json_data)
        if response and response.get('success') == True and response.get('obj') != []:
            totalPoint = response["obj"]["totalPoint"]
            if END:
                Log(f'当前积分：【{totalPoint}】')
                return
            Log(f'执行前积分：【{totalPoint}】')
            for task in response["obj"]["taskTitleLevels"]:
                self.taskId = task["taskId"]
                self.taskCode = task["taskCode"]
                self.strategyId = task["strategyId"]
                self.title = task["title"]
                status = task["status"]
                skip_title = ['用行业模板寄件下单', '去新增一个收件偏好', '参与积分活动']
                if status == 3:
                    print(f'>{self.title}-已完成')
                    continue
                if self.title in skip_title:
                    print(f'>{self.title}-跳过')
                    continue
                else:
                    self.doTask()
                    time.sleep(3)
                self.receiveTask()
        else:
            error_message = response.get('errorMessage') if response else '无返回'
            print(f'获取任务列表失败: {error_message}')

    def doTask(self):
        print(f'>>>开始去完成【{self.title}】任务')
        json_data = {
            'taskCode': self.taskCode,
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonRoutePost/memberEs/taskRecord/finishTask'
        response = self.do_request(url, data=json_data)
        if response and response.get('success') == True:
            print(f'>【{self.title}】任务-已完成')
        else:
            error_message = response.get('errorMessage') if response else '无返回'
            print(f'>【{self.title}】任务-{error_message}')

    def receiveTask(self):
        print(f'>>>开始领取【{self.title}】任务奖励')
        json_data = {
            "strategyId": self.strategyId,
            "taskId": self.taskId,
            "taskCode": self.taskCode,
            "deviceId": self.get_deviceId()
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~fetchIntegral'
        response = self.do_request(url, data=json_data)
        if response and response.get('success') == True:
            print(f'>【{self.title}】任务奖励领取成功！')
        else:
            error_message = response.get('errorMessage') if response else '无返回'
            print(f'>【{self.title}】任务-{error_message}')

    def main(self):
        if not self.login_res:
            Log(f'\n❌ 第{self.index}个账号登录失败，跳过')
            Log(f'   可能原因: cookie 过期且 redirect URL 中的 OAuth code 已失效')
            Log(f'   解决方法: 重新抓包获取 activityRedirect URL')
            return False
        self.sign()
        self.get_SignTaskList()
        self.get_SignTaskList(END=True)
        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_SFSY_TOKEN', '')
    saved_cookies_list = load_cookies()

    if not token:
        if not saved_cookies_list:
            print("未配置 ONESIGN_SFSY_TOKEN 变量，且无已保存的 cookie")
            print("首次使用需抓包: 小程序 → 我的 → 积分 → 找到 activityRedirect 请求 → 复制完整 URL")
            print("或手动将抓包中的 Cookie 写入 .sfsy_cookies.json")
            sys.exit(1)
        tokens = [''] * len(saved_cookies_list)
        print(f"[Cookie模式] 共{len(tokens)}个账号（纯 cookie，无 redirect URL 回退）")
    else:
        tokens = token.split('#')
        tokens = [t for t in tokens if t]
        print(f"共获取到{len(tokens)}个账号")

    success = True
    all_cookies = []
    for idx, info in enumerate(tokens):
        saved_ck = saved_cookies_list[idx] if idx < len(saved_cookies_list) else None
        runner = RUN(info, idx, saved_cookies=saved_ck)
        run_result = runner.main()
        if not run_result:
            success = False
        all_cookies.append(runner.get_cookies_for_save())

    save_cookies(all_cookies)

    if not success:
        sys.exit(1)