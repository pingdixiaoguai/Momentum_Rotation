import time
import requests
import json
import hmac
import hashlib
import base64
import urllib.parse

def send_to_dingtalk(webhook_url, secret, message_title, markdown_text):
    """
    发送Markdown格式的消息到钉钉机器人。
    """
    if not webhook_url or "http" not in webhook_url or not secret:
        print("错误：钉钉Webhook URL或Secret未配置或格式不正确，无法发送消息。")
        return

    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = f'{timestamp}\n{secret}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    url_with_sign = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {"title": message_title, "text": markdown_text}
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url_with_sign, data=json.dumps(payload), headers=headers, timeout=10)
        response_json = response.json()
        if response_json.get("errcode") == 0:
            print("钉钉消息发送成功！")
        else:
            print(f"钉钉消息发送失败：{response_json}")
    except Exception as e:
        print(f"发送钉钉消息时发生网络错误：{e}")