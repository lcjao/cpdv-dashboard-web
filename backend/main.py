from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import dashboard, analysis, bridges, llm, command, external_code, algorithm, ai_commands
from routes import signals as signals_routes
import ws
import config

app = FastAPI(title="CPDV Dashboard API")

# G14: CORS 白名单 + 收紧 methods/headers
# 浏览器规范禁止 allow_origins="*" + allow_credentials=True 同时使用，会被拒。
# 这里牺牲 wildcard，换成 env 控制的显式 origin 列表（默认 Vite dev server）。
# 生产部署时设置 CPDV_ALLOW_ORIGINS=https://your.domain 即可。
_origins_env = config._env_str(
    "CPDV_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
)
ALLOW_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,           # 现在 origin 是显式列表，可启用 credentials
    allow_methods=["GET", "POST"],     # 收紧：只看板用得到这两
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

app.include_router(dashboard.router)
app.include_router(analysis.router)
app.include_router(bridges.router)
app.include_router(llm.router)
app.include_router(command.router)
app.include_router(command._meta_router)  # G9: /api/command-meta
app.include_router(external_code.router)  # 外部代码文件操作
app.include_router(algorithm.router)  # 算法代码库看板 API
app.include_router(ai_commands.router)  # AI 命令系统
app.include_router(ws.router)
app.include_router(signals_routes.router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "name": "CPDV Dashboard API",
        "cors_origins": ALLOW_ORIGINS,
    }
