
import requests
from testbase.testcase import TestCase
from urllib.parse import urlparse, parse_qs

class UpdateAvatarNickTest(TestCase):
    '''验证头像昵称更换是否正常'''

    owner = "Mini_LLM"
    status = TestCase.EnumStatus.Ready
    priority = TestCase.EnumPriority.Normal
    timeout = 5

    def get_headers(self):
        '''获取公共请求头'''
        return {
            "th-session-id": requests.get('http://ubein.cn:82/session_id').json()['session_id'],
            "Content-Type": "application/json"
        }

    def step_get_user_info(self):
        '''获取用户当前头像及昵称信息'''
        self.start_step("Step 1: 获取用户当前头像及昵称信息")
        url = "https://wechat.wecity.qq.com/trpcapi/thuser_info/Get"
        body = {
            "request": {},
            "context": {
                "version": "V 8.13.59",
                "sub-businessid": "THMini",
                "channel": "AAEngZ_b9-g2Na-G2sT6HH4n",
                "scene": "1089",
                "networkType": "wifi"
            }
        }
        response = requests.post(url, json=body, headers=self.get_headers())
        self.log_info(f"Response Body (Get User Info): {response.text[:1000]}")
        response.raise_for_status()
        response_json = response.json()

        # 断言检查
        self.assert_("检查获取用户信息返回码为0", response_json['code'] == 0)
        self.assert_("检查获取用户信息返回消息为'SUCCESS'", response_json['msg'] == 'success')
        
        return response_json['avatar'], response_json['nick']

    def step_set_avatar(self, avatar_rid):
        '''设置用户头像'''
        self.start_step("Step 2: 设置用户头像")
        url = "https://wechat.wecity.qq.com/trpcapi/thuser_info/SetAvatar"
        body = {
            "request": {
                "rid": avatar_rid
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
        self.log_info(f"Response Body (Set Avatar): {response.text[:1000]}")
        response.raise_for_status()
        response_json = response.json()

        # 断言检查
        self.assert_("检查设置头像返回码为0", response_json['code'] == 0)
        self.assert_("检查设置头像返回消息为'SUCCESS'", response_json['msg'] == 'success')
        
        return response_json.get('url')

    def step_set_nick(self, new_nick):
        '''设置用户昵称'''
        self.start_step("Step 3: 设置用户昵称")
        url = "https://wechat.wecity.qq.com/trpcapi/thuser_info/SetNick"
        body = {
            "request": {
                "nick": new_nick
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
        self.log_info(f"Response Body (Set Nick): {response.text[:1000]}")
        response.raise_for_status()
        response_json = response.json()

        # 断言检查
        self.assert_("检查设置昵称返回码为0", response_json['code'] == 0)
        self.assert_("检查设置昵称返回消息为'SUCCESS'", response_json['msg'] == 'success')

    def step_verify_modifications(self, expected_avatar_url, expected_nick):
        '''验证用户头像及昵称的修改'''
        self.start_step("Step 4: 验证用户头像及昵称的修改")
        updated_avatar, updated_nick = self.step_get_user_info()
        self.log_info(f"Updated Avatar: {updated_avatar}, Updated Nick: {updated_nick}")

        updated_avatar_rid = self.extract_rid_from_url(updated_avatar)
        expected_avatar_rid = self.extract_rid_from_url(expected_avatar_url)

        self.assert_("验证头像已更新", updated_avatar_rid == expected_avatar_rid)
        self.assert_("验证昵称已更新", updated_nick == expected_nick)

    def extract_rid_from_url(self, url):
        '''从URL中提取资源ID'''
        query = urlparse(url).query
        q_params = parse_qs(query)
        return q_params.get('rid', [None])[0]

    def run_test(self):
        '''执行测试步骤'''
        original_avatar, original_nick = self.step_get_user_info()
        self.log_info(f"Original Avatar: {original_avatar}, Original Nick: {original_nick}")

        new_avatar_rid = "14ARD121ozzPQeZU8wsc8j2o9xQoIeZ4E4SONbgdJauqt7ThhMS-CXgGrnm0aBKu4y9oVv8"
        new_nick = "情书_"

        expected_avatar_url = self.step_set_avatar(new_avatar_rid)
        self.step_set_nick(new_nick)
        self.step_verify_modifications(expected_avatar_url, new_nick)

if __name__ == '__main__':
    UpdateAvatarNickTest().debug_run()
