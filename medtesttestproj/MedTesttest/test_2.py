
import requests
from testbase.testcase import TestCase

class HotwordSearchTest(TestCase):
    '''验证热词搜索是否正常'''

    owner = "Mini_LLM"
    status = TestCase.EnumStatus.Ready
    priority = TestCase.EnumPriority.Normal
    timeout = 10

    def get_headers(self):
        '''获取公共请求头'''
        session_id_response = requests.get('http://ubein.cn:82/session_id')
        self.log_info(f"Session Id Response: {session_id_response.text}")
        session_id = session_id_response.json()['session_id']

        return {
            "th-session-id": session_id,
            "Content-Type": "application/json"
        }

    def step_get_hot_queries(self):
        '''1.进入腾讯健康小程序
        2.点击页面顶部的“搜索”，进入搜索页'''
        url = "https://wechat.wecity.qq.com/trpcapi/trpc-tencent-health-search/GetHotQuery"
        body = {
            "request": {
                "channelId": 730,
                "offset": 0,
                "count": 2,
                "city_code": "440300",
                "city": "深圳"
            },
            "context": {
                "version": "V 8.13.59",
                "sub-businessid": "THMini",
                "channel": "AAEngZ_b9-g2Na-G2sT6HH4n",
                "scene": "1089",
                "networkType": "wifi"
            }
        }
        response = requests.post(url, json=body, headers=self.get_headers())
        self.log_info(f"Response Body from GetHotQuery: {response.text[:1000]}")
        response.raise_for_status()
        response_json = response.json()

        # 断言检查
        self.assert_("检查返回码是否为0", response_json['code'] == 0)
        self.assert_("检查消息是否为'success'", response_json['msg'] == 'success')

        # 提取热门搜索词
        hot_queries = [query['query'] for module in response_json["modules"] for query in module["queries"] if query["is_enable"]]
        self.log_info(f"Extracted Hot Queries: {hot_queries}")
        self.assert_("检查是否有可用的热门搜索词", len(hot_queries) > 0)
        return hot_queries

    def step_search_with_hotword(self, hotword):
        '''3.在热门搜索中，点击任意搜索热词进入'''
        url = "https://wechat.wecity.qq.com/trpcapi/trpc-tencent-health-search/GetHomeMixData"
        body = {
            "request": {
                "offset": 0,
                "count": 1,
                "type": 4,
                "grouping_key": hotword
            },
            "context": {
                "version": "V 8.13.59",
                "sub-businessid": "THMini",
                "channel": "AAEngZ_b9-g2Na-G2sT6HH4n",
                "scene": "1089",
                "networkType": "wifi"
            }
        }
        response = requests.post(url, json=body, headers=self.get_headers())
        self.log_info(f"Response Body from GetHomeMixData with hotword '{hotword}': {response.text[:1000]}")
        response.raise_for_status()
        response_json = response.json()

        # 断言检查
        self.assert_("检查返回码是否为0", response_json['code'] == 0)
        self.assert_("检查消息是否为'success'", response_json['msg'] == 'success')
        
        # 验证搜索结果是否包含预期内容
        self.assert_("检查是否有搜索结果返回", 'list' in response_json and len(response_json['list']) > 0)

    def test_search_hotword(self):
        hot_queries = self.step_get_hot_queries()
        # 选择一个热门搜索词进行搜索
        if hot_queries:
            self.step_search_with_hotword(hot_queries[0])

    def run_test(self):
        '''执行测试步骤'''
        self.test_search_hotword()

if __name__ == '__main__':
    HotwordSearchTest().debug_run()
