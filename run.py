import checkxhsdown
import threading
import sys
import logging
import os
import time
import sqlite3
import socket,json,requests
import requests.packages.urllib3.util.connection as urllib3_cn
import bootcheck

current_path = os.path.dirname(__file__)
conn = sqlite3.connect(os.path.join(
    current_path, 'config.db'), check_same_thread=False)

def allowed_gai_family():
    """
    https://github.com/shazow/urllib3/blob/master/urllib3/util/connection.py
    """
    family = socket.AF_INET
    # if urllib3_cn.HAS_IPV6:
    #     family = socket.AF_INET6 # force ipv6 only if it is available
    return family


urllib3_cn.allowed_gai_family = allowed_gai_family

logging.basicConfig(filename='/var/log/checkxhs.log', format='%(asctime)s-%(levelname)s:%(message)s',
                    level=logging.INFO, filemode='a', datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger()
sys.stderr.write = logger.error
sys.stdout.write = logger.info

logging.info("current_path: %s" % current_path)

# 用户模式
# checkxhsuserdownload = checkxhsdown.CheckXhsUserDown(conn)
# 收藏夹模式
checkxhsfavdownload = checkxhsdown.CheckXhsFavDown(conn)

checkxhsfavdownload.run()



# checkxhsfavdownload.rename()
# checkxhsfavdownload.randomvideo()
# checkxhsfavdownload.facedetection()

