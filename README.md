## 用于生成接口测试用例的`datasets` 目录结构
datasets/
│
├── 1/
│   ├── output.csv       # 原始日志文件
│   └── testcase.txt     # 测试用例文本
│
├── 2/
│   └── (类似于1/目录的结构)
│
...

## 生成测试用例说明
1.先运行`ProcessDataGenerateMerge.py`      进行数据清理，生成全量接口描述，以及从众多接口中找到生成测试用例所需接口集
#### 运行`ProcessDataGenerateMerge.py`进行数据清理，生成全量接口描述，以及从众多接口中找到生成测试用例所需接口集后的`datasets` 目录的结构视图如下
datasets/
│
├── 1/
│   ├── cleaned.csv      # 清理后的数据
│   ├── describe.csv     # 全量接口描述
│   ├── merged.csv       # 找到的生成接口测试用例所需日志集
│   ├── origin.csv       # 初步进行清理后的原始日志文件
│   ├── output.csv       # 原始日志文件
│   └── testcase.txt     # 测试用例文本
│
├── 2/
│   └── (类似于1/目录的结构)
|
|
...
2.然后运行`GenerateByreActQTA.py`          根据ProcessDataGenerateMerge.py提供的接口集通过 reactAgent 生成接口测试用例
#### 生成的QTA测试用例存放路径的项目目录结构：
medtesttestproj/
│
├── MedTestlib/
│
├── MedTesttest/  <---生成测试用例存放在这个文件夹下
│   ├── __pycache__/
│   ├── __init__.py
│   ├── test_1.py
│   ├── test_2.py
│   ├── ......
│   
│
├── .project
├── .pydevproject
├── manage.py
└── settings.py


## 运行已生成的测试用例
cd .\medtesttestproj\
python manage.py runtest MedTesttest