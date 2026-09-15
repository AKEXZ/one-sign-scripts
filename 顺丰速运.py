#!/usr/bin/python3
# -- coding: utf-8 --
"""
抓包步骤（仅在 cookie 过期且 redirect URL 失效时）：
  打开顺丰速运小程序 → 我的 → 积分
  抓包筛选 activityRedirect
  复制完整 URL，设置到 ONESIGN_SFSY_TOKEN 变量中
  多账号用 # 分割

Cookie 持久化：
  首次登录成功后 cookie 会保存到同目录下的 .sfsy_cookies.json，
  之后运行会优先使用已保存的 cookie。
  当 cookie 过期时会尝试用 redirect URL 重新登录；
  仅当 cookie 和 redirect URL 都失效时才需要重新抓包。
"""
import hashlib
import json
import os
import random
import time
import sys
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "顺丰速运"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(SCRIPT_DIR, ".sfsy_cookies.json")

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090551) XWEB/6945 Flue'


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
            'upgrade-insecure-requests': '1',
            'user-agent': UA,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'zh-CN,zh',
            'platform': 'MINI_PROGRAM',
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
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~automaticSignFetchPackage'
            resp = self.s.post(url, headers=self.headers, json={"comeFrom": "vioin", "channelFrom": "WEIXIN"})
            res = resp.json()
            if res.get('success') == True or (
                res.get('errorCode') and 'login' not in str(res.get('errorMessage', '')).lower()
            ):
                if self.phone:
                    Log(f'✅ Cookie 有效，用户:【{self.mobile}】恢复会话成功')
                else:
                    Log(f'✅ Cookie 有效，会话恢复成功')
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

    def _login_with_redirect(self):
        """用 activityRedirect URL 重新登录"""
        if not self.redirect_url:
            Log('❌ 没有可用的 redirect URL，无法登录')
            return False

        Log(f'用 redirect URL 重新登录...')
        try:
            ress = self.s.get(self.redirect_url, headers=self.headers, allow_redirects=True, timeout=15)

            # 检查是否被重定向到登录页
            if ress.status_code == 302 or 'login' in (ress.url or '').lower():
                Log(f'❌ Redirect URL 已失效（OAuth code 已过期或已使用），请重新抓包')
                Log(f'   小程序: 顺丰速运 → 我的 → 积分 → 抓 activityRedirect 请求')
                return False

            self.user_id = self.s.cookies.get_dict().get('_login_user_id_', '')
            self.phone = self.s.cookies.get_dict().get('_login_mobile_', '')
            self.mobile = self.phone[:3] + "*" * 4 + self.phone[7:] if len(self.phone) >= 11 else self.phone

            if self.phone:
                Log(f'✅ 登录成功，用户:【{self.mobile}】')
                return True
            else:
                Log(f'❌ 登录失败：未能获取用户信息（redirect URL 可能已过期）')
                Log(f'   请重新抓包获取新的 activityRedirect URL')
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
        json_data = {"comeFrom": "vioin", "channelFrom": "WEIXIN"}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~automaticSignFetchPackage'
        response = self.do_request(url, data=json_data)
        if response and response.get('success') == True:
            count_day = response.get('obj', {}).get('countDay', 0)
            if response.get('obj') and response['obj'].get('integralTaskSignPackageVOList'):
                packet_name = response["obj"]["integralTaskSignPackageVOList"][0]["packetName"]
                Log(f'>>>签到成功，获得【{packet_name}】，本周累计签到【{count_day + 1}】天')
            else:
                Log(f'今日已签到，本周累计签到【{count_day + 1}】天')
        else:
            error_message = response.get('errorMessage') if response else '无返回'
            print(f'签到失败: {error_message}')

    def superWelfare_receiveRedPacket(self):
        print(f'>>>>>>超值福利签到')
        json_data = {
            'channel': 'czflqdlhbxcx'
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberActLengthy~redPacketActivityService~superWelfare~receiveRedPacket'
        response = self.do_request(url, data=json_data)
        if response and response.get('success') == True:
            gift_list = response.get('obj', {}).get('giftList', [])
            if response.get('obj', {}).get('extraGiftList', []):
                gift_list.extend(response['obj']['extraGiftList'])
            gift_names = ', '.join([gift['giftName'] for gift in gift_list])
            receive_status = response.get('obj', {}).get('receiveStatus')
            status_message = '领取成功' if receive_status == 1 else '已领取过'
            Log(f'超值福利签到[{status_message}]: {gift_names}')
        else:
            error_message = response.get('errorMessage') if response else '无返回'
            print(f'超值福利签到失败: {error_message}')

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
        self.superWelfare_receiveRedPacket()
        self.get_SignTaskList()
        self.get_SignTaskList(END=True)
        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_SFSY_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_SFSY_TOKEN 变量")
        print("抓包获取: 小程序 → 我的 → 积分 → 找到 activityRedirect 请求 → 复制完整 URL")
        print("首次运行必须抓包，之后 cookie 会自动持久化，过期前无需重新抓包。")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")

    saved_cookies_list = load_cookies()

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