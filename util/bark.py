import base64
import json
import logging
import urllib.parse, urllib.request
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

logger = logging.getLogger(__name__)


def send_message(title, content):
    send_crypt_message(title, content)


def send_message_plaint(title, content):
    try:
        url = f"https://api.day.app/bYaNHYbrMk9SvyeRsK5y9/{urllib.parse.quote_plus(title)}/{urllib.parse.quote_plus(content)}"
        rsp = urllib.request.urlopen(url)
        data = rsp.read().decode()
        logger.info(f"title:{title} content:{content} url:{url} rsp:{data}")
    except:
        logger.exception(f"title:{title} content:{content}")


def send_crypt_message(title, content):
    body = {"title": title, "body": content}
    bodystr = json.dumps(body)
    padding_body = pad(bodystr.encode(), AES.block_size, style='pkcs7')

    key = b'm34hhBVvWYQ3cQNE'
    iv = b'a7hjabZ3X9qLJU7x'
    aes = AES.new(key, AES.MODE_CBC, iv)
    encrypted_aes = aes.encrypt(padding_body)
    encrypted_b64 = base64.b64encode(encrypted_aes).decode()

    try:
        url = f"https://api.day.app/bYaNHYbrMk9SvyeRsK5y9"
        req = urllib.request.Request(url=url, method="POST")
        req_data = f"ciphertext={urllib.parse.quote_plus(encrypted_b64)}".encode()
        rsp = urllib.request.urlopen(req, data=req_data)
        data = rsp.read().decode()
    except:
        logger.exception(f"title:{title} content:{content}")
