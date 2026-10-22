import uuid
import tempfile
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

def _get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        endpoint_url=settings.AWS_ENDPOINT_URL
    )

def save_upload(content: bytes, original_filename: str, user_id: int) -> str:
    """Yüklenen dosyayı storage'a kaydeder ve göreli yolunu (key) döner."""
    suffix = Path(original_filename).suffix.lower()
    relative = f"user_{user_id}/{uuid.uuid4().hex}{suffix}"
    
    if settings.STORAGE_BACKEND == "local":
        target = Path(settings.STORAGE_DIR) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    elif settings.STORAGE_BACKEND == "s3":
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=relative,
            Body=content
        )
    else:
        raise NotImplementedError(f"Storage backend desteklenmiyor: {settings.STORAGE_BACKEND}")
        
    return relative


@contextmanager
def get_file_path(relative_path: str) -> Generator[Path, None, None]:
    """Dosyanın okunabilir bir yerel Path nesnesini context içinde döner.
    
    S3 ise dosyayı /tmp klasörüne indirir, yield eder, blok bittiğinde siler.
    Local ise doğrudan dosya yolunu döner (silmez).
    """
    if settings.STORAGE_BACKEND == "local":
        yield Path(settings.STORAGE_DIR) / relative_path
    elif settings.STORAGE_BACKEND == "s3":
        s3 = _get_s3_client()
        suffix = Path(relative_path).suffix
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        try:
            s3.download_file(settings.AWS_BUCKET_NAME, relative_path, temp_path)
            yield Path(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    else:
        raise NotImplementedError(f"Storage backend desteklenmiyor: {settings.STORAGE_BACKEND}")


def delete_upload(relative_path: str) -> None:
    """Storage'daki dosyayı siler; dosya zaten yoksa sessizce geçer."""
    if settings.STORAGE_BACKEND == "local":
        target = Path(settings.STORAGE_DIR) / relative_path
        target.unlink(missing_ok=True)
    elif settings.STORAGE_BACKEND == "s3":
        s3 = _get_s3_client()
        try:
            s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=relative_path)
        except ClientError:
            pass
    else:
        raise NotImplementedError(f"Storage backend desteklenmiyor: {settings.STORAGE_BACKEND}")
