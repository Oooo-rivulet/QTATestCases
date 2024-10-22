
import requests
from testbase.testcase import TestCase

class HealthEvaluationTest(TestCase):
    '''健康测评接口测试'''

    owner = "Mini_LLM"
    status = TestCase.EnumStatus.Ready
    priority = TestCase.EnumPriority.Normal
    timeout = 10

    def get_headers(self):
        '''获取公共请求头'''
        return {
            "th-session-id": requests.get('http://ubein.cn:82/session_id').json()['session_id'],
            "Content-Type": "application/json"
        }

    def step_get_user_info(self):
        '''获取用户信息'''
        self.start_step("获取用户信息")
        url = "https://wechat.wecity.qq.com/trpcapi/thuser_info/Get"
        response = requests.post(url, json={"request": {}, "context": {
            "version": "V 8.13.59",
            "sub-businessid": "THMini",
            "channel": "AAEngZ_b9-g2Na-G2sT6HH4n",
            "scene": "1089",
            "networkType": "wifi"
        }},
        headers=self.get_headers())
        
        response.raise_for_status()
        self.log_info(f"Response Body for step_get_user_info: {response.text[:1000]}")
        response_json = response.json()
        self.assert_("检查返回码是否为0", response_json['code'] == 0)
        return response_json.get('th-request-id')

    def step_get_recommendation(self, request_id):
        '''获取推荐测评信息'''
        self.start_step("滑动页面，找到“建议测一测”模块")
        url = "https://wechat.wecity.qq.com/trpcapi/Evaluation/getEvaluationByScene"
        response = requests.post(url, json={"request": {"req": {"scene": "healthtab"}}, "context": {
            "version": "V 8.13.59",
            "sub-businessid": "THMini",
            "channel": "AAEngZ_b9-g2Na-G2sT6HH4n",
            "scene": "1089",
            "networkType": "wifi"
        }},
        headers=self.get_headers())
        
        response.raise_for_status()
        self.log_info(f"Response Body for step_get_recommendation: {response.text[:1000]}")
        response_json = response.json()
        self.assert_("检查返回码是否为0", response_json['code'] == 0)
        self.assert_("检查是否获取到测评列表", len(response_json['rsp']['entryList']) > 0)
        return request_id

    def step_enter_more_evaluations(self, request_id):
        '''进入更多健康测评'''
        self.start_step("点击“更多健康测评”进入")
        url = "https://wechat.wecity.qq.com/trpcapi/BaseQuiz/getFlowByCategory"
        response = requests.post(url, json={"request": {"req": {"bizId": "examination", "categoryId": "v2"}}, "context": {
            "version": "V 8.13.59",
            "sub-businessid": "THMini",
            "channel": "AAEngZ_b9-g2Na-G2sT6HH4n",
            "scene": "1089",
            "networkType": "wifi"
        }},
        headers=self.get_headers())
        
        response.raise_for_status()
        self.log_info(f"Response Body for step_enter_more_evaluations: {response.text[:1000]}")
        response_json = response.json()
        self.assert_("检查返回码是否为0", response_json['code'] == 0)
        return request_id

    def step_get_questions(self):
        '''获取问题列表并提交答案'''
        self.start_step("在“健康测一测”页面中，找到“健康测评”卡片并完成答题")
        url = "https://wechat.wecity.qq.com/trpcapi/DailyQA/getQuestion"
        response = requests.post(url, json={"request": {"req": {}}, "context": {
            "version": "V 8.13.59",
            "sub-businessid": "THMini",
            "channel": "AAEngZ_b9-g2Na-G2sT6HH4n",
            "scene": "1089",
            "networkType": "wifi"
        }},
        headers=self.get_headers())

        response.raise_for_status()
        self.log_info(f"Response Body for step_get_questions: {response.text[:1000]}")
        response_json = response.json()
        self.assert_("检查返回码是否为0", response_json['code'] == 0)
        self.assert_("检查返回是否成功", response_json['msg'] == 'success')
        # Ensure we're checking in the correct response section for 'question'
        self.assert_("检查是否获取到问题", 'question' in response_json['rsp'])
    
    def run_test(self):
        '''执行测试步骤'''
        request_id = self.step_get_user_info()
        self.step_get_recommendation(request_id)
        self.step_enter_more_evaluations(request_id)
        self.step_get_questions()

if __name__ == '__main__':
    HealthEvaluationTest().debug_run()
