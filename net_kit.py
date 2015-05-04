# coding=utf-8
import zlib
import base64
import socket
import requests
import random
import time
import json
import sys

reload(sys)
sys.setdefaultencoding('utf8')


class HttpHelper():
    """
    基于requests再次封装的http请求对象
    """
    url = ''
    host_url = ''
    num = 0
    requester = None

    def __init__(self):
        pass

    def get_requester(self):
        """
        获取固定会话信息的requester
        在执行若干次后会更新cookie, 一定几率降低被封可能
        """
        if self.num >= 30 or not self.requester:
            self.requester = requests.session()
            self.num = 0

        self.num += 1
        return self.requester

    @staticmethod
    def get_headers():
        """
        每次随机获取header, 一定几率降低被封可能
        """
        user_agent = [
            'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 ' +
            '(KHTML, like Gecko) Chrome/30.0.1599.69 Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.3; Win64; x64) ' +
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36',
            'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 ' +
            '(KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36',
        ]
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'User-Agent': random.choice(user_agent),
        }

    def post(self, url, params=()):
        return self.__request('post', url, params)

    def get(self, url, params=()):
        return self.__request('get', url, params)

    def __request(self, method, url, params=()):

        self.url = url

        start_time = time.time()
        try:
            if method == 'post':
                req = self.get_requester().post(self.url, headers=self.get_headers(), timeout=10, params=params)
            else:
                req = self.get_requester().get(self.url, headers=self.get_headers(), timeout=10, params=params)

        except requests.ConnectionError, e:
            return None, str(e.message), round((time.time() - start_time) * 1000, 2)
        except requests.HTTPError, e:
            return None, str(e.message), round((time.time() - start_time) * 1000, 2)
        except requests.Timeout, e:
            return None, str(e.message), round((time.time() - start_time) * 1000, 2)
        except Exception, e:
            return None, str(e.message), round((time.time() - start_time) * 1000, 2)
        else:
            return req.text, req.status_code, round((time.time() - start_time) * 1000, 2)


class SocketHelper():
    """
    slave与master数据传输对象
    使用特定格式传输
    传输时会压缩数据
    """
    data = {}
    project_name = ''

    def __init_data(self):
        self.data = {
            'project_name': self.project_name,
            'get_urls': 1,
            'urls_parsed': [],
            'urls_add': [],
            'save': [],
        }

    def __init__(self, project_name):
        self.project_name = project_name
        self.__init_data()

    def get_data(self):
        """
        获取master中的新url队列, 并把之前缓存的所有数据推送至master
        :return:
        """
        self.data['urls_add'] = list(set(self.data['urls_add']))  # queue 去重

        start_time = time.time()

        response = self.__request(self.data)
        print round((time.time() - start_time) * 1000, 2), 'ms'
        if response:
            self.__init_data()

        return response

    def put_data(self, urls_parsed=(), urls_add=(), save=()):
        """
        不会真正推送数据, 只先加入缓存属性中, 当执行self.get_data时再一并推送
        :param urls_parsed:
        :param urls_add:
        :param save:
        :return:
        """
        for url in urls_parsed:
            self.data['urls_parsed'].append(url)

        for url in urls_add:
            self.data['urls_add'].append(url)

        if save:
            self.data['save'].append(save)

    @staticmethod
    def __request(data):
        response = None
        try:
            json_string = SocketHelper.socket_client(json.dumps(data))
            response = json.loads(json_string)
        finally:
            return response

    @staticmethod
    def socket_client(content):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 7777))

        send_date = base64.b64encode(zlib.compress(content))  # 压缩编码

        # content前10个字符串用于标识内容长度.
        response_len = (str(len(send_date) + 10) + ' ' * 10)[0:10]
        sock.sendall(response_len + send_date)
        buff_size = 1024
        data = sock.recv(buff_size)

        # content前10个字符串用于标识内容长度.
        data_len = int(data[0:10])
        while len(data) < data_len:
            s = sock.recv(buff_size)
            data += s

        data = zlib.decompress(base64.b64decode(data[10:]))  # 解码解压

        sock.close()

        return data