import os

def delete_unwanted_files(directory):
    # 定义要保留的文件名
    files_to_keep = { "testcase.txt","output.csv"}
    
    # 遍历指定目录中的所有文件和目录
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 检查文件是否在保留列表中
            if file not in files_to_keep:
                # 生成文件的完整路径
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)  # 删除文件
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

# 使用示例
directory_path = "datasets"  # 替换为你的文件夹路径
delete_unwanted_files(directory_path)


