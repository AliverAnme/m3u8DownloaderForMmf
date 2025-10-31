import jwt
import base64
import json
from urllib.parse import urlparse


def extract_and_decode_jwt(url):
    """
    从URL中提取JWT令牌并解码其内容
    
    Args:
        url (str): 包含JWT令牌的URL
        
    Returns:
        dict: 包含JWT头部和载荷信息的字典
    """
    try:
        # 解析URL以获取路径部分
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # 从路径中提取JWT部分（URL通常格式为 /{jwt}/manifest/...）
        parts = path.strip('/').split('/')
        
        # 查找JWT部分（包含多个点的部分）
        jwt_token = None
        for part in parts:
            if part.count('.') == 2:  # JWT通常包含两个点，分为header.payload.signature
                jwt_token = part
                break
        
        if not jwt_token:
            raise ValueError("在URL中未找到JWT令牌")
        
        print(f"提取到的JWT令牌: {jwt_token}")
        
        # 分割JWT的三个部分
        header_part, payload_part, signature_part = jwt_token.split('.')
        
        # 解码头部
        # Base64 URL安全编码可能缺少填充字符，需要添加
        padding_length = 4 - len(header_part) % 4
        if padding_length < 4:  # 避免添加不必要的填充
            header_part += '=' * padding_length
            
        header = json.loads(base64.urlsafe_b64decode(header_part).decode('utf-8'))
        
        # 解码载荷
        padding_length = 4 - len(payload_part) % 4
        if padding_length < 4:
            payload_part += '=' * padding_length
            
        payload = json.loads(base64.urlsafe_b64decode(payload_part).decode('utf-8'))
        
        # 返回解码结果
        result = {
            "header": header,
            "payload": payload,
            "signature": signature_part[:20] + '...'  # 签名部分只显示前20个字符
        }
        
        return result['payload']['sub']
        
    except jwt.PyJWTError as e:
        print(f"JWT处理错误: {e}")
        return None
    except Exception as e:
        print(f"错误: {e}")
        return None


# 测试代码
def main():
    url = "https://videodelivery.net/eyJhbGciOiJSUzI1NiIsImtpZCI6IjBhMTVjYTYwYWRkMGFkNTBmYjMzMjBlN2M5MWI2NTEwIiwidHlwIjoiSldUIn0.eyJzdWIiOiI1ZTYzMTI2NDI1OTFhOWJmNWJlNDBiYTI3NWIzODJiYyIsImtpZCI6IjBhMTVjYTYwYWRkMGFkNTBmYjMzMjBlN2M5MWI2NTEwIiwiZXhwIjoxNzYwOTM1MzE3LCJuYmYiOjE3NjA5MzQ3MTcsImFjY2Vzc1J1bGVzIjpbeyJ0eXBlIjoiYW55IiwiYWN0aW9uIjoiYWxsb3cifV19.WCcSsE1d1nNQXIunR1__U439jE0FHHZTCpNdRla9WPNZJ3XsBwKo14d6QPk4tzQBbh2jOWOkLBNdzAKsekwJrIHP3R7GUYAulX-F9qvn0mhXNOQjOtlwg6ruDiVmsnFhcZZWprG9B7ELLk2SrpBgFornSrAVUZZ0a6D9tCG40zAmZO5AM3e3qqcY8BV8ZbIR4s1XetIDK8ryoK7ijI4eaFi4AeP-TLvwR9Xabq7RUogJii4J8KHy94dNuTfT74WLeqXF3_71zvOa50hhfG-CdGK7PcENuHf7huUQkDrlM1xvjZTeYBEeQ_awQlxVuqV74ppK4QiU5EWdhXrhhpfpww/manifest/video.m3u8"
    result = extract_and_decode_jwt(url)
    
    if result:
        print(f"JWT解码结果: {result}")
        print("5e6312642591a9bf5be40ba275b382bc")


if __name__ == "__main__":
    main()