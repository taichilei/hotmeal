"""
@File       : minio_client.py
@Author     : ChiLei Tai JOU
@Date       : 2025-04-18
@Description: MinIO 对象存储客户端封装，提供文件上传功能
"""
import os
import uuid

from dotenv import load_dotenv
from minio import Minio
from werkzeug.utils import secure_filename

load_dotenv()

client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=os.getenv("MINIO_SECURE") == "true"
)

bucket_name = os.getenv("MINIO_BUCKET")

def upload_to_minio(file, folder="avatar"):
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1]
    object_name = f"{folder}/{uuid.uuid4().hex}.{ext}"

    # 若桶不存在就创建
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=file.stream,
        length=-1,
        part_size=10 * 1024 * 1024,
        content_type=file.mimetype,
    )

    return f"http://{os.getenv('MINIO_ENDPOINT')}/{bucket_name}/{object_name}"
