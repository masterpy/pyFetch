# coding=utf-8
import helper
import time
from functions import echo_err, get_urls_form_html, format_and_filter_urls
from helper import S
from helper import Slave


class Spider(Slave):
    """
    slave抓取逻辑
    """
    handle_method = None
    pre_url_queue = []
    http_helper = None
    current_url = ''  # 当前url

    def __init__(self, project_name):
        Slave.__init__(self, project_name)
        self.http_helper = helper.HttpHelper()

    def run(self, func):
        """
        :param func:
        :return:
        """
        self.handle_method = func

        while True:
            # gevent.sleep(15)
            # todo 需要些速度控制方法. gevent.sleep
            # todo 需要判断header, 避免下载文件
            self.current_url = self.__get_queue_url()
            print self.current_url
            if not self.current_url:
                continue
            self.put_data(urls_parsed=[self.current_url, ])
            crawl_result = self.http_helper.get(self.current_url)
            if crawl_result[1] not in (200, 201):
                echo_err(
                    'URL: ' + self.current_url + ' 获取失败 HTTP code: ' + str(crawl_result[1]) + ' Runtime: ' + str(
                        crawl_result[2]) + 'ms')
                continue

            # 如果抓取自定义函数存在dict返回值则将dict推送至服务器
            parse_result = self.handle_method(
                S(self, crawl_result[0], get_urls_form_html(self.current_url, crawl_result[0])))
            if not isinstance(parse_result, dict):
                continue

            if 'url' not in parse_result:
                parse_result['url'] = self.current_url
            if 'runtime' not in parse_result:
                parse_result['runtime'] = crawl_result[2]

            self.put_data(save=parse_result)

    def crawl(self, url=''):
        """
        仅加入远程待抓取队列
        self.run()会循环的从本地队列中获取url进行实际抓取
        :param string url:
        :return:
        """
        self.put_data(urls_add=(format_and_filter_urls(self.current_url, url),))

    def __get_queue_url(self):
        """
        每次从本地队列返回一条将要抓取的url
        如果本地队列为空则去远程获取, 当远程获取失败会sleep数秒后重试直到成功
        远程获取的过程如果失败会因为等待重试的sleep而阻塞
        :return:string url|None
        """
        while not self.pre_url_queue:
            response = self.get_data()
            if not response:
                echo_err('远程响应异常, 60秒后重试')
                time.sleep(60)
                continue

            if 'urls' not in response or not response['urls']:
                echo_err('无法从远程获取url队列, 10秒后重试 ' + response['msg'] or '')
                time.sleep(10)
                continue

            self.pre_url_queue += response['urls']

        return self.pre_url_queue.pop(0)  # 出栈首位