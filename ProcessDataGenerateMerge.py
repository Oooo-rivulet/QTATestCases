import ast
import os
import re
import csv
import json
from urllib.parse import urlparse, urlunparse

import openai
import pandas as pd
import requests
from openai import OpenAI
from openai import BadRequestError

data_root = "datasets/"  # 数据集根目录
prompt_root = "prompt/"  # 数据集根目录
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_api_base = "https://api.chatanywhere.tech/v1"
client = OpenAI(api_key=openai_api_key,base_url=openai_api_base)



class Cleaner:
    def __init__(self, input_file, origin_file, cleaned_file, arg="URL_and_R"):
        self.input_file = input_file
        self.origin_file = origin_file
        self.cleaned_file = cleaned_file
        self.arg = arg
        csv.field_size_limit(10 * 1024 * 1024)

    # 清理url中的查询值
    def clean_url(self, url):
        parsed_url = urlparse(url)
        clean_url = urlunparse(parsed_url._replace(query=""))
        return clean_url

    # 判断该该日志的url是否为API接口
    def is_api_url(self, url):
        static_extensions = (
            '.jpg', '.jpeg', '.png', '.svg', '.gif', '.bmp', '.tiff', '.ico',
            '.mp4', '.avi', '.mov', '.wmv',
            '.mp3', '.wav', '.aac', '.ogg',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
            '.html', '.css', '.js',
            '.zip', '.rar', '.tar', '.gz',
            '.xml'
        )

        # 检查 URL 是否以其中任一静态资源扩展名结束
        return not url.endswith(static_extensions)

    # 逐条删除非API URL日志,只保留和业务相关的域名接口请求
    def check_and_filter(self, row):
        url = row['URL']
        if not self.is_api_url(url) or "wechat.wecity.qq.com" not in url:
            return pd.Series([pd.NA] * len(row), index=row.index)  # 返回与行长度相同、全为NA的Series
        return row

    # 清理大于7000的单条日志内容
    def process_column(self, column_data):
        if pd.isna(column_data):
            return column_data
        try:
            data = ast.literal_eval(column_data)
            if isinstance(data, dict):
                data = {k: v for k, v in data.items() if len(str(v)) <= 7000}
                return str(data)
            return column_data
        except (ValueError, SyntaxError):
            return column_data

    # 安全载入json
    def safe_json_loads(self, s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            try:
                return json.loads(s.replace("'", '"'))
            except json.JSONDecodeError:
                return ast.literal_eval(s)

    def process_log(self, row):
        # 解析Request列中的JSON数据
        request_data = self.safe_json_loads(row['Request'])
        if request_data is None:
            print(f"Invalid JSON in Request: {row['Request']}")
            request_data = {}
        # 提取method字段并新增Method列
        row['Method'] = request_data.get('method')
        # 清理Request列，只保留postData里的text
        row['Request'] = request_data.get('postData', {}).get('text')

        # 解析Response列中的JSON数据
        response_data = self.safe_json_loads(row['Response'])
        if response_data is None:
            print(f"Invalid JSON in Response: {row['Response']}")
            response_data = {}
        # 清理Response列，只保留content里的text
        row['Response'] = response_data.get('content', {}).get('text')
        return row

    # 清洗过程
    def process_csv(self):
        df = pd.read_csv(self.input_file)

        # 去除Headers列
        if 'Headers' in df.columns:
            df = df.drop(columns=['Headers'])

        # 去除无关日志
        df = df.apply(self.check_and_filter, axis=1).dropna()
        df['URL'] = df['URL'].apply(self.clean_url)

        # 清理request以及response
        df = df.apply(self.process_log, axis=1)
        if self.arg in ["R", "URL_and_R"]:
            df['Request'] = df['Request'].apply(self.process_column)
            df['Response'] = df['Response'].apply(self.process_column)

        # 添加行号列
        df.insert(0, 'Number', range(1, 1 + len(df)))

        # 保存为原始日志
        df.to_csv(self.origin_file, index=False)
        print(f'处理完毕{self.origin_file}')

        # 去除Number、Started Date列
        if 'Started Date' in df.columns:
            df = df.drop(columns=['Started Date'])
        if 'Number' in df.columns:
            df = df.drop(columns=['Number'])
        df.to_csv(self.cleaned_file, index=False)
        print(f'处理完毕{self.cleaned_file}')


class UserDataProcessor:
    def __init__(self, data_URL, prompt_URL, data_path, txt_path, output_data=None, text_data=None):
        self.data_URL = data_URL
        self.prompt_URL = prompt_URL
        self.data_path = data_path
        self.txt_path = txt_path
        self.output_data = output_data
        self.text_data = text_data

    def chat(self, content=""):
        """
        GPT接口
        :param content: 输入的问题内容，若为空则函数直接返回
        :return: 以 JSON 格式返回服务器的响应
        """
        try:
            chat_response = client.chat.completions.create(
                model="gpt-4o-mini",  # 确保使用正确的模型
                messages=[{"role": "system", "content": "You are an assistant."},
                          {"role": "user", "content": content}]
            )

            # 确保响应和choices存在且非空
            if chat_response and chat_response.choices:
                return chat_response.choices[0].message.content
            else:
                raise ValueError("Received an empty response from the API.")

        except Exception as e:
            print(f"Error during chat completion: {e}")
            return None

    def extract_test_steps(self):
        """
        :param text_content: 
        :return: 全部文本
        """
        with open(self.txt_path, 'r', encoding='utf-8') as file:
            # 读取文件内容
            self.text_data = file.read()
        return self.text_data

    def traverse_json(self, data, prefix=''):
        result = []
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                result.extend(self.traverse_json(value, new_prefix))
        elif isinstance(data, list):
            for index, value in enumerate(data):
                new_prefix = f"{prefix}[{index}]"
                result.extend(self.traverse_json(value, new_prefix))
        else:
            # 如果值是字符串并且包含双引号，则保留双引号；否则保持原样
            value_str = f'"{data}"' if isinstance(data, str) and data.startswith('"') and data.endswith('"') else str(
                data)
            result.append(f'"{prefix}": {value_str}')
        return result

    def strip_values(self,obj):
        if isinstance(obj, dict):
            return {k: self.strip_values(v) for k, v in obj.items() if isinstance(v, dict) or isinstance(v, list)}
        elif isinstance(obj, list):
            return [self.strip_values(item) for item in obj if isinstance(item, dict) or isinstance(item, list)]
        else:
            return None

    def fix_json_string(self,json_str):
        # 修正单引号为双引号
        json_str = re.sub(r"'(.*?)'", r'"\1"', json_str)
        # 修正逗号和冒号的使用
        json_str = re.sub(r':\s*\[', r': [', json_str)
        json_str = re.sub(r',\s*\}', r'}', json_str)
        return json_str

    # 将从API接口获取的数据保存到CSV文件中
    def save_to_csv(self, file_path, url, llm_response):
        fieldnames = ['URL', '接口定义', '请求参数', '回包信息']

        if isinstance(llm_response, dict):
            llm_response = json.dumps(llm_response)

        # 使用正则表达式提取接口定义、请求参数和回包信息
        interface_definition = re.search(r'接口定义：(.*?)请求参数：', llm_response, re.DOTALL)
        request_params = re.search(r'请求参数：(.*?)回包信息：', llm_response, re.DOTALL)
        response_info = re.search(r'回包信息：(.*)', llm_response, re.DOTALL)

        # 如果匹配到内容，则获取对应的组
        interface_definition = interface_definition.group(1).strip() if interface_definition else ''
        request_params = request_params.group(1).strip() if request_params else ''
        response_info = response_info.group(1).strip() if response_info else ''

        # 检查文件是否存在
        file_exists = os.path.isfile(file_path)

        with open(file_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # 仅在文件不存在时写入表头
            if not file_exists:
                writer.writeheader()

            # 确保字段不为空再写入
            if interface_definition or request_params or response_info:
                writer.writerow({
                    'URL': url,
                    '接口定义': interface_definition,
                    '请求参数': request_params,
                    '回包信息': response_info
                })

    def step_1(self, grouped, API_file):
        """
        :param grouped: 一个包含URL和与之相关联的DataFrame group_df 的迭代器。
        :param API_file: 用于保存CSV文件的路径
        """
        for URL, group_df in grouped:
            request_data = group_df['Request'].tolist()
            response_data = group_df['Response'].tolist()

            prompt = f"""
            #接口信息#:```
            URL：{URL}
            request：{self.traverse_json(request_data)}
            response：{self.traverse_json(response_data)}
            ```
            #规则#：
            1.充分理解并分析'接口信息'中的内容；
            2.分析出接口的定义，使用简单的一句话进行概括描述；
            3.分析'request'中的内容，理解里面的请求体字段含义；
            4.分析'response'中的内容，理解里面响应体数据的字段含义；
            5.用简洁的语句返回；
            7.严格按照接口定义，请求参数,回包信息的顺序返回，格式内的请求参数，回包信息严格按照返回示例格式
    
            #返回内容#：
            严格按照以下格式返回：
            接口定义：用简洁的一句话描述接口的功能
            请求参数：理解请求体中的关键字段含义，用简洁的语句概括请求字段，返回格式为“字段名（字段含义）”，不返回字段值
            回包信息：忽略字段值，理解响应体中的关键字段含义，并用简洁的语句概括回包内容，返回格式为“字段名（字段含义）”
    
            #返回示例#
            接口定义：获取特定健康场景下的测评列表
            请求参数：scene（场景标识），version（版本号），sub-businessid（子业务ID），channel（渠道标识），networkType（网络类型）
            回包信息：code（请求状态码），msg（状态信息），entryList（测评列表，包括测评按钮文本、花费、可用性、测评ID、完成状态、历史ID、图标链接、参与人数、跳转链接、测评题目数量、副标题、标题）       
            """
            try:
                llm_response = self.chat(prompt)
                if llm_response is None:
                    print(f"Error: No response received for URL: {URL}")
                    continue
                print(llm_response)
                self.save_to_csv(API_file, URL, llm_response)
            except BadRequestError as e:
                if "context_length_exceeded" in str(e):
                    print(f"Context length exceeded for URL: {URL}. Attempting to clean data and retry.")
                    # 使用清理逻辑来处理请求和响应数据
                    # 解析并清理
                    request_list = []
                    for item in request_data:
                        # 使用修正函数处理原始JSON字符串
                        fixed_json_str = self.fix_json_string(item)
                        print(fixed_json_str)
                        # 尝试解析JSON字符串
                        try:
                            data = json.loads(fixed_json_str)
                            # print("JSON解析成功：", data)
                            structured_data = self.strip_values(data)
                            # 将结构化的JSON数据转换回字符串形式
                            structured_json = json.dumps(structured_data, indent=2)
                            request_list.append(structured_json)
                        except json.JSONDecodeError as e:
                            pass
                    # print(f"request_list: {request_list}")
                    response_list = []
                    for item in response_data:
                        # 使用修正函数处理原始JSON字符串
                        fixed_json_str = self.fix_json_string(item)
                        print(fixed_json_str)
                        # 尝试解析JSON字符串
                        try:
                            data = json.loads(fixed_json_str)
                            # print("JSON解析成功：", data)
                            structured_data = self.strip_values(data)
                            # 将结构化的JSON数据转换回字符串形式
                            structured_json = json.dumps(structured_data, indent=2)
                            response_list.append(structured_json)
                        except json.JSONDecodeError as e:
                            pass
                    # 重新构建 prompt 并再次调用 self.chat
                    prompt = f"""
                    #接口信息#:```
                    URL：{URL}
                    request：{request_list}
                    response：{response_list}
                    ```
                    #规则#：
                    1.充分理解并分析'接口信息'中的内容；
                    2.分析出接口的定义，使用简单的一句话进行概括描述；
                    3.分析'request'中的内容，理解里面的请求体字段含义；
                    4.分析'response'中的内容，理解里面响应体数据的字段含义；
                    5.用简洁的语句返回；
                    7.严格按照接口定义，请求参数,回包信息的顺序返回，格式内的请求参数，回包信息严格按照返回示例格式

                    #返回内容#：
                    严格按照以下格式返回：
                    接口定义：用简洁的一句话描述接口的功能
                    请求参数：理解请求体中的关键字段含义，用简洁的语句概括请求字段，返回格式为“字段名（字段含义）”，不返回字段值
                    回包信息：忽略字段值，理解响应体中的关键字段含义，并用简洁的语句概括回包内容，返回格式为“字段名（字段含义）”

                    #返回示例#
                    接口定义：获取特定健康场景下的测评列表
                    请求参数：scene（场景标识），version（版本号），sub-businessid（子业务ID），channel（渠道标识），networkType（网络类型）
                    回包信息：code（请求状态码），msg（状态信息），entryList（测评列表，包括测评按钮文本、花费、可用性、测评ID、完成状态、历史ID、图标链接、参与人数、跳转链接、测评题目数量、副标题、标题）       
                    """
                    llm_response = self.chat(prompt)
                    if llm_response is None:
                        print(f"Error: No response received for URL: {URL}")
                        continue
                    print(llm_response)
                    self.save_to_csv(API_file, URL, llm_response)
            except Exception as e:
                print(f"Error during processing URL {URL}: {str(e)}")


    def write_large_csv(self, file_path, data_list):
        """
        将处理过的数据写入大型CSV文件。

        :param file_path: 要写入的CSV文件的路径
        :param data_list: 一个包含CsvData对象的列表
        """
        headers = ['URL', '请求参数', '回包信息', '用例步骤']

        with open(file_path, 'w', encoding='utf-8-sig', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()

            for csv_data in data_list:
                writer.writerow({
                    'URL': csv_data['URL'],
                    '请求参数': csv_data['请求参数'],
                    '回包信息': csv_data['回包信息'],
                    '用例步骤': csv_data['用例步骤']
                })

    def split_llm(self, response):
        """
        :param response: 大模型返回的结果
        :return: 列表形式的统一的结果
        """
        # 正则表达式匹配用例步骤、URL和接口定义
        pattern = r"用例步骤:\s*(\d+\.\S+?)\s*\|\s*URL:(https?://[^|\s]+)\s*\|\s*接口定义:(.+)"
        # 使用正则表达式查找所有匹配项
        matches = re.findall(pattern, response)
        new_dicts = []
        entry = {
            "用例步骤": '无',
            "URL": None,
            "接口定义": None
        }
        # 打印结果
        for match in matches:
            step, url, definition = match
            entry = {
                "用例步骤": step,
                "URL": url,
                "接口定义": definition
            }
            # print(entry)
            if entry['接口定义'] != '无':
                new_dicts.append(entry)
        print(new_dicts)
        return new_dicts

    def to_find_line(self, read_path, new_dicts):
        """
        :param new_dicts: 列表嵌套字典
        :return: 原本数据中找到的对应行
        """
        found_items = []
        with open(read_path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            # line_number = 0  # 记录当前行号
            for row in csv_reader:
                # line_number += 1
                # 检查当前行是否包含列表中字典的URL
                for d in new_dicts:
                    if d['URL'] in row:
                        found_items.append(row)

                        print("找到匹配项: {}".format(row))
                        break
        print(f"found_items:{found_items}")
        return found_items

    def save_csv(self, found_items, new_dicts):
        """
        :param found_items:原本数据中找到的对应行
        :param new_dicts:列表嵌套字典
        :return: 数据存储用的字典
        """
        use_dicts = []
        for item in found_items:
            # 假设每个item是一个列表，包含csv行数、URL、接口定义、请求参数和回包信息
            URL = item[0]  # URL
            definition = item[1]  # 接口定义
            request = item[2]  # 请求参数
            response = item[3]  # 回包信息
            step_name = []
            my_flag = 0
            for d in new_dicts:
                if d['URL'] == URL:
                    my_flag = 1
                    step_name.append(d['用例步骤'])
            if my_flag:
                entry = {
                    'URL': URL,
                    '请求参数': request,
                    '回包信息': response,
                    '用例步骤': step_name
                }
                use_dicts.append(entry)
        return use_dicts

    def step_2(self, read_path, save_path, no_api_path):
        """
        :param read_path: 读入的数据
        :param txt_path: 用例步骤文本
        :param save_path: 存储的接口集文件
        """
        my_data = pd.read_csv(read_path, encoding='utf-8')
        data_URL = my_data.loc[:, 'URL'].tolist()
        data_sub = my_data.loc[:, '接口定义'].tolist()
        my_text = self.text_data
        # 构建输入内容
        my_content = f"""
                # 用例数据：
                data: {{
                  "data_sub(接口定义)": {data_sub},
                  "data_URL": {data_URL}
                }}

                #文本用例：
                {my_text}

                # 规则：
                1. 阅读并理解文本内容，找到与'data'中意思相近的描述。
                2. 选择'data_URL'中对应的接口，确保它与用例步骤意思相近。
                3. 确保每步用例步骤对应的接口是唯一的，且不是重复的。
                4. 请特别注意！！验证预期结果可能也需要调用对应的接口
                5. 每步测试用例对应一行结果。
                6. 请严格按照返回内容格式以及示例返回你的回答


                # 返回内容格式：
                按照以下格式返回每个用例步骤的结果，每条用例步骤返回一行：
                '用例步骤:具体步骤描述 | URL:接口URL | 接口定义:接口定义 '

                # 示例:
                用例步骤:1.查看微信小程序 | URL:https://wechat.wecity.qq.com/trpcapi/THCfgServer/getCfg | 接口定义:获取配置信息
        
                """

        response = self.chat(content=my_content)
        print(f"response: {response}")
        new_dicts = self.split_llm(response)
        found_items = self.to_find_line(read_path, new_dicts)
        use_dicts = self.save_csv(found_items, new_dicts)
        if use_dicts:
            self.write_large_csv(save_path, use_dicts)
            return True
        else:
            output_line = "no api use!"
            print(output_line)
            with open(no_api_path, 'w', encoding='utf-8') as file:
                file.write(output_line)
            return False


    def main_workflow(self):
        input_file = f'{self.data_URL}/output.csv'
        origin_file = f'{self.data_URL}/origin.csv'
        cleaned_file = f'{self.data_URL}/cleaned.csv'
        API_file = f'{self.data_URL}/describe.csv'
        cleaner = Cleaner(input_file, origin_file, cleaned_file, arg="URL_and_R")
        cleaner.process_csv()
        df_cleaned = pd.read_csv(cleaned_file)
        grouped = df_cleaned.groupby('URL')
        self.step_1(grouped, API_file)
        # #step2
        self.extract_test_steps()
        read_path = f"{self.data_URL}/describe.csv"
        save_path = f"{self.data_URL}/merged.csv"
        no_api_path = f"{self.data_URL}/no_api_txt"
        self.step_2(read_path, save_path, no_api_path)
       


# 使用类
if __name__ == '__main__':
    for i in range(1,4):
        data_URL = data_root + str(i)
        prompt_URL = prompt_root + str(i)
        data_path = f'{data_URL}/output.csv'
        txt_path = f"{data_URL}/testcase.txt"
        # user_data = "这里是用户数据"
        processor = UserDataProcessor(data_URL, prompt_URL, data_path, txt_path)
        processor.main_workflow()
