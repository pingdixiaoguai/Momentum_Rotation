import time
import requests
import json
import hmac
import hashlib
import base64
import urllib.parse
# 引入日志模块
from utils import logger, error_logger


def send_to_dingtalk(webhook_url, secret, title, text_content, is_at_all=False):
    """
    一个通用的函数，可以发送Markdown或纯文本消息。
    """
    if not webhook_url or "http" not in webhook_url or not secret:
        error_logger.error("钉钉Webhook URL或Secret未配置或格式不正确，无法发送消息。")
        return

    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = f'{timestamp}\n{secret}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    url_with_sign = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    if is_at_all:
        payload = {"msgtype": "text", "text": {"content": text_content}, "at": {"isAtAll": True}}
    else:
        payload = {"msgtype": "markdown", "markdown": {"title": title, "text": text_content}}

    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url_with_sign, data=json.dumps(payload), headers=headers, timeout=10)
        response_json = response.json()
        if response_json.get("errcode") == 0:
            logger.info("钉钉消息发送成功！")
        else:
            error_logger.error(f"钉钉消息发送失败：{response_json}")
    except Exception as e:
        error_logger.error(f"发送钉钉消息时发生网络错误：{e}", exc_info=True)


def send_at_all_nudge(webhook_url, secret):
    """
    发送一条简单的文本消息，只为了 @所有人。
    """
    logger.info("正在发送 @所有人 提醒...")
    nudge_text = "【策略信号】已发送。"

    send_to_dingtalk(
        webhook_url,
        secret,
        title="策略提醒",
        text_content=nudge_text,
        is_at_all=True
    )