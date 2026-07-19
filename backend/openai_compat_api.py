"""
OpenAI-compatible API endpoint for OpenAvatarChat integration.

Exposes /v1/chat/completions with SSE streaming so OpenAvatarChat's
LLMOpenAICompatible handler can use TourAI's RAG + DeepSeek backend directly.

Usage:
    This module is auto-imported by main.py. No additional config needed.
"""

import json
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import CONFIG
from rag_system import get_retriever

router = APIRouter(prefix="/v1", tags=["openai-compat"])


# --------------- OpenAI-compatible models ---------------

class ChatMessage(BaseModel):
    role: str
    content: str | list[dict] = ""


class ChatCompletionRequest(BaseModel):
    model: str = "tourai-guide"
    messages: list[ChatMessage]
    stream: bool = True
    stream_options: Optional[dict] = None
    temperature: float = 0.7
    max_tokens: int = 2048


# --------------- helpers ---------------

def _extract_user_text(messages: list[ChatMessage]) -> tuple[str, list[dict]]:
    """Extract the last user message and build conversation context."""
    system_prompt = ""
    history = []
    last_user = ""

    for msg in messages:
        if msg.role == "system":
            system_prompt = msg.content if isinstance(msg.content, str) else str(msg.content)
        elif msg.role == "user":
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            last_user = content
            history.append({"role": "user", "content": content})
        elif msg.role == "assistant":
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            history.append({"role": "assistant", "content": content})

    return last_user, history


def _build_prompt(user_text: str, system_prompt: str) -> str:
    """Build the full prompt for DeepSeek with RAG context."""
    # Try RAG retrieval
    rag_context = ""
    try:
        retriever = get_retriever()
        rag_result = retriever.retrieve(user_text, top_k=5)
        if rag_result.get("docs") and not rag_result.get("below_threshold"):
            rag_context = "\n---\n".join(
                doc.page_content for doc in rag_result["docs"]
            )
    except Exception:
        pass

    if system_prompt:
        base_prompt = system_prompt
    else:
        base_prompt = (
            "你是一个专业的景区导览数字人，名叫小僧。请用口语化的方式回答游客的问题。\n"
            "要求：简洁生动、回答在2-4句内、不含markdown格式。"
        )

    if rag_context:
        return (
            f"{base_prompt}\n\n"
            f"【参考资料】：\n{rag_context}\n\n"
            f"【游客问题】：{user_text}\n\n"
            f"请基于参考资料用口语化方式回答（2-4句话）："
        )
    else:
        return f"{base_prompt}\n\n【游客问题】：{user_text}\n\n请用口语化方式回答（2-4句话）："


# --------------- endpoint ---------------

@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest, req: Request):
    """
    OpenAI-compatible chat completions with SSE streaming.

    Used by OpenAvatarChat's LLMOpenAICompatible handler to connect to TourAI.
    """
    user_text, history = _extract_user_text(request.messages)

    if not user_text:
        raise HTTPException(status_code=400, detail="No user message found")

    system_prompt = ""
    for msg in request.messages:
        if msg.role == "system":
            system_prompt = msg.content if isinstance(msg.content, str) else str(msg.content)
            break

    prompt = _build_prompt(user_text, system_prompt)
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    model_name = request.model

    llm = CONFIG.create_llm()

    if not request.stream:
        full_text = ""
        async for chunk in llm.astream(prompt):
            token = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if token: full_text += token
        return {
            "id": request_id, "object": "chat.completion", "created": int(time.time()),
            "model": model_name,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": full_text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    async def event_generator():
        full_text = ""
        created = int(time.time())

        try:
            async for chunk in llm.astream(prompt):
                token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if not token:
                    continue
                full_text += token

                # OpenAI SSE chunk format
                chunk_data = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model_name,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": token},
                            "finish_reason": None,
                        }
                    ],
                }
                if request.stream_options and request.stream_options.get("include_usage"):
                    chunk_data["usage"] = None
                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

            # Final chunk with finish_reason
            final_chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            if request.stream_options and request.stream_options.get("include_usage"):
                final_chunk["usage"] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": f"抱歉，出了一点问题：{str(e)}"},
                        "finish_reason": "error",
                    }
                ],
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models")
async def list_models():
    """OpenAI-compatible model list."""
    return {
        "object": "list",
        "data": [
            {
                "id": "tourai-guide",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "tourai",
            }
        ],
    }
