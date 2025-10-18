"""
加密工具模块
"""

import hashlib
import hmac
import base64
import time
import os
from typing import Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generate_signature(data: Dict[str, Any], secret_key: str) -> str:
    """生成请求签名"""
    
    # 对参数进行排序
    sorted_params = sorted(data.items())
    
    # 构建签名字符串
    sign_string = "&".join([f"{k}={v}" for k, v in sorted_params])
    sign_string += f"&key={secret_key}"
    
    # 生成MD5签名
    signature = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    return signature.upper()


def generate_timestamp() -> int:
    """生成时间戳"""
    return int(time.time() * 1000)


def encode_base64(data: str) -> str:
    """Base64编码"""
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def decode_base64(data: str) -> str:
    """Base64解码"""
    return base64.b64decode(data.encode('utf-8')).decode('utf-8')


def generate_hmac_sha256(data: str, key: str) -> str:
    """生成HMAC-SHA256签名"""
    signature = hmac.new(
        key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def _get_encryption_key() -> bytes:
    """获取加密密钥"""
    # 使用固定的盐值和密码生成密钥
    # 在实际生产环境中，应该使用更安全的密钥管理方式
    password = b"xueqiu_follow_strategy_2024"
    salt = b"xueqiu_salt_2024"
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_password(password: str) -> str:
    """
    加密密码
    
    Args:
        password: 明文密码
        
    Returns:
        加密后的密码（Base64编码）
    """
    if not password:
        return ""
    
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted_password = f.encrypt(password.encode('utf-8'))
        return base64.b64encode(encrypted_password).decode('utf-8')
    except Exception as e:
        raise ValueError(f"密码加密失败: {e}")


def decrypt_password(encrypted_password: str) -> str:
    """
    解密密码
    
    Args:
        encrypted_password: 加密的密码（Base64编码）
        
    Returns:
        明文密码
    """
    if not encrypted_password:
        return ""
    
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted_data = base64.b64decode(encrypted_password.encode('utf-8'))
        decrypted_password = f.decrypt(encrypted_data)
        return decrypted_password.decode('utf-8')
    except Exception as e:
        raise ValueError(f"密码解密失败: {e}")


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理（用于验证）
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的密码
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        验证结果
    """
    return hash_password(password) == hashed_password