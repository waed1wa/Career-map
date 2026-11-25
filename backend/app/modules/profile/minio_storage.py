"""Хранилище резюме в MinIO — адаптер порта ResumeStorage (контейнер «Файловое хранилище» на C4)."""

import io

from minio import Minio

from app.core.config import Settings


class MinioResumeStorage:
    def __init__(self, client: Minio, bucket: str):
        self._client = client
        self._bucket = bucket
        self._bucket_ready = False

    @classmethod
    def from_settings(cls, settings: Settings) -> "MinioResumeStorage":
        # Внутри сети Docker MinIO работает без HTTPS: наружу он не смотрит, HTTPS на стенде даёт Nginx
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
        return cls(client, settings.minio_bucket_resumes)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        if not self._bucket_ready:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
            self._bucket_ready = True
        self._client.put_object(
            self._bucket, key, io.BytesIO(data), length=len(data), content_type=content_type
        )

    def get(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return bytes(response.read())
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)
