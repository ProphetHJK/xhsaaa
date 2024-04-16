import requests
import json
import time
import logging
import base64
from re import search, I
import copy
import regex
import os
from requests.adapters import HTTPAdapter


class CheckDown(object):
    def __init__(self, conn):
        self.conn = conn
        self.config = {}
        self.firstrun = 1
        self.videodownlist = []
        self.haschecklist = []
        self.newnum = 0
        self.errorpushflag = 1
        self.conncursor = self.conn.cursor()
        cursor = self.conncursor.execute("SELECT key,value from config")
        for row in cursor:
            key = row[0]
            value = row[1]
            self.config[key] = value
        self.proxy = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }

        self.session = requests.Session()
        self.session.mount('http://', HTTPAdapter(max_retries=2))
        self.session.mount('https://', HTTPAdapter(max_retries=2))

    def check(self):
        self.newnum = 0
        self.videodownlist.clear()

    def download(self):
        logging.info('start download')

    def run(self):
        try:
            self.check()
            if len(self.videodownlist) > 0:
                self.download()
            self.firstrun = 0
        except Exception as ex:
            logging.info(ex)
            if self.errorpushflag == 1:
                ret4 = self.send_to_wecom("[ERROR]something error,check log",
                                            self.config['wechat_corpid'], self.config['wechat_agentid1'], self.config['wechat_secret1'])
                self.errorpushflag = 0
        logging.info('执行结束')

    def send_to_wecom(self, text, wecom_cid, wecom_aid, wecom_secret, wecom_touid='@all'):
        wecom_touid = self.config['wechat_userid']
        get_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wecom_cid}&corpsecret={wecom_secret}"
        response = self.session.get(get_token_url).content
        access_token = json.loads(response).get('access_token')
        if access_token and len(access_token) > 0:
            send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
            data = {
                "touser": wecom_touid,
                "agentid": wecom_aid,
                "msgtype": "text",
                "text": {
                    "content": text
                },
                "duplicate_check_interval": 600
            }
            response = self.session.post(
                send_msg_url, data=json.dumps(data)).content
            return response
        else:
            return False

    def send_to_wecom_image(self, base64_content, wecom_cid, wecom_aid, wecom_secret, wecom_touid='@all'):
        wecom_touid = self.config['wechat_userid']
        get_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wecom_cid}&corpsecret={wecom_secret}"
        response = self.session.get(get_token_url, timeout=5).content
        access_token = json.loads(response).get('access_token')
        if access_token and len(access_token) > 0:
            upload_url = f'https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image'
            upload_response = self.session.post(upload_url, files={
                "picture": base64.b64decode(base64_content)
            }).json()
            if "media_id" in upload_response:
                media_id = upload_response['media_id']
            else:
                return False

            send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
            data = {
                "touser": wecom_touid,
                "agentid": wecom_aid,
                "msgtype": "image",
                "image": {
                    "media_id": media_id
                },
                "duplicate_check_interval": 600
            }
            response = self.session.post(
                send_msg_url, data=json.dumps(data)).content
            return response
        else:
            return False

    def send_to_wecom_image_url(self, image_url, wecom_cid, wecom_aid, wecom_secret, wecom_touid='@all'):
        wecom_touid = self.config['wechat_userid']
        get_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wecom_cid}&corpsecret={wecom_secret}"
        response = self.session.get(get_token_url, timeout=5).content
        access_token = json.loads(response).get('access_token')
        if access_token and len(access_token) > 0:
            upload_url = f'https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image'
            upload_response = self.session.post(upload_url, files={
                "picture": self.session.get(image_url, timeout=5).content
            }).json()
            if "media_id" in upload_response:
                media_id = upload_response['media_id']
            else:
                return False

            send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
            data = {
                "touser": wecom_touid,
                "agentid": wecom_aid,
                "msgtype": "image",
                "image": {
                    "media_id": media_id
                },
                "duplicate_check_interval": 600
            }
            response = self.session.post(
                send_msg_url, data=json.dumps(data)).content
            return response
        else:
            return False

    def send_to_wecom_markdown(self, text, wecom_cid, wecom_aid, wecom_secret, wecom_touid='@all'):
        wecom_touid = self.config['wechat_userid']
        get_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wecom_cid}&corpsecret={wecom_secret}"
        response = self.session.get(get_token_url, timeout=5).content
        access_token = json.loads(response).get('access_token')
        if access_token and len(access_token) > 0:
            send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
            data = {
                "touser": wecom_touid,
                "agentid": wecom_aid,
                "msgtype": "markdown",
                "markdown": {
                    "content": text
                },
                "duplicate_check_interval": 600
            }
            response = self.session.post(
                send_msg_url, data=json.dumps(data)).content
            return response
        else:
            return False

    def send_to_wecom_news(self, news_title, news_desc, news_url, news_pic, wecom_cid, wecom_aid, wecom_secret, wecom_touid='@all'):
        wecom_touid = self.config['wechat_userid']
        get_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wecom_cid}&corpsecret={wecom_secret}"
        response = self.session.get(get_token_url, timeout=5).content
        access_token = json.loads(response).get('access_token')
        if access_token and len(access_token) > 0:
            send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
            data = {
                "touser": wecom_touid,
                "agentid": wecom_aid,
                "msgtype": "news",
                "news": {
                    "articles": [
                        {
                            "title": news_title,
                            "description": news_desc,
                            "url": news_url,
                            "picurl": news_pic,
                        }
                    ]
                },
                "duplicate_check_interval": 600
            }
            response = self.session.post(
                send_msg_url, data=json.dumps(data)).content
            return response
        else:
            return False
    def filtern(self, filen: str):
        "对文件名进行去除不应该字符"
        filen = str(filen)
        re = regex.search(r'[^[:print:]]', filen)
        while re is not None:
            filen = filen.replace(re.group(), '_')
            re = regex.search(r'[^[:print:]]', filen)
        filen = filen.replace('/', '_')
        filen = filen.replace('\\', '_')
        filen = filen.replace(':', '_')
        filen = filen.replace('*', '_')
        filen = filen.replace('?', '_')
        filen = filen.replace('"', '_')
        filen = filen.replace('<', '_')
        filen = filen.replace('>', '_')
        filen = filen.replace('|', '_')
        filen = filen.replace('$', '_')
        filen = filen.replace('`', '_')
        filen = filen.replace('\t', '_')
        while len(filen) > 0 and filen[0] == ' ':
            filen = filen[1:]
        return filen
                
