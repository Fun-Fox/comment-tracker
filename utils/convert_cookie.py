"""
Cookie 格式转换工具
将字符串格式的 Cookie 转换为 JSON 格式
"""
import json

def convert_cookie_string_to_json(cookie_string: str, domain: str = ".xiaohongshu.com") -> str:
    """
    将字符串格式的 Cookie 转换为 JSON 格式
    
    Args:
        cookie_string: Cookie 字符串，例如 "name1=value1; name2=value2"
        domain: Cookie 域名
        
    Returns:
        JSON 格式的 Cookie 数组
    """
    cookies = []
    
    # 分割每个 cookie
    for item in cookie_string.strip().split(';'):
        item = item.strip()
        if not item:
            continue
            
        # 分割 name 和 value
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/"
            })
    
    return json.dumps(cookies, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 示例：小红书 Cookie 字符串
    xhs_cookie_str = "abRequestId=97362d35-182d-57af-8f59-46c0865899a3; ets=1776420246152; a1=19d9ae5d2cbqqanp9pk2bpjfh1l1hbdkwg5w2rxi450000342150; webId=36fcb0e0d06c410774ca7a916a7899a4; web_session=0400697664e070a893403bbdd03b4b28352442"
    
    print("=== 原始 Cookie 字符串 ===")
    print(xhs_cookie_str[:100] + "...")
    print()
    
    print("=== 转换后的 JSON 格式 ===")
    json_cookies = convert_cookie_string_to_json(xhs_cookie_str)
    print(json_cookies)
    print()
    
    print("=== 使用方法 ===")
    print("1. 复制上面的 JSON 内容")
    print("2. 粘贴到 .env 文件中的 XHS_COOKIE= 后面")
    print("3. 确保 JSON 是一行（去掉换行）")
