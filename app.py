import hmac
import hashlib
import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "douyin_demo.db"))
DB_DIR = os.path.dirname(DB_PATH)
if DB_DIR:
    os.makedirs(DB_DIR, exist_ok=True)
DB_URL = f"sqlite:///{DB_PATH}"

DY_SECRET_KEY = os.getenv("DY_SECRET_KEY", "")
DY_BASE_URL = os.getenv(
    "DY_BASE_URL",
    "https://gmp.bytedanceapi.com/ai_chat_agent_test_api/v1/openapi",
)
DY_ALLOWED_DRIFT_SECONDS = int(os.getenv("DY_ALLOWED_DRIFT_SECONDS", "300"))
DY_HTTP_TIMEOUT_SECONDS = int(os.getenv("DY_HTTP_TIMEOUT_SECONDS", "20"))
DY_CLIENT_KEY = os.getenv("DY_CLIENT_KEY", "")
DY_CLIENT_SECRET = os.getenv("DY_CLIENT_SECRET", "")
DY_OAUTH_BASE_URL = os.getenv("DY_OAUTH_BASE_URL", "https://open.douyin.com")
DY_CALLBACK_EVENTS = [
    item.strip()
    for item in os.getenv("DY_CALLBACK_EVENTS", "").split(",")
    if item.strip()
]
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
AUTH_REDIRECT_URL = os.getenv("AUTH_REDIRECT_URL", "")
DY_MAIN_ACCOUNT_ID = int(os.getenv("DY_MAIN_ACCOUNT_ID", "0"))
DY_ACCOUNT_NAME = os.getenv("DY_ACCOUNT_NAME", "")
AIGC_BASE_URL = os.getenv("AIGC_BASE_URL", "").rstrip("/")
AIGC_API_TOKEN = os.getenv("AIGC_API_TOKEN", "")
AIGC_AUTH_HEADER = os.getenv("AIGC_AUTH_HEADER", "Access-Token")
AIGC_AUTH_PREFIX = os.getenv("AIGC_AUTH_PREFIX", "")
AIGC_UPLOAD_ELEMENT_PATH = os.getenv("AIGC_UPLOAD_ELEMENT_PATH", "/open_api/v3.0/aic/element/upload/")
AIGC_CREATE_TASK_PATH = os.getenv("AIGC_CREATE_TASK_PATH", "/open_api/v3.0/aic/video_mixcut/create/")
AIGC_QUERY_TASK_PATH = os.getenv("AIGC_QUERY_TASK_PATH", "/video_clip/tasks/{task_id}")
AIGC_HTTP_TIMEOUT_SECONDS = int(os.getenv("AIGC_HTTP_TIMEOUT_SECONDS", "60"))
AIGC_MOCK_ENABLED = os.getenv("AIGC_MOCK_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
REVIEW_BASE_URL = os.getenv("REVIEW_BASE_URL", "https://api.oceanengine.com").rstrip("/")
REVIEW_ACCESS_TOKEN = os.getenv("REVIEW_ACCESS_TOKEN", "")
REVIEW_AUTH_HEADER = os.getenv("REVIEW_AUTH_HEADER", "Access-Token")
REVIEW_AUTH_PREFIX = os.getenv("REVIEW_AUTH_PREFIX", "")
REVIEW_SUGGESTIONS_PATH = os.getenv("REVIEW_SUGGESTIONS_PATH", "/open_api/v3.0/reject_material/ai_repair/get/")
REVIEW_CROSS_ACCOUNT_PATH = os.getenv("REVIEW_CROSS_ACCOUNT_PATH", "/open_api/v3.0/reject_material/ai_repair/cross_account/get/")
REVIEW_ADOPT_CREATE_PATH = os.getenv("REVIEW_ADOPT_CREATE_PATH", "/open_api/v3.0/reject_material/ai_repair/adopt_task/create/")
REVIEW_ADOPT_RESULT_PATH = os.getenv("REVIEW_ADOPT_RESULT_PATH", "/open_api/v3.0/reject_material/ai_repair/adopt_task/get/")
REVIEW_HTTP_TIMEOUT_SECONDS = int(os.getenv("REVIEW_HTTP_TIMEOUT_SECONDS", "60"))
REVIEW_MOCK_ENABLED = os.getenv("REVIEW_MOCK_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title="Douyin DM Lead Demo", version="0.1.0")
logger = logging.getLogger("douyin_demo")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@app.middleware("http")
async def webhook_request_logger(request: Request, call_next):
    if request.url.path == "/webhook/douyin":
        body = await request.body()
        logger.info(
            "webhook incoming method=%s path=%s headers=%s body=%s",
            request.method,
            request.url.path,
            {
                "X-Auth-Timestamp": request.headers.get("X-Auth-Timestamp"),
                "Authorization": request.headers.get("Authorization"),
                "Content-Type": request.headers.get("Content-Type"),
            },
            body.decode("utf-8", errors="replace")[:4000],
        )
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}
        request = Request(request.scope, receive)

    response = await call_next(request)
    if request.url.path == "/webhook/douyin":
        logger.info("webhook response method=%s path=%s status=%s", request.method, request.url.path, response.status_code)
    return response


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event = Column(String(128), nullable=True)
    from_user_id = Column(String(255), nullable=True)
    to_user_id = Column(String(255), nullable=True)
    conversation_short_id = Column(Text, nullable=True)
    server_message_id = Column(Text, nullable=True)
    message_type = Column(String(128), nullable=True)
    create_time = Column(String(64), nullable=True)
    raw_body = Column(Text, nullable=False)
    raw_content = Column(Text, nullable=True)
    event_key = Column(String(128), nullable=True)
    is_duplicate = Column(Integer, nullable=False, default=0)
    created_at = Column(String(64), nullable=False)


class LeadContact(Base):
    __tablename__ = "lead_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    open_id = Column(String(255), nullable=False, unique=True, index=True)
    account_open_id = Column(String(255), nullable=True)
    latest_event = Column(String(128), nullable=True)
    latest_message_type = Column(String(128), nullable=True)
    conversation_short_id = Column(Text, nullable=True)
    server_message_id = Column(Text, nullable=True)
    latest_scene = Column(String(128), nullable=True)
    first_active_time = Column(String(64), nullable=True)
    latest_active_time = Column(String(64), nullable=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    phone = Column(String(64), nullable=True)
    wechat = Column(String(128), nullable=True)
    lead_status = Column(String(64), nullable=True)
    assignee = Column(String(128), nullable=True)
    remark = Column(Text, nullable=True)
    lead_channel = Column(String(128), nullable=True)
    lead_type = Column(String(128), nullable=True)
    tags = Column(Text, nullable=True)
    last_interaction_record = Column(Text, nullable=True)
    raw_snapshot = Column(Text, nullable=True)


class ApiCallLog(Base):
    __tablename__ = "api_call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_path = Column(String(255), nullable=False)
    request_body = Column(Text, nullable=False)
    request_timestamp = Column(String(64), nullable=False)
    http_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_type = Column(String(128), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_short_id = Column(Text, nullable=False, unique=True)
    lead_open_id = Column(String(255), nullable=False, index=True)
    account_open_id = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    latest_event = Column(String(128), nullable=True)
    latest_message_type = Column(String(128), nullable=True)
    latest_message_text = Column(Text, nullable=True)
    latest_message_time = Column(String(64), nullable=True)
    unread_count = Column(Integer, nullable=False, default=0)
    is_pinned = Column(Integer, nullable=False, default=0)
    is_closed = Column(Integer, nullable=False, default=0)
    raw_snapshot = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_short_id = Column(Text, nullable=False, index=True)
    server_message_id = Column(Text, nullable=True)
    sender_open_id = Column(String(255), nullable=True)
    receiver_open_id = Column(String(255), nullable=True)
    direction = Column(String(32), nullable=True)
    message_type = Column(String(128), nullable=True)
    message_text = Column(Text, nullable=True)
    create_time = Column(String(64), nullable=True)
    is_read = Column(Integer, nullable=False, default=0)
    raw_content = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)


class LeadFollowRecord(Base):
    __tablename__ = "lead_follow_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_open_id = Column(String(255), nullable=False, index=True)
    conversation_short_id = Column(Text, nullable=True)
    action_type = Column(String(64), nullable=False)
    content = Column(Text, nullable=True)
    operator_name = Column(String(128), nullable=True)
    created_at = Column(String(64), nullable=False)


class QuickReply(Base):
    __tablename__ = "quick_replies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(String(64), nullable=False)


class AuthCallbackRecord(Base):
    __tablename__ = "auth_callback_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(Text, nullable=True)
    auth_code = Column(Text, nullable=True)
    state = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    open_id = Column(String(255), nullable=True)
    nick_name = Column(String(255), nullable=True)
    avatar = Column(Text, nullable=True)
    raw_query = Column(Text, nullable=True)
    callback_url = Column(Text, nullable=False)
    created_at = Column(String(64), nullable=False)


class AuthTokenRecord(Base):
    __tablename__ = "auth_token_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    callback_record_id = Column(Integer, nullable=True)
    open_id = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    expires_in = Column(Integer, nullable=True)
    refresh_expires_in = Column(Integer, nullable=True)
    access_token_expires_at = Column(String(64), nullable=True)
    refresh_token_expires_at = Column(String(64), nullable=True)
    status = Column(String(64), nullable=False)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class AigcVideoTask(Base):
    __tablename__ = "aigc_video_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(128), nullable=False, unique=True, index=True)
    task_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=True)
    prompt = Column(Text, nullable=True)
    script = Column(Text, nullable=True)
    product_name = Column(String(255), nullable=True)
    selling_points = Column(Text, nullable=True)
    material_urls = Column(Text, nullable=True)
    image_urls = Column(Text, nullable=True)
    status = Column(String(64), nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    result_video_url = Column(Text, nullable=True)
    result_cover_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    source = Column(String(32), nullable=False, default="mock")
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class SendMsgRequest(BaseModel):
    main_account_id: int
    from_user_id: str
    to_user_id: str
    content: str | None = None
    image_id: str | None = None
    conversation_id: str | None = None
    msg_id: str | None = None
    scene: str | None = Field(
        default=None,
        description="im_reply_msg / im_enter_direct_msg / im_b2b_direct_message / im_authorize_message",
    )


class SendLeadMessageRequest(BaseModel):
    main_account_id: int
    from_user_id: str
    lead_open_id: str
    content: str | None = None
    image_id: str | None = None
    scene: str = "im_enter_direct_msg"


class AuthUrlRequest(BaseModel):
    main_account_id: int
    account_name: str
    auth_redirect_url: str
    callback_url: str
    callback_event: list[str] | None = None


class UploadImageRequest(BaseModel):
    main_account_id: int
    image_base64: str
    file_name: str


class DownloadResourceRequest(BaseModel):
    main_account_id: int
    conversation_id: str
    msg_id: str
    resource_type: str


class AigcVideoTaskCreateRequest(BaseModel):
    account_id: int | None = None
    account_type: str | None = None
    task_type: str = Field(default="video_edit", description="video_edit / image_to_video")
    title: str | None = None
    prompt: str | None = None
    script: str | None = None
    product_name: str | None = None
    selling_points: list[str] = Field(default_factory=list)
    benefit_points: list[str] = Field(default_factory=list)
    video_element_ids: list[int] = Field(default_factory=list)
    material_urls: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    count: int = 1
    task_name: str | None = None
    is_auto_save_all_result: bool = False
    gen_element: dict[str, Any] = Field(default_factory=dict)
    subtitle_style: dict[str, Any] = Field(default_factory=dict)
    render_option: dict[str, Any] = Field(default_factory=dict)
    audio_option: dict[str, Any] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class AigcPassthroughRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class ReviewPassthroughRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class LeadAssignRequest(BaseModel):
    assignee: str


class LeadFollowRequest(BaseModel):
    content: str
    operator_name: str | None = None
    action_type: str = "follow_up"


class LeadTagRequest(BaseModel):
    tags: list[str]


class QuickReplyRequest(BaseModel):
    title: str
    content: str


class ConversationSendMessageRequest(BaseModel):
    main_account_id: int
    from_user_id: str
    content: str | None = None
    image_id: str | None = None
    scene: str = "im_reply_msg"


class AuthCallbackSaveRequest(BaseModel):
    code: str | None = None
    auth_code: str | None = None
    state: str | None = None
    error: str | None = None
    open_id: str | None = None
    nick_name: str | None = None
    avatar: str | None = None
    raw_query: str | None = None
    callback_url: str


class BindInfoRequest(BaseModel):
    main_account_id: int
    page_num: int = 1
    page_size: int = 10
    name_or_open_id: str | None = None


class UpstreamApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        upstream_status: int | None = None,
        response_text: str | None = None,
        error_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.upstream_status = upstream_status
        self.response_text = response_text
        self.error_type = error_type


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def future_iso(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    return datetime.fromtimestamp(time.time() + seconds, tz=timezone.utc).isoformat()


def parse_dt_millis(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def in_millis_range(value: str | None, start_ms: int | None, end_ms: int | None) -> bool:
    current = parse_dt_millis(value)
    if current is None:
        return start_ms is None and end_ms is None
    if start_ms is not None and current < start_ms:
        return False
    if end_ms is not None and current > end_ms:
        return False
    return True


@contextmanager
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    with db_session() as session:
        yield session


async def verify_signature(
    request: Request,
    ts_str: str = Header(..., alias="X-Auth-Timestamp"),
    signature: str = Header(..., alias="Authorization"),
) -> None:
    if not DY_SECRET_KEY:
        raise HTTPException(500, "DY_SECRET_KEY is not configured")

    try:
        ts = int(ts_str)
    except ValueError as exc:
        raise HTTPException(401, "Invalid timestamp") from exc

    now_ts = int(time.time())
    if abs(now_ts - ts) > DY_ALLOWED_DRIFT_SECONDS:
        raise HTTPException(401, "Request expired")

    body = await request.body()
    logger.info(
        "webhook verify start path=%s timestamp=%s auth_present=%s body=%s",
        request.url.path,
        ts_str,
        bool(signature),
        body.decode("utf-8", errors="replace")[:2000],
    )
    sign_str = body.decode("utf-8") + "-" + ts_str
    expect = hashlib.sha256((DY_SECRET_KEY + sign_str).encode("utf-8")).hexdigest()
    if not hmac.compare_digest(expect, signature):
        logger.warning(
            "webhook signature mismatch path=%s timestamp=%s expected=%s actual=%s",
            request.url.path,
            ts_str,
            expect,
            signature,
        )
        raise HTTPException(401, "Signature mismatch")


def parse_content(raw_content: Any) -> dict[str, Any]:
    if isinstance(raw_content, dict):
        return raw_content
    if isinstance(raw_content, str):
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            return {}
    return {}


def normalize_message_text(content: dict[str, Any]) -> str:
    for key in ["text", "content", "title", "message"]:
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def extract_user_profile(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    content = parse_content(payload.get("content"))
    user_infos = content.get("user_infos") or []
    from_user_id = payload.get("from_user_id")
    for user in user_infos:
        if user.get("open_id") == from_user_id:
            return user.get("nick_name"), user.get("avatar")
    if user_infos:
        first_user = user_infos[0]
        return first_user.get("nick_name"), first_user.get("avatar")
    return None, None


def build_event_key(payload: dict[str, Any]) -> str:
    content = parse_content(payload.get("content"))
    key_parts = [
        str(payload.get("event") or ""),
        str(payload.get("from_user_id") or ""),
        str(payload.get("to_user_id") or ""),
        str(content.get("conversation_short_id") or ""),
        str(content.get("server_message_id") or ""),
        str(content.get("create_time") or ""),
    ]
    raw_key = "|".join(key_parts)
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def persist_event(session: Session, payload: dict[str, Any], event_key: str, is_duplicate: bool) -> WebhookEvent:
    content = parse_content(payload.get("content"))
    event = WebhookEvent(
        event=payload.get("event"),
        from_user_id=payload.get("from_user_id"),
        to_user_id=payload.get("to_user_id"),
        conversation_short_id=content.get("conversation_short_id"),
        server_message_id=content.get("server_message_id"),
        message_type=content.get("message_type"),
        create_time=str(content.get("create_time") or ""),
        raw_body=json.dumps(payload, ensure_ascii=False),
        raw_content=json.dumps(content, ensure_ascii=False),
        event_key=event_key,
        is_duplicate=1 if is_duplicate else 0,
        created_at=now_iso(),
    )
    session.add(event)
    session.flush()
    return event


def find_existing_event_by_key(session: Session, event_key: str) -> WebhookEvent | None:
    return (
        session.query(WebhookEvent)
        .filter(WebhookEvent.event_key == event_key, WebhookEvent.is_duplicate == 0)
        .order_by(WebhookEvent.id.desc())
        .first()
    )


def upsert_lead_contact(session: Session, payload: dict[str, Any]) -> LeadContact:
    content = parse_content(payload.get("content"))
    open_id = payload.get("from_user_id")
    if not open_id:
        raise HTTPException(400, "Webhook payload missing from_user_id")
    display_name, avatar_url = extract_user_profile(payload)
    last_message_text = normalize_message_text(content)

    lead = session.query(LeadContact).filter(LeadContact.open_id == open_id).one_or_none()
    if lead is None:
        lead = LeadContact(
            open_id=open_id,
            first_active_time=str(content.get("create_time") or ""),
            lead_status="pending",
        )
        session.add(lead)

    lead.account_open_id = payload.get("to_user_id")
    lead.latest_event = payload.get("event")
    lead.latest_message_type = content.get("message_type")
    lead.conversation_short_id = content.get("conversation_short_id")
    lead.server_message_id = content.get("server_message_id")
    lead.latest_scene = payload.get("event")
    lead.latest_active_time = str(content.get("create_time") or "")
    lead.display_name = display_name or lead.display_name or "未命名"
    lead.avatar_url = avatar_url or lead.avatar_url
    lead.lead_channel = "企业号"
    lead.lead_type = "私信"
    lead.last_interaction_record = last_message_text or lead.last_interaction_record
    lead.raw_snapshot = json.dumps(payload, ensure_ascii=False)
    session.flush()
    return lead


def upsert_conversation(session: Session, payload: dict[str, Any], lead: LeadContact) -> Conversation | None:
    content = parse_content(payload.get("content"))
    conversation_short_id = content.get("conversation_short_id")
    if not conversation_short_id:
        return None

    display_name, avatar_url = extract_user_profile(payload)
    latest_message_text = normalize_message_text(content)
    event = payload.get("event")
    conversation = (
        session.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        conversation = Conversation(
            conversation_short_id=conversation_short_id,
            lead_open_id=lead.open_id,
            account_open_id=payload.get("to_user_id"),
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        session.add(conversation)

    conversation.lead_open_id = lead.open_id
    conversation.account_open_id = payload.get("to_user_id")
    conversation.display_name = display_name or lead.display_name or conversation.display_name
    conversation.avatar_url = avatar_url or lead.avatar_url or conversation.avatar_url
    conversation.latest_event = event
    conversation.latest_message_type = content.get("message_type")
    conversation.latest_message_text = latest_message_text or conversation.latest_message_text
    conversation.latest_message_time = str(content.get("create_time") or "")
    if event == "im_receive_msg":
        conversation.unread_count = (conversation.unread_count or 0) + 1
    conversation.raw_snapshot = json.dumps(payload, ensure_ascii=False)
    conversation.updated_at = now_iso()
    session.flush()
    return conversation


def persist_message(session: Session, payload: dict[str, Any], conversation: Conversation | None) -> Message | None:
    content = parse_content(payload.get("content"))
    conversation_short_id = content.get("conversation_short_id")
    if conversation is None or not conversation_short_id:
        return None

    direction = "inbound"
    if payload.get("event") == "im_send_msg":
        direction = "outbound"

    message = Message(
        conversation_short_id=conversation_short_id,
        server_message_id=content.get("server_message_id"),
        sender_open_id=payload.get("from_user_id"),
        receiver_open_id=payload.get("to_user_id"),
        direction=direction,
        message_type=content.get("message_type"),
        message_text=normalize_message_text(content),
        create_time=str(content.get("create_time") or ""),
        is_read=0 if direction == "inbound" else 1,
        raw_content=json.dumps(content, ensure_ascii=False),
        created_at=now_iso(),
    )
    session.add(message)
    session.flush()
    return message


def create_follow_record(
    session: Session,
    *,
    lead_open_id: str,
    conversation_short_id: str | None,
    action_type: str,
    content: str | None,
    operator_name: str | None,
) -> LeadFollowRecord:
    record = LeadFollowRecord(
        lead_open_id=lead_open_id,
        conversation_short_id=conversation_short_id,
        action_type=action_type,
        content=content,
        operator_name=operator_name,
        created_at=now_iso(),
    )
    session.add(record)
    session.flush()
    return record


def persist_api_call_log(
    session: Session,
    path: str,
    request_body: str,
    request_timestamp: str,
    http_status: int | None = None,
    response_body: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> ApiCallLog:
    log = ApiCallLog(
        api_path=path,
        request_body=request_body,
        request_timestamp=request_timestamp,
        http_status=http_status,
        response_body=response_body,
        error_type=error_type,
        error_message=error_message,
        created_at=now_iso(),
    )
    session.add(log)
    session.flush()
    return log


def persist_auth_callback_record(
    session: Session,
    body: AuthCallbackSaveRequest,
) -> AuthCallbackRecord:
    record = AuthCallbackRecord(
        code=body.code,
        auth_code=body.auth_code,
        state=body.state,
        error=body.error,
        open_id=body.open_id,
        nick_name=body.nick_name,
        avatar=body.avatar,
        raw_query=body.raw_query,
        callback_url=body.callback_url,
        created_at=now_iso(),
    )
    session.add(record)
    session.flush()
    return record


def persist_auth_token_record(
    session: Session,
    *,
    callback_record_id: int | None,
    token_data: dict[str, Any] | None,
    raw_response: dict[str, Any],
    status: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> AuthTokenRecord:
    token_data = token_data or {}
    expires_in = int(token_data["expires_in"]) if str(token_data.get("expires_in") or "").isdigit() else None
    refresh_expires_in = (
        int(token_data["refresh_expires_in"])
        if str(token_data.get("refresh_expires_in") or "").isdigit()
        else None
    )
    record = AuthTokenRecord(
        callback_record_id=callback_record_id,
        open_id=token_data.get("open_id"),
        access_token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        scope=token_data.get("scope"),
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in,
        access_token_expires_at=future_iso(expires_in),
        refresh_token_expires_at=future_iso(refresh_expires_in),
        status=status,
        error_code=error_code,
        error_message=error_message,
        raw_response=json.dumps(raw_response, ensure_ascii=False),
        created_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(record)
    session.flush()
    return record


def serialize_aigc_task(task: AigcVideoTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "task_id": task.task_id,
        "task_type": task.task_type,
        "title": task.title,
        "prompt": task.prompt,
        "script": task.script,
        "product_name": task.product_name,
        "selling_points": json.loads(task.selling_points) if task.selling_points else [],
        "material_urls": json.loads(task.material_urls) if task.material_urls else [],
        "image_urls": json.loads(task.image_urls) if task.image_urls else [],
        "status": task.status,
        "progress": task.progress,
        "result_video_url": task.result_video_url,
        "result_cover_url": task.result_cover_url,
        "error_message": task.error_message,
        "source": task.source,
        "response_body": json.loads(task.response_body) if task.response_body else None,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def persist_aigc_video_task(
    session: Session,
    *,
    task_id: str,
    task_type: str,
    title: str | None,
    prompt: str | None,
    script: str | None,
    product_name: str | None,
    selling_points: list[str],
    material_urls: list[str],
    image_urls: list[str],
    request_body: dict[str, Any],
    status: str,
    progress: int,
    response_body: dict[str, Any] | None,
    result_video_url: str | None,
    result_cover_url: str | None,
    error_message: str | None,
    source: str,
) -> AigcVideoTask:
    now = now_iso()
    task = (
        session.query(AigcVideoTask)
        .filter(AigcVideoTask.task_id == task_id)
        .one_or_none()
    )
    if task is None:
        task = AigcVideoTask(
            task_id=task_id,
            task_type=task_type,
            created_at=now,
            updated_at=now,
        )
        session.add(task)

    task.task_type = task_type
    task.title = title
    task.prompt = prompt
    task.script = script
    task.product_name = product_name
    task.selling_points = json.dumps(selling_points, ensure_ascii=False)
    task.material_urls = json.dumps(material_urls, ensure_ascii=False)
    task.image_urls = json.dumps(image_urls, ensure_ascii=False)
    task.status = status
    task.progress = progress
    task.request_body = json.dumps(request_body, ensure_ascii=False)
    task.response_body = json.dumps(response_body, ensure_ascii=False) if response_body is not None else None
    task.result_video_url = result_video_url
    task.result_cover_url = result_cover_url
    task.error_message = error_message
    task.source = source
    task.updated_at = now
    session.flush()
    return task


def build_aigc_payload(body: AigcVideoTaskCreateRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "account_id": body.account_id,
        "account_type": body.account_type,
        "product_info": {
            "product_name": body.product_name,
        },
        "product_selling_points": body.selling_points,
        "benefit_points": body.benefit_points,
        "video_element_ids": body.video_element_ids,
        "count": body.count,
        "task_name": body.task_name,
        "is_auto_save_all_result": body.is_auto_save_all_result,
    }

    if body.gen_element:
        payload["gen_element"] = body.gen_element
    if body.subtitle_style:
        payload["subtitle_style"] = body.subtitle_style
    if body.render_option:
        payload["render_option"] = body.render_option
    if body.audio_option:
        payload["audio_option"] = body.audio_option

    if body.prompt or body.script or body.material_urls or body.image_urls or body.extra:
        payload["extra"] = {
            "task_type": body.task_type,
            "title": body.title,
            "prompt": body.prompt,
            "script": body.script,
            "material_urls": body.material_urls,
            "image_urls": body.image_urls,
            **body.extra,
        }

    return {key: value for key, value in payload.items() if value not in (None, "", [], {})}


def make_mock_aigc_response(task_id: str, body: AigcVideoTaskCreateRequest) -> dict[str, Any]:
    suffix = task_id[-6:]
    status = "succeeded"
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "task_id": task_id,
            "status": status,
            "progress": 100,
            "task_type": body.task_type,
            "video_url": f"https://mock.misanduo.local/videos/{suffix}.mp4",
            "cover_url": f"https://mock.misanduo.local/covers/{suffix}.jpg",
            "summary": {
                "title": body.title or "未命名视频任务",
                "product_name": body.product_name or "未填写商品",
                "material_count": len(body.material_urls),
                "image_count": len(body.image_urls),
            },
        },
    }


def create_aigc_task_via_upstream(payload: dict[str, Any]) -> dict[str, Any]:
    if not AIGC_BASE_URL:
        raise HTTPException(400, "AIGC_BASE_URL is not configured")
    if not AIGC_API_TOKEN:
        raise HTTPException(400, "AIGC_API_TOKEN is not configured")

    request_timestamp = str(int(time.time()))
    url = f"{AIGC_BASE_URL}{AIGC_CREATE_TASK_PATH}"
    resp = None
    try:
        resp = requests.post(
            url,
            json=payload,
            headers=build_aigc_headers(),
            timeout=AIGC_HTTP_TIMEOUT_SECONDS,
        )
        response_text = resp.text
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"AIGC {AIGC_CREATE_TASK_PATH}",
                request_body=json.dumps(payload, ensure_ascii=False),
                request_timestamp=request_timestamp,
                http_status=resp.status_code,
                response_body=response_text,
            )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        response_text = resp.text if resp is not None else None
        status_code = resp.status_code if resp is not None else None
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"AIGC {AIGC_CREATE_TASK_PATH}",
                request_body=json.dumps(payload, ensure_ascii=False),
                request_timestamp=request_timestamp,
                http_status=status_code,
                response_body=response_text,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise UpstreamApiError(
            "AIGC upstream request failed",
            status_code=502,
            upstream_status=status_code,
            response_text=response_text,
            error_type=type(exc).__name__,
        ) from exc


def query_aigc_task_via_upstream(task_id: str) -> dict[str, Any]:
    if not AIGC_BASE_URL:
        raise HTTPException(400, "AIGC_BASE_URL is not configured")
    if not AIGC_API_TOKEN:
        raise HTTPException(400, "AIGC_API_TOKEN is not configured")

    path = AIGC_QUERY_TASK_PATH.format(task_id=task_id)
    request_timestamp = str(int(time.time()))
    url = f"{AIGC_BASE_URL}{path}"
    resp = None
    try:
        resp = requests.get(
            url,
            headers=build_aigc_headers(include_content_type=False),
            timeout=AIGC_HTTP_TIMEOUT_SECONDS,
        )
        response_text = resp.text
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"AIGC {path}",
                request_body="",
                request_timestamp=request_timestamp,
                http_status=resp.status_code,
                response_body=response_text,
            )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        response_text = resp.text if resp is not None else None
        status_code = resp.status_code if resp is not None else None
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"AIGC {path}",
                request_body="",
                request_timestamp=request_timestamp,
                http_status=status_code,
                response_body=response_text,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise UpstreamApiError(
            "AIGC task query failed",
            status_code=502,
            upstream_status=status_code,
            response_text=response_text,
            error_type=type(exc).__name__,
        ) from exc


def build_aigc_headers(*, include_content_type: bool = True) -> dict[str, str]:
    if not AIGC_API_TOKEN:
        raise HTTPException(400, "AIGC_API_TOKEN is not configured")
    headers: dict[str, str] = {}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    token_value = f"{AIGC_AUTH_PREFIX}{AIGC_API_TOKEN}" if AIGC_AUTH_PREFIX is not None else AIGC_API_TOKEN
    headers[AIGC_AUTH_HEADER] = token_value
    return headers


def call_aigc_upstream_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not AIGC_BASE_URL:
        raise HTTPException(400, "AIGC_BASE_URL is not configured")

    request_timestamp = str(int(time.time()))
    url = f"{AIGC_BASE_URL}{path}"
    resp = None
    request_body = json.dumps(payload, ensure_ascii=False)

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=build_aigc_headers(),
            timeout=AIGC_HTTP_TIMEOUT_SECONDS,
        )
        response_text = resp.text
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"AIGC {path}",
                request_body=request_body,
                request_timestamp=request_timestamp,
                http_status=resp.status_code,
                response_body=response_text,
            )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        response_text = resp.text if resp is not None else None
        status_code = resp.status_code if resp is not None else None
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"AIGC {path}",
                request_body=request_body,
                request_timestamp=request_timestamp,
                http_status=status_code,
                response_body=response_text,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise UpstreamApiError(
            "AIGC upstream request failed",
            status_code=502,
            upstream_status=status_code,
            response_text=response_text,
            error_type=type(exc).__name__,
        ) from exc


def build_review_headers(*, include_content_type: bool = True) -> dict[str, str]:
    if not REVIEW_ACCESS_TOKEN:
        raise HTTPException(400, "REVIEW_ACCESS_TOKEN is not configured")
    headers: dict[str, str] = {}
    if include_content_type:
        headers["Content-Type"] = "application/json"
    headers[REVIEW_AUTH_HEADER] = f"{REVIEW_AUTH_PREFIX}{REVIEW_ACCESS_TOKEN}"
    return headers


def call_review_upstream(
    *,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not REVIEW_BASE_URL:
        raise HTTPException(400, "REVIEW_BASE_URL is not configured")

    url = f"{REVIEW_BASE_URL}{path}"
    request_timestamp = str(int(time.time()))
    request_body = json.dumps(payload, ensure_ascii=False) if payload is not None else ""
    resp = None

    try:
        if method.upper() == "GET":
            params = {
                key: value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                for key, value in (payload or {}).items()
                if value not in (None, "", [], {})
            }
            resp = requests.get(
                url,
                params=params,
                headers=build_review_headers(include_content_type=False),
                timeout=REVIEW_HTTP_TIMEOUT_SECONDS,
            )
            request_body = urlencode(params)
        else:
            resp = requests.post(
                url,
                json=payload or {},
                headers=build_review_headers(),
                timeout=REVIEW_HTTP_TIMEOUT_SECONDS,
            )
        response_text = resp.text
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"REVIEW {path}",
                request_body=request_body,
                request_timestamp=request_timestamp,
                http_status=resp.status_code,
                response_body=response_text,
            )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        response_text = resp.text if resp is not None else None
        status_code = resp.status_code if resp is not None else None
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=f"REVIEW {path}",
                request_body=request_body,
                request_timestamp=request_timestamp,
                http_status=status_code,
                response_body=response_text,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise UpstreamApiError(
            "Review upstream request failed",
            status_code=502,
            upstream_status=status_code,
            response_text=response_text,
            error_type=type(exc).__name__,
        ) from exc


def make_mock_review_response(name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if name == "suggestions":
        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": [
                    {
                        "repair_id": 10001,
                        "material_id": payload.get("material_id", 8888),
                        "reason": "素材含夸张宣传语",
                        "preview_url": "https://mock.misanduo.local/review/preview-10001.mp4",
                        "status": "ready",
                    }
                ]
            },
        }
    if name == "cross_account":
        return {
            "code": 0,
            "message": "success",
            "data": {
                "list": [
                    {
                        "account_id": payload.get("account_id", 123456),
                        "repair_id": 10001,
                        "material_id": payload.get("material_id", 8888),
                    }
                ]
            },
        }
    if name == "adopt_create":
        return {
            "code": 0,
            "message": "success",
            "data": {
                "task_id": f"review_task_{int(time.time() * 1000)}",
                "status": "processing",
            },
        }
    return {
        "code": 0,
        "message": "success",
        "data": {
            "task_id": payload.get("task_id", f"review_task_{int(time.time() * 1000)}"),
            "status": "success",
            "success_count": 1,
            "failed_count": 0,
        },
    }


def sync_aigc_task_from_response(
    task: AigcVideoTask,
    response: dict[str, Any],
    db: Session,
) -> AigcVideoTask:
    data = response.get("data") if isinstance(response, dict) else None
    result_video_url = (data or {}).get("video_url") or (data or {}).get("result_video_url")
    result_cover_url = (data or {}).get("cover_url") or (data or {}).get("result_cover_url")
    progress = int((data or {}).get("progress") or task.progress or 0)
    status = (data or {}).get("status") or task.status
    task.status = status
    task.progress = progress
    task.result_video_url = result_video_url or task.result_video_url
    task.result_cover_url = result_cover_url or task.result_cover_url
    task.response_body = json.dumps(response, ensure_ascii=False)
    task.updated_at = now_iso()
    db.flush()
    return task


def call_oauth_token_api(path: str, form_data: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(
        f"{DY_OAUTH_BASE_URL.rstrip('/')}{path}",
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=DY_HTTP_TIMEOUT_SECONDS,
    )
    response_text = resp.text
    with db_session() as session:
        persist_api_call_log(
            session=session,
            path=path,
            request_body=json.dumps(form_data, ensure_ascii=False),
            request_timestamp=str(int(time.time())),
            http_status=resp.status_code,
            response_body=response_text,
        )
    resp.raise_for_status()
    return resp.json()


def exchange_code_for_access_token(code: str, callback_record_id: int | None = None) -> AuthTokenRecord:
    if not DY_CLIENT_KEY:
        raise HTTPException(400, "DY_CLIENT_KEY is not configured")
    if not DY_CLIENT_SECRET:
        raise HTTPException(400, "DY_CLIENT_SECRET is not configured")

    response = call_oauth_token_api(
        "/oauth/access_token/",
        {
            "client_key": DY_CLIENT_KEY,
            "client_secret": DY_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    data = response.get("data") if isinstance(response, dict) else None
    error_code = str((data or {}).get("error_code") or "")
    message = response.get("message") if isinstance(response, dict) else ""
    status = "success" if error_code in {"", "0"} else "error"

    with db_session() as session:
        return persist_auth_token_record(
            session,
            callback_record_id=callback_record_id,
            token_data=data,
            raw_response=response,
            status=status,
            error_code=error_code or None,
            error_message=message or (data or {}).get("description"),
        )


def build_auth_status(record: AuthTokenRecord | None) -> dict[str, Any]:
    if record is None:
        return {
            "authorized": False,
            "need_reauthorize": True,
            "reason": "no_token_record",
            "token_record": None,
        }

    refresh_expired = False
    if record.refresh_token_expires_at:
        try:
            refresh_expired = datetime.fromisoformat(record.refresh_token_expires_at) <= datetime.now(timezone.utc)
        except ValueError:
            refresh_expired = False

    authorized = record.status == "success" and bool(record.refresh_token) and not refresh_expired
    reason = "ok"
    if record.status != "success":
        reason = "token_exchange_failed"
    elif not record.refresh_token:
        reason = "refresh_token_missing"
    elif refresh_expired:
        reason = "refresh_token_expired"

    return {
        "authorized": authorized,
        "need_reauthorize": not authorized,
        "reason": reason,
        "token_record": {
            "id": record.id,
            "open_id": record.open_id,
            "scope": record.scope,
            "status": record.status,
            "error_code": record.error_code,
            "error_message": record.error_message,
            "expires_in": record.expires_in,
            "refresh_expires_in": record.refresh_expires_in,
            "access_token_expires_at": record.access_token_expires_at,
            "refresh_token_expires_at": record.refresh_token_expires_at,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        },
    }


def build_bind_auth_status(
    callback_record: AuthCallbackRecord | None,
    bind_info: dict[str, Any] | None,
    token_record: AuthTokenRecord | None,
) -> dict[str, Any]:
    bind_status = bind_info.get("bind_status") if bind_info else None
    authorized = bind_status == 1
    reason = "ok" if authorized else "bind_info_not_found"

    if callback_record is None:
        reason = "no_callback_record"
    elif not callback_record.open_id:
        reason = "callback_open_id_missing"
    elif bind_status == 0:
        reason = "not_bound"
    elif bind_status == 2:
        reason = "bind_failed"
    elif bind_status == 3:
        reason = "unbind"

    return {
        "authorized": authorized,
        "need_reauthorize": not authorized,
        "reason": reason,
        "configured_callback_url": f"{PUBLIC_BASE_URL.rstrip('/')}/webhook/douyin" if PUBLIC_BASE_URL else "",
        "configured_auth_redirect_url": AUTH_REDIRECT_URL,
        "callback_record": {
            "id": callback_record.id,
            "open_id": callback_record.open_id,
            "nick_name": callback_record.nick_name,
            "avatar": callback_record.avatar,
            "created_at": callback_record.created_at,
        }
        if callback_record
        else None,
        "bind_info": bind_info,
        "token_record": {
            "id": token_record.id,
            "open_id": token_record.open_id,
            "scope": token_record.scope,
            "status": token_record.status,
            "error_code": token_record.error_code,
            "error_message": token_record.error_message,
            "access_token_expires_at": token_record.access_token_expires_at,
            "refresh_token_expires_at": token_record.refresh_token_expires_at,
        }
        if token_record
        else None,
    }


def signed_post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    if not DY_SECRET_KEY:
        raise HTTPException(500, "DY_SECRET_KEY is not configured")

    body_text = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(int(time.time()))
    sign_str = body_text + "-" + timestamp
    signature = hashlib.sha256((DY_SECRET_KEY + sign_str).encode("utf-8")).hexdigest()
    resp = None

    try:
        resp = requests.post(
            f"{DY_BASE_URL}{path}",
            data=body_text.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Auth-Timestamp": timestamp,
                "Authorization": signature,
            },
            timeout=DY_HTTP_TIMEOUT_SECONDS,
        )

        response_text = resp.text
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=path,
                request_body=body_text,
                request_timestamp=timestamp,
                http_status=resp.status_code,
                response_body=response_text,
            )

        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError as exc:
            raise UpstreamApiError(
                "Upstream returned non-JSON response",
                status_code=502,
                upstream_status=resp.status_code,
                response_text=response_text,
                error_type=type(exc).__name__,
            ) from exc
    except requests.RequestException as exc:
        response_text = None
        status_code = None
        if resp is not None:
            response_text = resp.text
            status_code = resp.status_code

        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=path,
                request_body=body_text,
                request_timestamp=timestamp,
                http_status=status_code,
                response_body=response_text,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise UpstreamApiError(
            "Upstream request failed",
            status_code=502,
            upstream_status=status_code,
            response_text=response_text,
            error_type=type(exc).__name__,
        ) from exc
    except Exception as exc:
        with db_session() as session:
            persist_api_call_log(
                session=session,
                path=path,
                request_body=body_text,
                request_timestamp=timestamp,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise


def run_startup_migrations() -> None:
    with engine.begin() as conn:
        columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(webhook_events)").fetchall()
        }
        if "event_key" not in columns:
            conn.exec_driver_sql("ALTER TABLE webhook_events ADD COLUMN event_key VARCHAR(128)")
        if "is_duplicate" not in columns:
            conn.exec_driver_sql("ALTER TABLE webhook_events ADD COLUMN is_duplicate INTEGER NOT NULL DEFAULT 0")
        lead_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(lead_contacts)").fetchall()
        }
        optional_lead_columns = {
            "display_name": "ALTER TABLE lead_contacts ADD COLUMN display_name VARCHAR(255)",
            "avatar_url": "ALTER TABLE lead_contacts ADD COLUMN avatar_url TEXT",
            "phone": "ALTER TABLE lead_contacts ADD COLUMN phone VARCHAR(64)",
            "wechat": "ALTER TABLE lead_contacts ADD COLUMN wechat VARCHAR(128)",
            "lead_status": "ALTER TABLE lead_contacts ADD COLUMN lead_status VARCHAR(64)",
            "assignee": "ALTER TABLE lead_contacts ADD COLUMN assignee VARCHAR(128)",
            "remark": "ALTER TABLE lead_contacts ADD COLUMN remark TEXT",
            "lead_channel": "ALTER TABLE lead_contacts ADD COLUMN lead_channel VARCHAR(128)",
            "lead_type": "ALTER TABLE lead_contacts ADD COLUMN lead_type VARCHAR(128)",
            "tags": "ALTER TABLE lead_contacts ADD COLUMN tags TEXT",
            "last_interaction_record": "ALTER TABLE lead_contacts ADD COLUMN last_interaction_record TEXT",
        }
        for column_name, ddl in optional_lead_columns.items():
            if column_name not in lead_columns:
                conn.exec_driver_sql(ddl)
        auth_callback_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(auth_callback_records)").fetchall()
        }
        optional_auth_callback_columns = {
            "open_id": "ALTER TABLE auth_callback_records ADD COLUMN open_id VARCHAR(255)",
            "nick_name": "ALTER TABLE auth_callback_records ADD COLUMN nick_name VARCHAR(255)",
            "avatar": "ALTER TABLE auth_callback_records ADD COLUMN avatar TEXT",
        }
        for column_name, ddl in optional_auth_callback_columns.items():
            if column_name not in auth_callback_columns:
                conn.exec_driver_sql(ddl)
        task_tables = {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "aigc_video_tasks" in task_tables:
            task_columns = {
                row[1]
                for row in conn.exec_driver_sql("PRAGMA table_info(aigc_video_tasks)").fetchall()
            }
            optional_task_columns = {
                "result_cover_url": "ALTER TABLE aigc_video_tasks ADD COLUMN result_cover_url TEXT",
                "source": "ALTER TABLE aigc_video_tasks ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'mock'",
            }
            for column_name, ddl in optional_task_columns.items():
                if column_name not in task_columns:
                    conn.exec_driver_sql(ddl)


def get_configured_auth_payload() -> dict[str, Any]:
    if not PUBLIC_BASE_URL:
        raise HTTPException(400, "PUBLIC_BASE_URL is not configured")
    if not AUTH_REDIRECT_URL:
        raise HTTPException(400, "AUTH_REDIRECT_URL is not configured")
    if DY_MAIN_ACCOUNT_ID <= 0:
        raise HTTPException(400, "DY_MAIN_ACCOUNT_ID is not configured")
    if not DY_ACCOUNT_NAME:
        raise HTTPException(400, "DY_ACCOUNT_NAME is not configured")

    payload = {
        "main_account_id": DY_MAIN_ACCOUNT_ID,
        "account_name": DY_ACCOUNT_NAME,
        "auth_redirect_url": AUTH_REDIRECT_URL,
        "callback_url": f"{PUBLIC_BASE_URL.rstrip('/')}/webhook/douyin",
    }
    if DY_CALLBACK_EVENTS:
        payload["callback_event"] = DY_CALLBACK_EVENTS
    return payload


def upsert_conversation_summary(
    session: Session,
    *,
    conversation_short_id: str,
    lead_open_id: str,
    account_open_id: str | None,
    display_name: str | None,
    avatar_url: str | None,
    latest_event: str | None,
    latest_message_type: str | None,
    latest_message_text: str | None,
    latest_message_time: str | None,
) -> Conversation:
    conversation = (
        session.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        conversation = Conversation(
            conversation_short_id=conversation_short_id,
            lead_open_id=lead_open_id,
            account_open_id=account_open_id,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        session.add(conversation)

    conversation.lead_open_id = lead_open_id
    conversation.account_open_id = account_open_id
    conversation.display_name = display_name or conversation.display_name
    conversation.avatar_url = avatar_url or conversation.avatar_url
    conversation.latest_event = latest_event
    conversation.latest_message_type = latest_message_type
    conversation.latest_message_text = latest_message_text or conversation.latest_message_text
    conversation.latest_message_time = latest_message_time or conversation.latest_message_time
    conversation.updated_at = now_iso()
    session.flush()
    return conversation


def persist_local_outbound_message(
    session: Session,
    *,
    conversation_short_id: str,
    sender_open_id: str,
    receiver_open_id: str,
    message_text: str | None,
    server_message_id: str | None,
) -> Message:
    message = Message(
        conversation_short_id=conversation_short_id,
        server_message_id=server_message_id,
        sender_open_id=sender_open_id,
        receiver_open_id=receiver_open_id,
        direction="outbound",
        message_type="text",
        message_text=message_text,
        create_time=str(int(time.time() * 1000)),
        is_read=1,
        raw_content=json.dumps({"text": message_text}, ensure_ascii=False),
        created_at=now_iso(),
    )
    session.add(message)
    session.flush()
    return message


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    run_startup_migrations()


@app.exception_handler(UpstreamApiError)
def handle_upstream_api_error(_: Request, exc: UpstreamApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": -1,
            "msg": exc.message,
            "error_type": exc.error_type,
            "upstream_status": exc.upstream_status,
            "upstream_response": exc.response_text,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/douyin")
async def douyin_webhook(
    request: Request,
    _: None = Depends(verify_signature),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = await request.json()
    logger.info("webhook payload accepted path=%s payload=%s", request.url.path, json.dumps(payload, ensure_ascii=False)[:4000])
    event_key = build_event_key(payload)
    existing_event = find_existing_event_by_key(db, event_key)
    is_duplicate = existing_event is not None

    event = persist_event(db, payload, event_key=event_key, is_duplicate=is_duplicate)
    lead = upsert_lead_contact(db, payload)
    conversation = upsert_conversation(db, payload, lead)
    message = None
    if not is_duplicate:
        message = persist_message(db, payload, conversation)
        create_follow_record(
            db,
            lead_open_id=lead.open_id,
            conversation_short_id=conversation.conversation_short_id if conversation else None,
            action_type="webhook_event",
            content=lead.last_interaction_record,
            operator_name="system",
        )

    response = {
        "code": 0,
        "msg": "success",
        "data": {
            "event_id": event.id,
            "lead_id": lead.id,
            "event": lead.latest_event,
            "open_id": lead.open_id,
            "event_key": event_key,
            "is_duplicate": is_duplicate,
            "conversation_id": conversation.conversation_short_id if conversation else None,
            "message_id": message.id if message else None,
        },
    }
    logger.info("webhook processed path=%s response=%s", request.url.path, json.dumps(response, ensure_ascii=False))
    return response


@app.get("/leads")
def list_leads(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    lead_status: str | None = None,
    assignee: str | None = None,
    tag: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(LeadContact)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (LeadContact.display_name.like(like))
            | (LeadContact.open_id.like(like))
            | (LeadContact.phone.like(like))
        )
    if lead_status:
        query = query.filter(LeadContact.lead_status == lead_status)
    if assignee:
        query = query.filter(LeadContact.assignee == assignee)
    leads = query.order_by(LeadContact.id.desc()).all()
    if tag:
        leads = [item for item in leads if tag in ((item.tags or "").split(",") if item.tags else [])]
    if start_time is not None or end_time is not None:
        leads = [item for item in leads if in_millis_range(item.latest_active_time, start_time, end_time)]
    total = len(leads)
    start_index = max((page - 1) * page_size, 0)
    end_index = start_index + page_size
    leads = leads[start_index:end_index]
    items = [
        {
            "id": item.id,
            "open_id": item.open_id,
            "display_name": item.display_name,
            "avatar_url": item.avatar_url,
            "phone": item.phone,
            "wechat": item.wechat,
            "account_open_id": item.account_open_id,
            "latest_event": item.latest_event,
            "latest_message_type": item.latest_message_type,
            "conversation_short_id": item.conversation_short_id,
            "server_message_id": item.server_message_id,
            "latest_scene": item.latest_scene,
            "first_active_time": item.first_active_time,
            "latest_active_time": item.latest_active_time,
            "lead_status": item.lead_status,
            "assignee": item.assignee,
            "remark": item.remark,
            "lead_channel": item.lead_channel,
            "lead_type": item.lead_type,
            "tags": (item.tags or "").split(",") if item.tags else [],
            "last_interaction_record": item.last_interaction_record,
        }
        for item in leads
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/events")
def list_events(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    events = db.query(WebhookEvent).order_by(WebhookEvent.id.desc()).all()
    return [
        {
            "id": item.id,
            "event": item.event,
            "from_user_id": item.from_user_id,
            "to_user_id": item.to_user_id,
            "conversation_short_id": item.conversation_short_id,
            "server_message_id": item.server_message_id,
            "message_type": item.message_type,
            "create_time": item.create_time,
            "event_key": item.event_key,
            "is_duplicate": bool(item.is_duplicate),
            "created_at": item.created_at,
        }
        for item in events
    ]


@app.get("/api-call-logs")
def list_api_call_logs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    logs = db.query(ApiCallLog).order_by(ApiCallLog.id.desc()).all()
    return [
        {
            "id": item.id,
            "api_path": item.api_path,
            "request_timestamp": item.request_timestamp,
            "http_status": item.http_status,
            "response_body": item.response_body,
            "error_type": item.error_type,
            "error_message": item.error_message,
            "created_at": item.created_at,
        }
        for item in logs
    ]


@app.get("/aigc/video-tasks")
def list_aigc_video_tasks(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    tasks = db.query(AigcVideoTask).order_by(AigcVideoTask.id.desc()).all()
    return [serialize_aigc_task(item) for item in tasks]


@app.post("/aigc/materials/upload")
def upload_aigc_material(body: AigcPassthroughRequest) -> dict[str, Any]:
    if AIGC_MOCK_ENABLED:
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "element_id": f"mock_element_{int(time.time() * 1000)}",
                "status": "uploaded",
                "payload": body.payload,
            },
        }
    return call_aigc_upstream_post(AIGC_UPLOAD_ELEMENT_PATH, body.payload)


@app.post("/review/suggestions")
def get_review_suggestions(body: ReviewPassthroughRequest) -> dict[str, Any]:
    if REVIEW_MOCK_ENABLED:
        return make_mock_review_response("suggestions", body.payload)
    return call_review_upstream(method="GET", path=REVIEW_SUGGESTIONS_PATH, payload=body.payload)


@app.post("/review/cross-account")
def get_review_cross_account(body: ReviewPassthroughRequest) -> dict[str, Any]:
    if REVIEW_MOCK_ENABLED:
        return make_mock_review_response("cross_account", body.payload)
    return call_review_upstream(method="POST", path=REVIEW_CROSS_ACCOUNT_PATH, payload=body.payload)


@app.post("/review/adopt-task")
def create_review_adopt_task(body: ReviewPassthroughRequest) -> dict[str, Any]:
    if REVIEW_MOCK_ENABLED:
        return make_mock_review_response("adopt_create", body.payload)
    return call_review_upstream(method="POST", path=REVIEW_ADOPT_CREATE_PATH, payload=body.payload)


@app.post("/review/adopt-task/result")
def get_review_adopt_task_result(body: ReviewPassthroughRequest) -> dict[str, Any]:
    if REVIEW_MOCK_ENABLED:
        return make_mock_review_response("adopt_result", body.payload)
    return call_review_upstream(method="GET", path=REVIEW_ADOPT_RESULT_PATH, payload=body.payload)


@app.post("/aigc/video-tasks")
def create_aigc_video_task(
    body: AigcVideoTaskCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = build_aigc_payload(body)
    task_id = f"aigc_{int(time.time() * 1000)}"
    source = "mock" if AIGC_MOCK_ENABLED else "upstream"

    if AIGC_MOCK_ENABLED:
        response = make_mock_aigc_response(task_id, body)
    else:
        response = create_aigc_task_via_upstream(payload)
        data = response.get("data") if isinstance(response, dict) else None
        task_id = (data or {}).get("task_id") or task_id

    data = response.get("data") if isinstance(response, dict) else None
    task = persist_aigc_video_task(
        db,
        task_id=task_id,
        task_type=body.task_type,
        title=body.title,
        prompt=body.prompt,
        script=body.script,
        product_name=body.product_name,
        selling_points=body.selling_points,
        material_urls=body.material_urls,
        image_urls=body.image_urls,
        request_body=payload,
        status=(data or {}).get("status") or "queued",
        progress=int((data or {}).get("progress") or 0),
        response_body=response if isinstance(response, dict) else None,
        result_video_url=(data or {}).get("video_url") or (data or {}).get("result_video_url"),
        result_cover_url=(data or {}).get("cover_url") or (data or {}).get("result_cover_url"),
        error_message=None,
        source=source,
    )
    return {"code": 0, "msg": "success", "data": serialize_aigc_task(task)}


@app.get("/aigc/video-tasks/{task_id}")
def get_aigc_video_task(task_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    task = db.query(AigcVideoTask).filter(AigcVideoTask.task_id == task_id).one_or_none()
    if task is None:
        raise HTTPException(404, "AIGC task not found")
    return {"code": 0, "msg": "success", "data": serialize_aigc_task(task)}


@app.post("/aigc/video-tasks/{task_id}/refresh")
def refresh_aigc_video_task(task_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    task = db.query(AigcVideoTask).filter(AigcVideoTask.task_id == task_id).one_or_none()
    if task is None:
        raise HTTPException(404, "AIGC task not found")

    if task.source == "mock":
        response = {
            "code": 0,
            "msg": "success",
            "data": {
                "task_id": task.task_id,
                "status": "succeeded",
                "progress": 100,
                "video_url": task.result_video_url,
                "cover_url": task.result_cover_url,
            },
        }
    else:
        response = query_aigc_task_via_upstream(task.task_id)

    task = sync_aigc_task_from_response(task, response, db)
    return {"code": 0, "msg": "success", "data": serialize_aigc_task(task)}


@app.get("/auth-callback-records")
def list_auth_callback_records(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    records = db.query(AuthCallbackRecord).order_by(AuthCallbackRecord.id.desc()).all()
    return [
        {
            "id": item.id,
            "code": item.code,
            "auth_code": item.auth_code,
            "state": item.state,
            "error": item.error,
            "open_id": item.open_id,
            "nick_name": item.nick_name,
            "avatar": item.avatar,
            "raw_query": item.raw_query,
            "callback_url": item.callback_url,
            "created_at": item.created_at,
        }
        for item in records
    ]


@app.post("/auth-callback-records")
def create_auth_callback_record(
    body: AuthCallbackSaveRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    record = persist_auth_callback_record(db, body)
    token_record = None
    if body.code:
        token_record = exchange_code_for_access_token(body.code, callback_record_id=record.id)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "id": record.id,
            "token_record_id": token_record.id if token_record else None,
        },
    }


@app.post("/douyin/list-bind-info")
def list_bind_info(body: BindInfoRequest) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    return signed_post("/list_bind_info", payload)


@app.get("/auth-token-records")
def list_auth_token_records(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    records = db.query(AuthTokenRecord).order_by(AuthTokenRecord.id.desc()).all()
    return [
        {
            "id": item.id,
            "callback_record_id": item.callback_record_id,
            "open_id": item.open_id,
            "scope": item.scope,
            "status": item.status,
            "error_code": item.error_code,
            "error_message": item.error_message,
            "expires_in": item.expires_in,
            "refresh_expires_in": item.refresh_expires_in,
            "access_token_expires_at": item.access_token_expires_at,
            "refresh_token_expires_at": item.refresh_token_expires_at,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in records
    ]


@app.get("/auth-status")
def get_auth_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    latest_callback = db.query(AuthCallbackRecord).order_by(AuthCallbackRecord.id.desc()).first()
    latest_token = db.query(AuthTokenRecord).order_by(AuthTokenRecord.id.desc()).first()

    bind_item = None
    if latest_callback and latest_callback.open_id and DY_MAIN_ACCOUNT_ID > 0:
        try:
            result = signed_post(
                "/list_bind_info",
                {
                    "main_account_id": DY_MAIN_ACCOUNT_ID,
                    "page_num": 1,
                    "page_size": 10,
                    "name_or_open_id": latest_callback.open_id,
                },
            )
            bind_list = ((result or {}).get("data") or {}).get("bind_list") or []
            bind_item = next((item for item in bind_list if item.get("open_id") == latest_callback.open_id), None)
        except Exception:
            bind_item = None

    return {
        "code": 0,
        "msg": "success",
        "data": build_bind_auth_status(latest_callback, bind_item, latest_token),
    }


@app.get("/dashboard/lead-stats")
def dashboard_lead_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    leads = db.query(LeadContact).all()
    total = len(leads)
    pending = sum(1 for item in leads if (item.lead_status or "pending") == "pending")
    following = sum(1 for item in leads if (item.lead_status or "") == "following")
    closed = sum(1 for item in leads if (item.lead_status or "") == "closed")
    unread_conversations = db.query(Conversation).filter(Conversation.unread_count > 0).count()
    unread_messages = sum(item.unread_count or 0 for item in db.query(Conversation).all())
    return {
        "total_leads": total,
        "pending_leads": pending,
        "following_leads": following,
        "closed_leads": closed,
        "unread_conversations": unread_conversations,
        "unread_messages": unread_messages,
    }


@app.get("/conversations")
def list_conversations(
    keyword: str | None = None,
    unread_only: bool = False,
    start_time: int | None = None,
    end_time: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    query = db.query(Conversation)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Conversation.display_name.like(like))
            | (Conversation.lead_open_id.like(like))
            | (Conversation.latest_message_text.like(like))
        )
    if unread_only:
        query = query.filter(Conversation.unread_count > 0)
    conversations = query.order_by(Conversation.is_pinned.desc(), Conversation.id.desc()).all()
    if start_time is not None or end_time is not None:
        conversations = [
            item for item in conversations if in_millis_range(item.latest_message_time, start_time, end_time)
        ]
    return [
        {
            "id": item.id,
            "conversation_short_id": item.conversation_short_id,
            "lead_open_id": item.lead_open_id,
            "account_open_id": item.account_open_id,
            "display_name": item.display_name,
            "avatar_url": item.avatar_url,
            "latest_event": item.latest_event,
            "latest_message_type": item.latest_message_type,
            "latest_message_text": item.latest_message_text,
            "latest_message_time": item.latest_message_time,
            "unread_count": item.unread_count,
            "is_pinned": bool(item.is_pinned),
            "is_closed": bool(item.is_closed),
        }
        for item in conversations
    ]


@app.get("/conversations/unread-summary")
def conversation_unread_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    conversations = db.query(Conversation).all()
    return {
        "unread_conversations": sum(1 for item in conversations if (item.unread_count or 0) > 0),
        "unread_messages": sum(item.unread_count or 0 for item in conversations),
    }


@app.get("/conversations/{conversation_short_id}/messages")
def get_conversation_messages(conversation_short_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    messages = (
        db.query(Message)
        .filter(Message.conversation_short_id == conversation_short_id)
        .order_by(Message.id.asc())
        .all()
    )
    return [
        {
            "id": item.id,
            "conversation_short_id": item.conversation_short_id,
            "server_message_id": item.server_message_id,
            "sender_open_id": item.sender_open_id,
            "receiver_open_id": item.receiver_open_id,
            "direction": item.direction,
            "message_type": item.message_type,
            "message_text": item.message_text,
            "create_time": item.create_time,
            "is_read": bool(item.is_read),
        }
        for item in messages
    ]


@app.post("/conversations/{conversation_short_id}/read")
def mark_conversation_read(conversation_short_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    conversation.unread_count = 0
    db.query(Message).filter(Message.conversation_short_id == conversation_short_id).update(
        {"is_read": 1},
        synchronize_session=False,
    )
    return {"code": 0, "msg": "success"}


@app.get("/quick-replies")
def list_quick_replies(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    items = db.query(QuickReply).order_by(QuickReply.id.desc()).all()
    return [
        {
            "id": item.id,
            "title": item.title,
            "content": item.content,
            "created_at": item.created_at,
        }
        for item in items
    ]


@app.post("/quick-replies")
def create_quick_reply(body: QuickReplyRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = QuickReply(title=body.title, content=body.content, created_at=now_iso())
    db.add(item)
    db.flush()
    return {"code": 0, "msg": "success", "data": {"id": item.id}}


@app.get("/leads/{lead_open_id}/follow-records")
def get_lead_follow_records(lead_open_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    records = (
        db.query(LeadFollowRecord)
        .filter(LeadFollowRecord.lead_open_id == lead_open_id)
        .order_by(LeadFollowRecord.id.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "lead_open_id": item.lead_open_id,
            "conversation_short_id": item.conversation_short_id,
            "action_type": item.action_type,
            "content": item.content,
            "operator_name": item.operator_name,
            "created_at": item.created_at,
        }
        for item in records
    ]


@app.post("/leads/{lead_open_id}/assign")
def assign_lead(lead_open_id: str, body: LeadAssignRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    lead = db.query(LeadContact).filter(LeadContact.open_id == lead_open_id).one_or_none()
    if lead is None:
        raise HTTPException(404, "Lead not found")
    lead.assignee = body.assignee
    if not lead.lead_status:
        lead.lead_status = "pending"
    create_follow_record(
        db,
        lead_open_id=lead.open_id,
        conversation_short_id=lead.conversation_short_id,
        action_type="assign",
        content=f"分配给 {body.assignee}",
        operator_name=body.assignee,
    )
    return {"code": 0, "msg": "success"}


@app.post("/leads/{lead_open_id}/follow")
def follow_lead(lead_open_id: str, body: LeadFollowRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    lead = db.query(LeadContact).filter(LeadContact.open_id == lead_open_id).one_or_none()
    if lead is None:
        raise HTTPException(404, "Lead not found")
    lead.lead_status = "following"
    lead.remark = body.content
    create_follow_record(
        db,
        lead_open_id=lead.open_id,
        conversation_short_id=lead.conversation_short_id,
        action_type=body.action_type,
        content=body.content,
        operator_name=body.operator_name,
    )
    return {"code": 0, "msg": "success"}


@app.post("/leads/{lead_open_id}/tags")
def update_lead_tags(lead_open_id: str, body: LeadTagRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    lead = db.query(LeadContact).filter(LeadContact.open_id == lead_open_id).one_or_none()
    if lead is None:
        raise HTTPException(404, "Lead not found")
    lead.tags = ",".join(body.tags)
    create_follow_record(
        db,
        lead_open_id=lead.open_id,
        conversation_short_id=lead.conversation_short_id,
        action_type="tag_update",
        content=f"标签更新为: {', '.join(body.tags)}",
        operator_name="system",
    )
    return {"code": 0, "msg": "success"}


@app.get("/leads/export")
def export_leads(
    keyword: str | None = None,
    lead_status: str | None = None,
    assignee: str | None = None,
    tag: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    result = list_leads(
        page=1,
        page_size=100000,
        keyword=keyword,
        lead_status=lead_status,
        assignee=assignee,
        tag=tag,
        start_time=start_time,
        end_time=end_time,
        db=db,
    )
    return result["items"]


@app.post("/conversations/{conversation_short_id}/pin")
def pin_conversation(conversation_short_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    conversation.is_pinned = 1
    conversation.updated_at = now_iso()
    return {"code": 0, "msg": "success"}


@app.post("/conversations/{conversation_short_id}/unpin")
def unpin_conversation(conversation_short_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    conversation.is_pinned = 0
    conversation.updated_at = now_iso()
    return {"code": 0, "msg": "success"}


@app.post("/conversations/{conversation_short_id}/close")
def close_conversation(conversation_short_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    conversation.is_closed = 1
    conversation.updated_at = now_iso()
    return {"code": 0, "msg": "success"}


@app.post("/conversations/{conversation_short_id}/open")
def open_conversation(conversation_short_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    conversation.is_closed = 0
    conversation.updated_at = now_iso()
    return {"code": 0, "msg": "success"}


@app.post("/douyin/send-msg")
def send_msg(body: SendMsgRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    result = signed_post("/send_msg", payload)
    if body.conversation_id:
        lead = (
            db.query(LeadContact)
            .filter(LeadContact.conversation_short_id == body.conversation_id)
            .one_or_none()
        )
        display_name = lead.display_name if lead else None
        avatar_url = lead.avatar_url if lead else None
        upsert_conversation_summary(
            db,
            conversation_short_id=body.conversation_id,
            lead_open_id=body.to_user_id,
            account_open_id=body.from_user_id,
            display_name=display_name,
            avatar_url=avatar_url,
            latest_event="im_send_msg",
            latest_message_type="text",
            latest_message_text=body.content,
            latest_message_time=str(int(time.time() * 1000)),
        )
        persist_local_outbound_message(
            db,
            conversation_short_id=body.conversation_id,
            sender_open_id=body.from_user_id,
            receiver_open_id=body.to_user_id,
            message_text=body.content,
            server_message_id=(result.get("data") or {}).get("msg_id") if isinstance(result, dict) else None,
        )
    return result


@app.post("/douyin/get-auth-url")
def get_auth_url(body: AuthUrlRequest) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    return signed_post("/get_aweme_auth_url", payload)


@app.post("/douyin/get-auth-url/configured")
def get_auth_url_from_config() -> dict[str, Any]:
    payload = get_configured_auth_payload()
    return signed_post("/get_aweme_auth_url", payload)


@app.post("/douyin/upload-image")
def upload_image(body: UploadImageRequest) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    return signed_post("/upload_image_file", payload)


@app.post("/douyin/download-resource")
def download_resource(body: DownloadResourceRequest) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    return signed_post("/download_resource", payload)


@app.post("/leads/send-message")
def send_message_to_lead(body: SendLeadMessageRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    lead = db.query(LeadContact).filter(LeadContact.open_id == body.lead_open_id).one_or_none()
    if lead is None:
        raise HTTPException(404, "Lead not found")

    payload = {
        "main_account_id": body.main_account_id,
        "from_user_id": body.from_user_id,
        "to_user_id": body.lead_open_id,
        "content": body.content,
        "image_id": body.image_id,
        "conversation_id": lead.conversation_short_id,
        "msg_id": lead.server_message_id,
        "scene": body.scene,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    result = signed_post("/send_msg", payload)
    if lead.conversation_short_id:
        upsert_conversation_summary(
            db,
            conversation_short_id=lead.conversation_short_id,
            lead_open_id=lead.open_id,
            account_open_id=body.from_user_id,
            display_name=lead.display_name,
            avatar_url=lead.avatar_url,
            latest_event="im_send_msg",
            latest_message_type="text",
            latest_message_text=body.content,
            latest_message_time=str(int(time.time() * 1000)),
        )
        persist_local_outbound_message(
            db,
            conversation_short_id=lead.conversation_short_id,
            sender_open_id=body.from_user_id,
            receiver_open_id=lead.open_id,
            message_text=body.content,
            server_message_id=(result.get("data") or {}).get("msg_id") if isinstance(result, dict) else None,
        )
    return result


@app.post("/conversations/{conversation_short_id}/messages")
def send_conversation_message(
    conversation_short_id: str,
    body: ConversationSendMessageRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.conversation_short_id == conversation_short_id)
        .one_or_none()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")

    payload = {
        "main_account_id": body.main_account_id,
        "from_user_id": body.from_user_id,
        "to_user_id": conversation.lead_open_id,
        "content": body.content,
        "image_id": body.image_id,
        "conversation_id": conversation_short_id,
        "scene": body.scene,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    result = signed_post("/send_msg", payload)
    upsert_conversation_summary(
        db,
        conversation_short_id=conversation_short_id,
        lead_open_id=conversation.lead_open_id,
        account_open_id=body.from_user_id,
        display_name=conversation.display_name,
        avatar_url=conversation.avatar_url,
        latest_event="im_send_msg",
        latest_message_type="text",
        latest_message_text=body.content,
        latest_message_time=str(int(time.time() * 1000)),
    )
    persist_local_outbound_message(
        db,
        conversation_short_id=conversation_short_id,
        sender_open_id=body.from_user_id,
        receiver_open_id=conversation.lead_open_id,
        message_text=body.content,
        server_message_id=(result.get("data") or {}).get("msg_id") if isinstance(result, dict) else None,
    )
    return result
