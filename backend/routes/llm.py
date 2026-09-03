from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/proxy")
async def proxy(request: Request):
    body = await request.json()
    base_url = body.get("baseUrl", "https://api.openai.com/v1").rstrip("/")
    api_key = body.get("apiKey", "")
    payload = body.get("payload", {})
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async def gen():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{base_url}/chat/completions", headers=headers, json=payload
            ) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(gen(), media_type="text/event-stream")
