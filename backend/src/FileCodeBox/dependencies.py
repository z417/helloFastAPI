#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 28/Apr/2023 10:28
 * @LastEditors  : Yuri
 * @LastEditTime : 28/Apr/2023 11:06
 * @FilePath     : /teach/helloFastAPI/backend/src/FileCodeBox/dependencies.py
 * @Description  : file desc
'''
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status


class IPRATELimit:
    def __init__(self, count, minutes):
        self.ips = {}
        self.count = count
        self.minutes = minutes

    def check_ip(self, ip):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if ip in self.ips:
            if self.ips[ip]['count'] >= self.count:
                if self.ips[ip]['time'] + timedelta(minutes=self.minutes) > now:
                    return False
                else:
                    self.ips.pop(ip, None)
        return True

    def add_ip(self, ip):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        ip_info = self.ips.get(ip, {'count': 0, 'time': now})
        ip_info['count'] += 1
        ip_info['time'] = now
        self.ips[ip] = ip_info
        return ip_info['count']

    async def remove_expired_ip(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # 用安全拷贝的列表遍历，绝对防范字典大小在遍历中改变导致的崩溃
        expired_ips = [
            ip for ip, info in self.ips.items()
            if info['time'] + timedelta(minutes=self.minutes) < now
        ]
        for ip in expired_ips:
            self.ips.pop(ip, None)

    def __call__(self, request: Request):
        ip_header = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For')
        ip = ip_header.split(',')[0].strip() if ip_header else (request.client.host if request.client else "127.0.0.1")
        
        if not self.check_ip(ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests, do it later')
        
        # 自动计数，修复只校验不记录的缺陷
        self.add_ip(ip)
        return ip

