#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：抓包工具中筛选 eco.trantor.top，找到任意请求的 Authorization 头，复制 Bearer 后面的完整 JWT token
变量：ONESIGN_VMTDD_TOKEN（Bearer token，多账号用 # 分隔）
      可选变量 ONESIGN_VMTDD_LOCATION（经纬度，格式 "lat,lon"，用于获取推荐打卡点列表，默认洛阳）
      可选变量 ONESIGN_VMTDD_REGION（城市名，用于获取推荐打卡点，默认洛阳市）

cron: 10 7 * * *
new Env('维迈通多多签到');
"""
import json
import math
import os
import sys
import time
import random
from datetime import datetime

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 随机延迟 1~30 分钟
_delay = random.randint(60, 1800)
print(f"【维迈通多多】随机延迟 {_delay // 60} 分 {_delay % 60} 秒")
time.sleep(_delay)

SCRIPT_NAME = "维迈通多多"
BASE_URL = "https://eco.trantor.top"
success = True


def Log(cont=''):
    print(cont)


# ============================================================
# RUN 类 - 单账号签到 & 任务
# ============================================================

class RUN:
    def __init__(self, info, index):
        global success
        self.token = info.strip()
        self.index = index + 1

        # 解析位置信息（支持环境变量，多个账号位置不同时也用 # 分隔）
        location_raw = os.environ.get('ONESIGN_VMTDD_LOCATION', '34.15083803941892,112.47299011458907')
        region_raw = os.environ.get('ONESIGN_VMTDD_REGION', '洛阳市')
        locations = location_raw.split('#')
        regions = region_raw.split('#')
        loc_idx = index % len(locations)
        reg_idx = index % len(regions)
        self.location = locations[loc_idx].strip()
        self.region_name = regions[reg_idx].strip()

        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            'version': '260906001',
            'user-agent': 'okhttp/4.12.0 (Linux; U; Android 15; RMX5062 Build/UKQ1.231108.001)',
            'language': 'zh_CN',
            'Authorization': f'Bearer {self.token}',
            'Host': 'eco.trantor.top',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
        }

        # 从 token 中解析用户信息
        self._parse_token()

        Log(f"\n---------开始执行第{self.index}个账号>>>>>")
        if self.user_id:
            Log(f"用户: {self.username} (ID: {self.user_id})")
        Log(f"位置: {self.region_name} ({self.location})")

    def _parse_token(self):
        self.user_id = ''
        self.username = '未知'
        try:
            parts = self.token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                import base64
                decoded = base64.b64decode(payload).decode('utf-8')
                data = json.loads(decoded)
                if isinstance(data, list) and len(data) >= 2:
                    self.user_id = str(data[0])
                    self.username = str(data[1])
        except Exception:
            pass

    def _post(self, path, data=None):
        try:
            if data:
                resp = self.s.post(
                    f'{BASE_URL}{path}',
                    data=data,
                    headers=self.headers,
                    timeout=15,
                )
            else:
                resp = self.s.post(
                    f'{BASE_URL}{path}',
                    headers=self.headers,
                    timeout=15,
                )
            return resp.json()
        except requests.RequestException as e:
            Log(f"请求错误: {e}")
            return None
        except json.JSONDecodeError:
            Log(f"响应解析失败: {resp.text[:200] if 'resp' in dir() else ''}")
            return None

    def _sleep(self, label=''):
        delay = 1.5 + random.uniform(0, 1)
        if label:
            Log(f"  ⏳ {label}，等待 {delay:.1f}s...")
        time.sleep(delay)

    # ---- 签到 ----

    def sign_info(self):
        Log("查询签到状态...")
        result = self._post('/ecosystem/integral/operation/signInfo')
        if result and result.get('code') == 0:
            data = result['data']
            is_sign = '已签到' if data.get('isSign') == 1 else '未签到'
            Log(f"  状态: {is_sign} | 连续签到: {data.get('continuousTimes', 0)}天 | 今日积分: {data.get('todayScore', '0')}")
            return data
        else:
            Log(f"  查询失败: {result}")
            return None

    def sign(self):
        global success
        Log("执行签到...")
        result = self._post('/ecosystem/integral/operation/sign')
        if result and result.get('code') == 0:
            Log(f"  签到成功！{result.get('msg', '')}")
            return True
        elif result and result.get('code') == 1 and '已经签到' in result.get('msg', ''):
            Log("  今日已签到，无需重复")
            return True
        else:
            Log(f"  签到失败: {result}")
            success = False
            return False

    # ---- 领取积分 ----

    def receive_integral(self):
        Log("领取待领积分...")
        result = self._post('/ecosystem/integral/operation/receive', data='id=all&type=0')
        if result and result.get('code') == 0:
            Log("  领取成功！")
            return True
        elif result and result.get('code') == 1 and '领取失败' in result.get('msg', ''):
            Log("  暂无待领取积分")
            return True
        else:
            Log(f"  领取异常: {result}")
            global success
            success = False
            return False

    # ---- 积分 ----

    def my_points(self, end=False):
        global success
        label = '执行后' if end else '当前'
        result = self._post('/ecosystem/integral/userIntegral/myIntegral')
        if result and result.get('code') == 0:
            data = result['data']
            Log(f"  {label}积分: {data.get('value', '0')}" +
                (f" (即将过期: {data.get('expirationValue', '0')})" if data.get('expirationValue', '0') != '0' else ""))
            return data
        else:
            Log(f"  查询积分失败: {result}")
            success = False
            return None

    # ---- 任务列表 ----

    def task_list(self):
        Log("获取任务列表...")
        result = self._post('/ecosystem/integral/operation/v1/integralDataList')
        if result and result.get('code') == 0:
            data = result['data']
            Log("  ── 每日任务 ──")
            for task in data.get('dailyTasks', []):
                status = '✅' if task.get('receiveStatus') == 1 else '⬜'
                Log(f"  {status} {task['taskTitle']} (+{task['value']}积分)")
            Log("  ── 进阶任务 ──")
            for task in data.get('advancedTasks', []):
                status = '✅' if task.get('receiveStatus') == 1 else '⬜'
                Log(f"  {status} {task['taskTitle']} (+{task['value']}积分)")
            return data
        else:
            Log(f"  获取任务列表失败: {result}")
            return None

    # ---- 点赞任务 ----

    def _get_recommend_punchpoints(self, need_count=5):
        punch_ids = []
        seen = set()
        next_page = None

        # 第一页: 不带 page 参数，通常只返回 2 个
        params = {
            'location': self.location,
            'type': '1',
            'regionName': self.region_name,
        }
        result = self._post('/ecosystem/punchpoint/recommend', data=params)
        if result and result.get('code') == 0:
            data = result['data']
            for item in data.get('list', []):
                if item['punchId'] not in seen:
                    punch_ids.append(item['punchId'])
                    seen.add(item['punchId'])
            next_page = data.get('nextPage')

        # 如果不够 need_count 个，用 nextPage 翻页获取更多 (每页最多 20 个)
        while len(punch_ids) < need_count and next_page:
            self._sleep()
            params['page'] = next_page
            result = self._post('/ecosystem/punchpoint/recommend', data=params)
            if result and result.get('code') == 0:
                data = result['data']
                for item in data.get('list', []):
                    if item['punchId'] not in seen:
                        punch_ids.append(item['punchId'])
                        seen.add(item['punchId'])
                next_page = data.get('nextPage')
            else:
                break

        return punch_ids

    def _like_punchpoint(self, punch_id):
        result = self._post('/ecosystem/useraction/like', data={
            'punchId': str(punch_id),
            'type': '1',
        })
        return result and result.get('code') == 0

    def do_like_task(self, count=5):
        global success
        Log(f"执行点赞任务 (目标: {count}个打卡点)...")

        punch_ids = self._get_recommend_punchpoints()
        if not punch_ids:
            Log("  没有可点赞的打卡点")
            return False

        target = min(count, len(punch_ids))
        ok = 0
        for i in range(target):
            pid = punch_ids[i]
            if self._like_punchpoint(pid):
                Log(f"  [{i+1}/{target}] 点赞 punchId={pid} 成功")
                ok += 1
            else:
                Log(f"  [{i+1}/{target}] 点赞 punchId={pid} 失败")
                success = False
            if i < target - 1:
                self._sleep()

        Log(f"  点赞完成: {ok}/{target}")
        return ok >= target

    # ---- 骑行模拟 ----

    def _generate_trajectory(self, start_lat, start_lon, distance_m=1500, points_per_km=150, time_offset_s=0):
        # 平均速度 8 m/s (~29 km/h)，每点时间间隔
        avg_speed_mps = 8.0

        # 使用正弦曲线模拟真实山路的海拔变化
        alt_base = random.uniform(50, 400)
        alt_amplitude = random.uniform(30, 200)
        alt_phase = random.uniform(0, math.pi * 2)
        alt_freq = random.uniform(1.5, 3.5)

        # 随机初始方向 (度)
        bearing = random.uniform(0, 360)
        bearing_rad = math.radians(bearing)

        # 每米对应的经纬度增量
        lat_per_m = 1.0 / 111320.0
        lon_per_m = 1.0 / (111320.0 * math.cos(math.radians(start_lat)))

        points_count = max(60, int(distance_m / 1000.0 * points_per_km))
        step_m = distance_m / points_count
        step_time_ms = int(step_m / avg_speed_mps * 1000)  # 每点时间间隔(ms)

        base_ms = int(time.time() * 1000) - time_offset_s * 1000
        points = []

        current_lat = start_lat
        current_lon = start_lon
        prev_speed = random.uniform(5, 20)

        for i in range(points_count):
            progress = i / points_count

            # 方向：在初始方向上叠加平滑的正弦偏移，形成弯曲路径
            turn_amount = math.sin(progress * math.pi * random.uniform(1.5, 3.0)) * random.uniform(20, 50)
            turn_amount += random.uniform(-3, 3)  # 小幅随机抖动
            cur_bearing = bearing_rad + math.radians(turn_amount)

            lat_offset = step_m * lat_per_m * math.cos(cur_bearing)
            lon_offset = step_m * lon_per_m * math.sin(cur_bearing)

            current_lat += lat_offset
            current_lon += lon_offset

            # 海拔：正弦曲线 + 随机噪声，限制在 9~500
            raw_alt = alt_base + alt_amplitude * math.sin(progress * math.pi * alt_freq + alt_phase)
            alt_noise = random.uniform(-8, 8)
            alt = round(raw_alt + alt_noise, 1)
            alt = max(9.0, min(500.0, alt))

            # 速度：模拟真实骑行 (0~98 km/h)
            if progress < 0.05:
                # 起步加速
                target_speed = random.uniform(0, 15)
            elif progress > 0.9:
                # 减速停车
                target_speed = random.uniform(0, 10)
            elif random.random() < 0.03:
                # 偶然急刹车/等红灯
                target_speed = random.uniform(0, 3)
            elif random.random() < 0.08:
                # 偶有加速冲刺
                target_speed = random.uniform(55, 95)
            elif random.random() < 0.1:
                # 低速行驶
                target_speed = random.uniform(5, 20)
            else:
                # 正常巡航
                target_speed = random.uniform(18, 50)

            # 平滑速度过渡
            speed = round(prev_speed + (target_speed - prev_speed) * random.uniform(0.3, 0.7), 3)
            speed = max(0.0, min(98.0, speed))
            prev_speed = speed

            ts = base_ms - (points_count - i) * step_time_ms

            points.append(f"{round(current_lat, 6)},{round(current_lon, 6)},{alt},0.0,{speed},{ts}")

        return ';'.join(points), base_ms, points_count

    def _upload_trajectory_batch(self, user_id, pos_items, upload_time_ms):
        """一次上传多个 .pos 轨迹文件 (匹配真实 App 行为)"""
        # pos_items: [(group_id, pos_content, ride_time_ms), ...]

        files = []
        weather_data = {}
        through_city_data = {}

        for group_id, pos_content, ride_time_ms in pos_items:
            filename = f"{group_id}_{user_id}_{ride_time_ms}_1.5.27.11.pos"
            files.append(('file', (filename, pos_content.encode('utf-8'), 'application/octet-stream')))
            weather_data[filename] = [{"1": "1"}]
            through_city_data[filename] = [{"1": self.region_name}]

        data = {
            'token': self.token,
            'time': str(upload_time_ms),
            'weather': json.dumps(weather_data),
            'throughCity': json.dumps(through_city_data),
        }

        try:
            resp = requests.post(
                'https://data.trantor.top/uploadLocationFile/trajectory',
                data=data,
                files=files,
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            Log(f"  轨迹上传异常: {e}")
            return None

    def simulate_riding(self):
        global success
        Log("模拟单人骑行...")

        lat_parts = self.location.split(',')
        try:
            lat = float(lat_parts[0].strip())
            lon = float(lat_parts[1].strip())
        except (ValueError, IndexError):
            Log("  位置解析失败，使用默认坐标")
            lat, lon = 34.1509, 112.4730

        # 1. 上报设备连接
        Log("  上报设备连接...")
        device_result = self._post('/ecosystem/deviceConnect/report', data={
            'province': '河南省',
            'city': self.region_name,
            'location': self.location,
            'deviceModel': 'SOAIY GD36',
            'macAddress': '41:42:F8:68:33:6B',
        })
        if device_result and device_result.get('code') == 0:
            Log("  设备连接上报成功")
        else:
            Log(f"  设备连接上报失败: {device_result}")

        self._sleep()

        # 2. 生成 2 段轨迹 (模拟两次骑行，匹配真实 App 行为)
        user_id = self.user_id or '2960774'

        avg_speed_mps = 8.0

        pos_items = []
        total_points = 0
        total_distance = 0
        for i in range(2):
            distance = random.randint(1500, 5000)
            # 估算骑行时长，用于计算合理的时间偏移
            estimated_duration_s = int(distance / avg_speed_mps)
            # 两段之间间隔 1~3 分钟
            gap_s = random.randint(60, 180)
            time_offset_s = (2 - i) * (estimated_duration_s + gap_s)

            pos_content, ride_time_ms, pts_count = self._generate_trajectory(
                lat, lon, distance_m=distance, time_offset_s=time_offset_s
            )
            group_id = random.randint(1000000000, 9999999999)
            pos_items.append((group_id, pos_content, ride_time_ms))
            total_points += pts_count
            total_distance += distance

            Log(f"  第{i + 1}段: {distance}m, {pts_count}点, 约{estimated_duration_s // 60}分{estimated_duration_s % 60}秒, group_id={group_id}")
            if i == 0:
                self._sleep()

        upload_time_ms = int(time.time() * 1000)
        Log(f"  上传 {len(pos_items)} 段轨迹 (共{total_distance}m, {total_points}点) ...")
        upload_result = self._upload_trajectory_batch(user_id, pos_items, upload_time_ms)
        if upload_result and upload_result.get('code') == 200:
            Log("  轨迹上传成功！")
            return True
        else:
            Log(f"  轨迹上传失败: {upload_result}")
            success = False
            return False

    # ---- 群组对讲 ----

    def _upload_group_trajectory(self, user_id, pos_content, ride_time_ms, upload_time_ms):
        """群组对讲专用上传 (1个文件, timestamp格式weather/throughCity, 尾部终止标记)"""
        filename = f"{random.randint(1000000000, 9999999999)}_{user_id}_{ride_time_ms}_1.5.27.11.pos"

        # 群组对讲格式: timestamp:value 而不是 1:value
        weather_ts = str(ride_time_ms // 1000)
        temperature = str(random.randint(15, 35))
        weather_data = {filename: [{weather_ts: temperature}]}
        through_city_data = {filename: [{weather_ts: self.region_name}]}

        # 轨迹尾部追加终止标记 0,0,0,0,0,ending_ts
        ending_content = pos_content + f";0,0,0,0,0,{upload_time_ms}"

        files = [
            ('file', (filename, ending_content.encode('utf-8'), 'application/octet-stream')),
        ]
        data = {
            'token': self.token,
            'time': str(upload_time_ms),
            'weather': json.dumps(weather_data),
            'throughCity': json.dumps(through_city_data),
        }

        try:
            resp = requests.post(
                'https://data.trantor.top/uploadLocationFile/trajectory',
                data=data,
                files=files,
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            Log(f"  轨迹上传异常: {e}")
            return None

    def simulate_group_intercom(self):
        global success
        Log("模拟群组对讲...")

        lat_parts = self.location.split(',')
        try:
            lat = float(lat_parts[0].strip())
            lon = float(lat_parts[1].strip())
        except (ValueError, IndexError):
            Log("  位置解析失败，使用默认坐标")
            lat, lon = 34.1509, 112.4730

        user_id = self.user_id or '2960774'

        # 1. 打卡记录上报
        Log("  上报打卡记录...")
        try:
            punch_ids = self._get_recommend_punchpoints(need_count=2)
        except Exception:
            punch_ids = []
        if len(punch_ids) >= 2:
            punch_param = f"punchIds=%5B{punch_ids[0]}%2C{punch_ids[1]}%5D"
            punch_result = self._post('/ecosystem/punchrecord/add', data=punch_param)
            if punch_result and punch_result.get('code') == 0:
                Log(f"  打卡记录上报成功 (punchIds=[{punch_ids[0]},{punch_ids[1]}])")
            else:
                Log(f"  打卡记录上报: {punch_result}")
        else:
            Log("  跳过打卡记录 (无可用打卡点)")

        # 2. 骑行数据
        Log("  查询骑行数据...")
        riding_data = self._post('/ecosystem/trajectoryData/ridingData', data='white=2')
        if riding_data and riding_data.get('code') == 0:
            brand = riding_data['data'].get('brandName', '未知')
            bike = riding_data['data'].get('cyclingName', '未知')
            Log(f"  骑行数据: {brand} {bike}")
        else:
            Log(f"  骑行数据查询: {riding_data}")

        # 3. 打卡点信息
        point_info = self._post('/ecosystem/punchpoint/myInfo')
        if point_info and point_info.get('code') == 0:
            Log(f"  打卡信息 - 收藏:{point_info['data']['collectTotal']} 打卡:{point_info['data']['pointTotal']} 点赞:{point_info['data']['likeTotal']}")

        # 4. 上报设备连接
        self._sleep()
        Log("  上报设备连接...")
        device_result = self._post('/ecosystem/deviceConnect/report', data={
            'province': '河南省',
            'city': self.region_name,
            'location': self.location,
            'deviceModel': 'SOAIY GD36',
            'macAddress': '41:42:F8:68:33:6B',
        })
        if device_result and device_result.get('code') == 0:
            Log("  设备连接上报成功")
        else:
            Log(f"  设备连接上报失败: {device_result}")

        self._sleep()

        # 5. 生成并上传轨迹 (群组对讲格式: 1个文件，时间戳设 1~8 小时前)
        distance = random.randint(1500, 5000)
        estimated_duration_s = int(distance / 8.0)
        # 群组对讲的时间戳比单人骑行更早，随机 1~8 小时前 (不会让脚本等 8 小时)
        time_offset_s = random.randint(3600, 28800)
        pos_content, ride_time_ms, pts_count = self._generate_trajectory(
            lat, lon, distance_m=distance, time_offset_s=time_offset_s
        )
        Log(f"  轨迹: {distance}m, {pts_count}点, 约{estimated_duration_s // 60}分{estimated_duration_s % 60}秒 (时间偏移 {time_offset_s // 3600}h{time_offset_s % 3600 // 60}m前)")

        upload_time_ms = int(time.time() * 1000)
        upload_result = self._upload_group_trajectory(user_id, pos_content, ride_time_ms, upload_time_ms)
        if upload_result and upload_result.get('code') == 200:
            Log("  轨迹上传成功！")
            return True
        else:
            Log(f"  轨迹上传失败: {upload_result}")
            success = False
            return False

    # ---- 签到日历 ----

    def sign_calendar(self, year=None, month=None):
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        result = self._post('/ecosystem/integral/operation/v1/calendar', data={
            'year': str(year),
            'month': str(month),
        })
        if result and result.get('code') == 0:
            signed = [d['date'][-2:] for d in result['data'] if d.get('signStatus') == '2']
            Log(f"  本月已签到 {len(signed)} 天: {', '.join(signed) if signed else '无'}")
            return result['data']
        else:
            Log(f"  查询日历失败: {result}")
            return None

    # ---- 主流程 ----

    def main(self):
        global success

        # 1. 查询积分
        if not self.my_points():
            return False

        # 2. 签到
        info = self.sign_info()
        if info and int(info.get('isSign', 1)) != 1:
            self.sign()
        elif info:
            Log("今日已签到，跳过")

        # 3. 查询任务列表，判断哪些需要执行
        self._sleep()
        tasks = self.task_list()

        # 4. 检测各任务状态
        need_like = True
        # need_group = True  # 群组对讲暂不可用 (需要群内成员/对讲数据)
        need_ride = True
        if tasks:
            for t in tasks.get('dailyTasks', []):
                title = t.get('taskTitle', '')
                if t.get('receiveStatus') == 1:
                    if '点赞' in title:
                        Log("点赞任务已完成，跳过")
                        need_like = False
                    # if '群组对讲' in title:
                    #     Log("群组对讲任务已完成，跳过")
                    #     need_group = False
                    if '单人骑行' in title:
                        Log("单人骑行任务已完成，跳过")
                        need_ride = False

        # 5. 群组对讲 (暂不可用: 需要群内成员/对讲数据)
        # if need_group:
        #     self._sleep()
        #     self.simulate_group_intercom()

        # 6. 点赞任务
        if need_like:
            self._sleep()
            self.do_like_task(count=5)

        # 7. 单人骑行
        if need_ride:
            self._sleep()
            self.simulate_riding()
            # 轨迹上传后等待服务器异步处理完成
            Log("  等待服务器处理轨迹数据...")
            time.sleep(5)

        # 8. 签到日历
        self._sleep()
        self.sign_calendar()

        # 9. 领取积分 (所有任务执行后统一领取)
        self._sleep()
        self.receive_integral()

        # 10. 最终积分
        self.my_points(end=True)

        return True


# ============================================================
# 主入口
# ============================================================

if __name__ == '__main__':
    token = os.environ.get('ONESIGN_VMTDD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_VMTDD_TOKEN 变量")
        print("抓包获取: 抓包工具筛选 eco.trantor.top，复制任意请求 Authorization 头 Bearer 后的 JWT token")
        sys.exit(1)

    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")

    for idx, info in enumerate(tokens):
        RUN(info, idx).main()

    if not success:
        sys.exit(1)