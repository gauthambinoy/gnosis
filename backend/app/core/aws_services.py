"""
Gnosis AWS Service Layer
Gracefully degrades to local alternatives when AWS is unavailable.
"""
import json
import time
import uuid
from typing import Optional
from app.config import get_settings

# Try importing boto3
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError  # noqa: F401  (re-exported for callers)
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

class AWSServices:
    """Unified AWS client — falls back to local when not configured."""
    
    def __init__(self):
        self.settings = get_settings()
        self._s3 = None
        self._sqs = None
        self._ses = None
        self._dynamodb = None
        self._available = False
        self._init_clients()
    
    def _init_clients(self):
        if not HAS_BOTO3:
            return
        try:
            session_kwargs = {"region_name": self.settings.aws_region}
            if self.settings.aws_access_key_id:
                session_kwargs["aws_access_key_id"] = self.settings.aws_access_key_id
                session_kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key
            session = boto3.Session(**session_kwargs)
            self._s3 = session.client("s3")
            self._sqs = session.client("sqs")
            self._ses = session.client("ses")
            self._dynamodb = session.resource("dynamodb")
            self._available = True
        except Exception:
            self._available = False
    
    @property
    def available(self) -> bool:
        return self._available
    
    # ─── S3 File Storage ───
    async def upload_file(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream", bucket: str = "") -> Optional[str]:
        bucket = bucket or self.settings.s3_upload_bucket
        if not self._available or not bucket:
            return None  # Caller falls back to local storage
        try:
            key = f"uploads/{uuid.uuid4().hex}/{filename}"
            self._s3.put_object(Bucket=bucket, Key=key, Body=file_bytes, ContentType=content_type)
            return f"s3://{bucket}/{key}"
        except Exception:
            return None
    
    async def download_file(self, s3_uri: str) -> Optional[bytes]:
        if not self._available or not s3_uri.startswith("s3://"):
            return None
        try:
            parts = s3_uri.replace("s3://", "").split("/", 1)
            bucket, key = parts[0], parts[1]
            resp = self._s3.get_object(Bucket=bucket, Key=key)
            return resp["Body"].read()
        except Exception:
            return None
    
    async def generate_presigned_url(self, s3_uri: str, expires_in: int = 3600) -> Optional[str]:
        if not self._available or not s3_uri.startswith("s3://"):
            return None
        try:
            parts = s3_uri.replace("s3://", "").split("/", 1)
            return self._s3.generate_presigned_url(
                "get_object", Params={"Bucket": parts[0], "Key": parts[1]}, ExpiresIn=expires_in
            )
        except Exception:
            return None
    
    async def delete_file(self, s3_uri: str) -> bool:
        if not self._available or not s3_uri.startswith("s3://"):
            return False
        try:
            parts = s3_uri.replace("s3://", "").split("/", 1)
            self._s3.delete_object(Bucket=parts[0], Key=parts[1])
            return True
        except Exception:
            return False
    
    # ─── SQS Message Queue ───
    async def send_execution_task(self, agent_id: str, user_input: str, user_id: str = "") -> Optional[str]:
        queue_url = self.settings.sqs_execution_queue_url
        if not self._available or not queue_url:
            return None  # Caller executes synchronously
        try:
            msg = json.dumps({"agent_id": agent_id, "user_input": user_input, "user_id": user_id, "timestamp": time.time()})
            resp = self._sqs.send_message(QueueUrl=queue_url, MessageBody=msg, MessageGroupId=agent_id if ".fifo" in queue_url else None)
            return resp.get("MessageId")
        except Exception:
            return None
    
    async def send_webhook_event(self, webhook_id: str, payload: dict) -> Optional[str]:
        queue_url = self.settings.sqs_webhook_queue_url
        if not self._available or not queue_url:
            return None
        try:
            msg = json.dumps({"webhook_id": webhook_id, "payload": payload, "timestamp": time.time()})
            resp = self._sqs.send_message(QueueUrl=queue_url, MessageBody=msg)
            return resp.get("MessageId")
        except Exception:
            return None
    
    # ─── SES Email ───
    async def send_email(self, to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
        sender = self.settings.ses_sender_email
        if not self._available or not sender:
            return False
        try:
            self._ses.send_email(
                Source=sender,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Html": {"Data": html_body},
                        "Text": {"Data": text_body or subject}
                    }
                }
            )
            return True
        except Exception:
            return False
    
    # ─── DynamoDB Execution History ───
    async def log_execution(self, agent_id: str, user_id: str, result: dict) -> bool:
        table_name = self.settings.dynamodb_execution_table
        if not self._available or not table_name:
            return False
        try:
            table = self._dynamodb.Table(table_name)
            table.put_item(Item={
                "agent_id": agent_id,
                "timestamp": str(time.time()),
                "user_id": user_id,
                "status": result.get("status", "unknown"),
                "duration_ms": result.get("duration_ms", 0),
                "tokens_used": result.get("tokens_used", 0),
                "result_summary": json.dumps(result)[:1000],
                "expires_at": int(time.time()) + 86400 * 90  # TTL: 90 days
            })
            return True
        except Exception:
            return False
    
    async def get_execution_history(self, agent_id: str, limit: int = 20) -> list[dict]:
        table_name = self.settings.dynamodb_execution_table
        if not self._available or not table_name:
            return []
        try:
            table = self._dynamodb.Table(table_name)
            resp = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("agent_id").eq(agent_id),
                ScanIndexForward=False, Limit=limit
            )
            return resp.get("Items", [])
        except Exception:
            return []
    
    def get_status(self) -> dict:
        return {
            "aws_available": self._available,
            "boto3_installed": HAS_BOTO3,
            "s3_bucket": self.settings.s3_upload_bucket or "(not configured)",
            "sqs_queue": bool(self.settings.sqs_execution_queue_url),
            "ses_sender": self.settings.ses_sender_email or "(not configured)",
            "dynamodb_table": self.settings.dynamodb_execution_table or "(not configured)",
        }

# Singleton
aws_services = AWSServices()
