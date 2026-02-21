import asyncio
from functools import partial

from fastapi import APIRouter
from pydantic import BaseModel

from server.api_server.chat.chat_mgr import handle_chat

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@chat_router.post("/completions", response_model=ChatResponse)
async def chat_completions(req: ChatRequest):
    """对话补全接口。"""
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        partial(
            handle_chat,
            user_message=req.message,
            conversation_id=req.conversation_id,
        ),
    )
    return ChatResponse(**result)
