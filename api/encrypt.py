# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：encrypt.py
日期：2022年06月17日 15:51
"""
import base64
from Crypto.Cipher import AES


"""
ECB没有偏移量
"""


def pad(text):
    """
    #填充函数，使被加密数据的字节码长度是block_size的整数倍
    """
    count = len(text.encode('utf-8'))
    add = 16 - (count % 16)
    entext = text + (chr(add) * add)
    return entext.encode('utf-8')


def add_to_16(text):
    if len(text.encode('utf-8')) % 16:
        add = 16 - (len(text.encode('utf-8')) % 16)
    else:
        add = 0
    text = text + ('\0' * add)
    return text.encode('utf-8')


# 加密函数
def encrypt(text):
    key = '9999999999999999'.encode('utf-8')
    text = add_to_16(text)
    cryptos = AES.new(key=key, mode=AES.MODE_ECB)
    cipher_text = cryptos.encrypt(text)
    msg = str(base64.b64encode(cipher_text), encoding="utf8")
    return msg


# 解密后，去掉补足的空格用strip() 去掉
def decrypt(text):
    key = '9999999999999999'.encode('utf-8')
    mode = AES.MODE_ECB
    cryptor = AES.new(key, mode)
    res = base64.decodebytes(text.encode("utf-8"))
    plain_text = cryptor.decrypt(res).decode("utf-8").rstrip('\0')
    return plain_text
