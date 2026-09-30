from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx
import config

router = APIRouter(prefix="/api/llm", tags=["llm"])

# G15: baseUrl 白名单 + 可选 bearer 鉴权
# 默认包含 OpenAI/Claude/Moonshot 官方域。生产部署可通过
# CPDV_LLM_ALLOWED_BASES 环境变量追加自定义 baseUrl（CSV）。
_DEFAULT_BASES = (
    "https://api.openai.com/v1,"
    "https://api.anthropic.com/v1,"
    "https://api.moonshot.cn/v1,"
    "https://api.deepseek.com/v1,"
    "https://api.agnes-ai.cn/v1"
)
_env_bases = config._env_str("CPDV_LLM_ALLOWED_BASES", _DEFAULT_BASES)
ALLOWED_BASES = tuple(b.rstrip("/") for b in _env_bases.split(",") if b.strip())
# 鉴权 token（可选）：设置 CPDV_LLM_TOKEN 后，前端必须传 X-LLM-Token 头
REQUIRED_TOKEN = config._env_str("CPDV_LLM_TOKEN", "") or None


def _check_base(base_url: str) -> str:
    """校验 baseUrl 在白名单内（含子域匹配）。返回规范化后的 base_url。"""
    base = base_url.rstrip("/")
    for allowed in ALLOWED_BASES:
        if base == allowed or base.startswith(allowed + "/"):
            return base
    raise HTTPException(
        status_code=400,
        detail=f"baseUrl '{base_url}' 不在白名单。允许: {', '.join(ALLOWED_BASES)}",
    )


@router.post("/proxy")
async def proxy(request: Request):
    # G15: 可选 token 鉴权（开发环境不设 REQUIRED_TOKEN 则跳过）
    if REQUIRED_TOKEN:
        token = request.headers.get("X-LLM-Token", "")
        if token != REQUIRED_TOKEN:
            raise HTTPException(status_code=401, detail="X-LLM-Token 缺失或错误")

    body = await request.json()
    raw_base = body.get("baseUrl", "https://api.openai.com/v1")
    base_url = _check_base(raw_base)
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


@router.get("/config")
def llm_config():
    """返回给前端看自己能否用 LLM（避免前端静默失败）。"""
    return {
        "allowed_bases": list(ALLOWED_BASES),
        "auth_required": REQUIRED_TOKEN is not None,
    }
