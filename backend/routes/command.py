"""命令分发：解析文本 → 调对应 service → 返回结构化结果。"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import config
from scheduler import parse_command, parse_params, validate_params
from services import (
    cpdv_service,
    predict_service,
    multi_crack_service,
    random_service,
    record_service,
    train_service,
    compare_service,
    evaluate_service,
)
from services.cpdv_service import DEFAULT_SIM
from data_loader import load_registry, load_dashboard_data
from ws import emit as emit_progress

router = APIRouter(prefix="/api/command", tags=["command"])


# G9: 命令元数据由 config.COMMAND_META 提供，单独路由挂在 /api/command-meta。
# 启动时前端一次拉取 → 缓存到内存 → 动态生成 TOOL_ROUTE / buildCpdvTools / QuickCommands。
_meta_router = APIRouter(prefix="/api", tags=["meta"])

# 危险命令黑名单：后端二次校验，双重保险
DANGEROUS_COMMANDS = {
    'delete_all_data',
    'reset_model',
    'shutdown',
    'purge_registry',
    'factory_reset',
}


@_meta_router.get("/command-meta")
def command_meta():
    return {
        "version": 1,
        "source": "config.COMMAND_META",
        "commands": config.get_command_meta(),
    }


class CmdReq(BaseModel):
    text: str
    bridge: Optional[str] = None
    bridge_b: Optional[str] = None   # 对比/差异类命令的第二个桥
    # 直接接受结构化参数（来自前端的 executeToolCalls 回填），与 parse_params(text) 合并
    params: Optional[dict] = None


def _resolve_bridge_id(name_or_id: Optional[str]) -> Optional[str]:
    """根据名称或 id 在 registry 中找桥，找不到则返回原值（让 service 抛错）。"""
    if not name_or_id:
        return None
    reg = load_registry()
    for b in reg.get("bridges", []):
        if b.get("id") == name_or_id or b.get("name") == name_or_id:
            return b.get("id") or name_or_id
    return name_or_id


def _check_dangerous(action: str) -> Optional[dict]:
    """检查是否为危险命令，若是返回错误响应。"""
    if action in DANGEROUS_COMMANDS:
        return {
            "action": action,
            "status": "error",
            "error": f"危险命令被拦截：{action}。该操作可能造成数据丢失或系统不可用，已禁止执行。",
        }
    return None


@router.post("")
async def execute_command(req: CmdReq, request: Request):
    parsed = parse_command(req.text)
    if not parsed:
        return {"action": "unknown", "text": req.text,
                "error": "未识别命令。请使用「看板总览/注册桥梁/计算CPDV/预测损伤/多裂缝预测/随机工况分析/对比/训练模型/刷新看板/记录实验」之一。"}
    action, full_text = parsed
    # 后端危险命令二次校验
    danger = _check_dangerous(action)
    if danger:
        return danger
    # 合并文本解析参数 + 结构化 params + 顶层 bridge
    text_params = parse_params(full_text)
    merged_params = {**text_params, **(req.params or {})}
    ok, msg = validate_params(merged_params)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    bridge_id = _resolve_bridge_id(req.bridge or merged_params.pop("bridge", None))

    # 通用结果容器：路由分发正确时总能带出 action + 已解析参数，便于前端排错
    ctx = {"action": action, "bridge_id": bridge_id}

    def _ok(extra: dict):
        return {**ctx, **extra}

    def _fail(e: Exception):
        # 不再 raise HTTPException——直接返回结构化错误，保留 action 字段
        return {
            **ctx,
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
            "stdout_tail": getattr(e, "args", [str(e)])[0][-1500:]
            if isinstance(getattr(e, "args", [None])[0], str) else "",
        }

    try:
        if action == "cpdv":
            depth = float(merged_params.pop("depth", 0.2))
            distances = merged_params.pop("distances", "5,10,15,20,25")
            if isinstance(distances, str):
                distances = [float(x) for x in distances.replace("，", ",").split(",") if x.strip()]
            # G20: 多裂缝模式 —— depths 与 distances 一一对应（如 distances=5,10,15 & depths=0.2,0.3,0.25）
            depths = merged_params.pop("depths", None)
            if depths is not None:
                if isinstance(depths, str):
                    depths = [float(x) for x in depths.replace("，", ",").split(",") if x.strip()]
                elif isinstance(depths, (int, float)):
                    depths = [float(depths)]
                else:
                    depths = [float(x) for x in depths]
                if len(depths) != len(distances):
                    raise ValueError(f"depths({len(depths)}) 数量必须与 distances({len(distances)}) 一致")
            bridge = bridge_id or "bridge_01"
            emit_progress("pipeline", "cpdv_start",
                          f"开始CPDV计算: bridge={bridge}, depth={depth}", percent=5,
                          bridge=bridge)
            emit_progress("cpdv", "preparing",
                          f"准备计算 {bridge} depth={depth} distances={distances}"
                          + (f" depths={depths}" if depths else ""),
                          percent=2.0, bridge=bridge, depth=depth, distances=distances)
            try:
                result = cpdv_service.compute_cpdv(
                    bridge, depth, distances, merged_params, config.DATA_DIR, depths=depths)
                emit_progress("pipeline", "cpdv_done",
                              f"CPDV计算完成: bridge={bridge}", percent=100,
                              bridge=bridge,
                              metrics={"n_signals": len(result.get("cpdv_signals", []))})
                emit_progress("cpdv", "done",
                              f"已计算 {bridge} CPDV (depth={depth})"
                              + (f", 多裂缝 {len(depths)} 条" if depths else ""),
                              percent=100.0, bridge=bridge,
                              stdout_lines=len((result.get("stdout") or "").splitlines()))
                return _ok({"depth": depth, "depths": depths, "distances": distances, **result, "need_refresh": True, "bridge_id": bridge_id})
            except Exception as e:
                emit_progress("pipeline", "cpdv_error", str(e)[:200], percent=0,
                              bridge=bridge)
                emit_progress("cpdv", "error", str(e)[:200], percent=0.0, bridge=bridge)
                raise

        if action == "predict":
            model = merged_params.pop("model", "outputs/models/cracknet.json")
            input_data = merged_params.pop("input_data", "outputs/data/verify_data.npz")
            try:
                result = predict_service.predict_single(model, input_data)
                return _ok({"model": model, "input_data": input_data, **result})
            except Exception as e:
                # predict_service 链路依赖仓库旧脚本，目前不可用——返回明确原因
                return _ok({
                    "model": model, "input_data": input_data,
                    "status": "unavailable",
                    "error": f"predict 链路不可用：{e}",
                    "hint": "单裂缝 NN/LSTM 模型脚本不在 CODE_ROOT；当前看板仅推荐使用 multi_crack（双头）模型。",
                })

        if action == "multi_crack":
            model = merged_params.pop("model", multi_crack_service.DEFAULT_MODEL)
            input_data = merged_params.pop("input_data", "outputs/data/multi_condition.npz")
            bridge_label = bridge_id or "default"
            try:
                emit_progress("pipeline", "multi_crack_start",
                              f"开始多裂缝预测: bridge={bridge_label}", percent=5,
                              bridge=bridge_label)
                result = multi_crack_service.predict_multi_crack(model, input_data, bridge_id=bridge_id)
                emit_progress("pipeline", "multi_crack_done",
                              f"多裂缝预测完成: bridge={bridge_label}", percent=100,
                              bridge=bridge_label,
                              metrics=result.get("prediction", {}))
                return _ok({"model": model, "input_data": input_data,
                            "bridge": bridge_id, **result, "need_refresh": True, "bridge_id": bridge_id})
            except Exception as e:
                emit_progress("pipeline", "multi_crack_error", str(e)[:200], percent=0,
                              bridge=bridge_label)
                return _ok({
                    "model": model, "input_data": input_data,
                    "status": "error", "error": f"{type(e).__name__}: {e}",
                })

        if action == "evaluate":
            model = merged_params.pop("model", evaluate_service.DEFAULT_MODEL)
            input_data = merged_params.pop("input_data", "outputs/data/multi_condition.npz")
            cls_threshold = float(merged_params.pop("cls_threshold", 0.3))
            match_cost = float(merged_params.pop("match_cost", 5.0))
            pos_threshold = float(merged_params.pop("pos_threshold", 0.0))
            bridge_label = bridge_id or "default"
            try:
                emit_progress("pipeline", "evaluate_start",
                              f"开始模型评估: bridge={bridge_label}", percent=5,
                              bridge=bridge_label)
                result = evaluate_service.evaluate_model(
                    bridge_id=bridge_id,
                    model=model,
                    input_data=input_data,
                    cls_threshold=cls_threshold,
                    match_cost=match_cost,
                    pos_threshold=pos_threshold,
                )
                emit_progress("pipeline", "evaluate_done",
                              f"模型评估完成: bridge={bridge_label}", percent=100,
                              bridge=bridge_label,
                              metrics=result.get("metrics", {}))
                return _ok({"model": model, "input_data": input_data, **result, "need_refresh": True, "bridge_id": bridge_id})
            except Exception as e:
                emit_progress("pipeline", "evaluate_error", str(e)[:200], percent=0,
                              bridge=bridge_label)
                return _ok({
                    "model": model, "input_data": input_data,
                    "status": "error", "error": f"{type(e).__name__}: {e}",
                })

        if action == "train_and_evaluate":
            model_type = merged_params.pop("model_type", "multi_crack")
            n_samples = int(merged_params.pop("n_samples", 10000))
            epochs = int(merged_params.pop("epochs", 30))
            phase1_epochs = merged_params.pop("phase1_epochs", None)
            if phase1_epochs is not None:
                phase1_epochs = int(phase1_epochs)
            phase2_epochs = merged_params.pop("phase2_epochs", None)
            if phase2_epochs is not None:
                phase2_epochs = int(phase2_epochs)
            regenerate = bool(merged_params.pop("regenerate", False))
            data = merged_params.pop("data", None)
            model = merged_params.pop("model", None)
            force = bool(merged_params.pop("force", False))
            # 评估参数
            cls_threshold = float(merged_params.pop("cls_threshold", 0.3))
            match_cost = float(merged_params.pop("match_cost", 5.0))
            pos_threshold = float(merged_params.pop("pos_threshold", 0.0))
            try:
                # 耗时预估：训练 + 评估
                train_est = max(20, int(epochs * 1.2))
                eval_est = 30
                total_est = train_est + eval_est
                if total_est > 120 and not force:
                    return _ok({
                        "model_type": model_type, "epochs": epochs,
                        "estimated_s": total_est,
                        "status": "needs_confirmation",
                        "hint": f"预计总耗时 ~{total_est}s（训练 {train_est}s + 评估 {eval_est}s）。"
                                f"如确认请加 force=true（实测 demo 用 epochs<=30）",
                    })
                # P0 修复：训练+评估必须指定 bridge
                if not bridge_id:
                    reg = load_registry()
                    bridges = reg.get("bridges", [])
                    if bridges:
                        bridge_id = bridges[0]["id"]
                        emit_progress("train_and_evaluate", "bridge_resolved",
                                      f"未指定桥梁，默认使用第一座: {bridge_id}", percent=1,
                                      bridge=bridge_id)
                    else:
                        return _ok({
                            "action": "train_and_evaluate", "status": "error",
                            "error": "无已注册桥梁，请先执行「注册桥梁」",
                        })
                emit_progress("train_and_evaluate", "train_start",
                              f"开始训练+评估，bridge={bridge_id}", percent=1,
                              bridge=bridge_id)
                # 1) 训练
                train_result = train_service.train_model(
                    bridge_id=bridge_id,
                    model_type=model_type, n_samples=n_samples,
                    data=data, model=model, epochs=epochs,
                    phase1_epochs=phase1_epochs, phase2_epochs=phase2_epochs,
                    regenerate=regenerate,
                    abort_check=lambda: request.is_disconnected(),
                )
                if train_result.get("error") or train_result.get("status") == "error":
                    return _ok({"action": "train_and_evaluate", "bridge_id": bridge_id,
                                "train_result": train_result,
                                "status": "train_failed", "error": train_result.get("error")})
                # 训练成功，用训练产出的模型路径做评估
                trained_model = train_result.get("model") or model
                # 2) 评估
                eval_result = evaluate_service.evaluate_model(
                    bridge_id=bridge_id,
                    model=trained_model,
                    input_data=data or "outputs/data/multi_condition.npz",
                    cls_threshold=cls_threshold,
                    match_cost=match_cost,
                    pos_threshold=pos_threshold,
                )
                # P0 修复：校验评估阶段 meta_written 必须非 null（_write_bridge_eval_meta 失败会抛异常）
                meta_written = eval_result.get("meta_written")
                if not meta_written:
                    raise RuntimeError("评估完成但 meta 未写回 registry（bridge 未注册或写入失败）")
                emit_progress("pipeline", "train_and_eval_done",
                              f"训练+评估完成: bridge={bridge_id}", percent=100,
                              bridge=bridge_id,
                              metrics=eval_result.get("metrics", {}))
                return _ok({
                    "train_result": train_result,
                    "eval_result": eval_result,
                    "meta_written": meta_written,
                    "need_refresh": True,
                    "bridge_id": bridge_id,
                })
            except Exception as e:
                emit_progress("pipeline", "train_and_eval_error", str(e)[:200], percent=0,
                              bridge=bridge_id)
                emit_progress("train_and_evaluate", "error", str(e)[:200], percent=0)
                return _ok({
                    "model_type": model_type, "status": "error",
                    "error": f"{type(e).__name__}: {e}",
                })

        if action == "random_condition":
            mode = merged_params.pop("mode", "single")
            n_samples = int(merged_params.pop("n_samples", 50))
            positions = merged_params.pop("positions", merged_params.pop("distances", "5,10,15,20"))
            if isinstance(positions, str):
                positions = [float(x) for x in positions.replace("，", ",").split(",") if x.strip()]
            bridge_label = bridge_id or "default"
            try:
                emit_progress("pipeline", "random_start",
                              f"开始随机工况分析: bridge={bridge_label}, n={n_samples}", percent=5,
                              bridge=bridge_label)
                result = random_service.random_condition(mode, n_samples, positions)
                emit_progress("pipeline", "random_done",
                              f"随机工况分析完成: bridge={bridge_label}", percent=100,
                              bridge=bridge_label)
                return _ok({"mode": mode, "n_samples": n_samples, "positions": positions, **result, "need_refresh": True, "bridge_id": bridge_id})
            except Exception as e:
                emit_progress("pipeline", "random_error", str(e)[:200], percent=0,
                              bridge=bridge_label)
                return _ok({
                    "mode": mode, "n_samples": n_samples, "positions": positions,
                    "status": "error", "error": f"{type(e).__name__}: {e}",
                })

        if action == "train":
            model_type = merged_params.pop("model_type", "multi_crack")
            n_samples = int(merged_params.pop("n_samples", 10000))
            epochs = int(merged_params.pop("epochs", 30))   # 默认改小，便于 <60s 完成
            phase1_epochs = merged_params.pop("phase1_epochs", None)
            if phase1_epochs is not None:
                phase1_epochs = int(phase1_epochs)
            phase2_epochs = merged_params.pop("phase2_epochs", None)
            if phase2_epochs is not None:
                phase2_epochs = int(phase2_epochs)
            regenerate = bool(merged_params.pop("regenerate", False))
            data = merged_params.pop("data", None)
            model = merged_params.pop("model", None)
            force = bool(merged_params.pop("force", False))
            try:
                # 耗时预估：>2 分钟要求 force=True 才执行（避免 AI 误调）
                est = max(20, int(epochs * 1.2))
                if est > 120 and not force:
                    return _ok({
                        "model_type": model_type, "epochs": epochs,
                        "estimated_s": est,
                        "status": "needs_confirmation",
                        "hint": f"预计耗时 ~{est}s（>{epochs*1.2:.0f}s/epoch）。"
                                f"如确认请加 force=true（实测 demo 用 epochs<=30）",
                    })
                # P0 修复：训练必须指定 bridge（写回 metrics 需要 bridge_id）
                # 若未指定，默认使用第一座已注册桥
                if not bridge_id:
                    reg = load_registry()
                    bridges = reg.get("bridges", [])
                    if bridges:
                        bridge_id = bridges[0]["id"]
                        emit_progress("train", "bridge_resolved",
                                      f"未指定桥梁，默认使用第一座: {bridge_id}", percent=1,
                                      bridge=bridge_id)
                    else:
                        return _ok({
                            "action": "train", "status": "error",
                            "error": "无已注册桥梁，请先执行「注册桥梁」",
                        })
                emit_progress("pipeline", "train_start",
                              f"开始训练: bridge={bridge_id}, epochs={epochs}", percent=5,
                              bridge=bridge_id, epochs=epochs)
                emit_progress("train", "bridge_resolved",
                              f"开始训练，bridge={bridge_id}", percent=1,
                              bridge=bridge_id)
                result = train_service.train_model(
                    bridge_id=bridge_id,
                    model_type=model_type, n_samples=n_samples,
                    data=data, model=model, epochs=epochs,
                    phase1_epochs=phase1_epochs, phase2_epochs=phase2_epochs,
                    regenerate=regenerate,
                    abort_check=lambda: request.is_disconnected(),
                )
                emit_progress("pipeline", "train_done",
                              f"训练完成: bridge={bridge_id}", percent=100,
                              bridge=bridge_id,
                              metrics=result.get("metrics", {}))
                return _ok({"model_type": model_type, **result, "need_refresh": True, "bridge_id": bridge_id})
            except Exception as e:
                emit_progress("pipeline", "train_error", str(e)[:200], percent=0,
                              bridge=bridge_id)
                emit_progress("train", "error", str(e)[:200], percent=0)
                return _ok({
                    "model_type": model_type, "status": "error",
                    "error": f"{type(e).__name__}: {e}",
                })

        if action == "overview" or action == "refresh":
            # 完整刷新：合并数据 + 信号数据 + 指标数据
            from data_loader import load_dashboard_merged, load_bridge_signals, load_registry, load_records
            import json as _json
            
            # 1. 加载合并的看板数据
            merged = load_dashboard_merged()
            
            # 2. 批量加载所有桥梁的信号数据
            reg = load_registry()
            bridges = reg.get("bridges", [])
            all_signals = {}
            for b in bridges:
                bid = b.get("id")
                signals = load_bridge_signals(bid)
                if signals:
                    all_signals[bid] = signals
            
            # 3. 加载实验记录
            all_records = load_records()
            
            # 4. 组装响应
            result = {
                "dashboard": merged,
                "signals": all_signals,
                "records": all_records[-50:] if all_records else [],  # 最近50条记录
                "bridge_count": len(bridges),
                "record_count": len(all_records),
                "generated": _json.dumps({"now": _json.__import__('datetime').datetime.now().isoformat()}) if hasattr(_json, '__import__') else None,
            }
            
            # 发射进度事件
            emit_progress("pipeline", "refresh_done", "刷新完成", percent=100)
            
            return _ok(result)

        if action == "list":
            bridges = load_registry().get("bridges", [])
            return _ok({"bridges": bridges})

        if action == "register":
            name = merged_params.pop("name", None) or bridge_id
            if not name:
                raise HTTPException(status_code=400, detail="缺少桥梁名。请使用「注册桥梁 <名称> [参数]」")
            reserved = {"bridge", "depth", "distances", "model", "input_data",
                        "mode", "n_samples", "positions", "epochs", "regenerate", "data"}
            clean = {k: v for k, v in merged_params.items() if k not in reserved}
            from routes.bridges import RegisterReq, register_bridge
            req2 = RegisterReq(name=name, params=clean or None)
            # 幂等注册：统一走 REST 端点的同名去重 + 持久计数器发号
            # （修复 LLM 路径旧逻辑 len(reg)+1 与 _next_id 撞号、重名桥追加重复项的根因）
            res = register_bridge(req2)
            return _ok({"bridge": res, "need_refresh": True, "bridge_id": res.get("id"),
                        "duplicated": res.get("duplicated", False),
                        "updated": res.get("updated", False)})

        if action == "record":
            # 「记录实验 [bridge_id] [...任意参数] [note=...]」
            # 关键设计：record 服务记录"用户本次实验的所有参数"，所以**不过滤**
            # depth/mv/epochs 等命令结构参数——它们本身就是用户想记的内容。
            # 只剥 meta 元字段（note/summary/action_type）让它们走专属通道。
            note = merged_params.pop("note", None) or merged_params.pop("summary", None)
            action_type = merged_params.pop("action_type", "cpdv")
            if isinstance(note, float):  # parse_params 误把 note 转成 float 时
                note = None
            params_only = dict(merged_params)   # 全部保留
            # 把 list 类型的 distances 等转回 list
            for k, v in params_only.items():
                if isinstance(v, str) and "," in v and v.replace(".", "").replace(",", "").replace("-", "").isdigit():
                    parts = [float(x) for x in v.replace("，", ",").split(",") if x.strip()]
                    if parts:
                        params_only[k] = parts
            rec = record_service.record_experiment(
                bridge_id=bridge_id or "unknown",
                action=action_type,
                params=params_only,
                result={},   # 当前仅做"参数记录"，result 留空给后续 predict/train 接
                note=note,
            )
            return _ok({
                "record": rec,
                "action_type": action_type,
                "params_recorded": list(params_only.keys()),
                "need_refresh": True,
                "bridge_id": bridge_id,
            })

        if action == "record_experiment":
            # 详细记录实验：支持完整的 type/protocol/bridge/params/metrics/note
            note = merged_params.pop("note", None)
            exp_type = merged_params.pop("type", merged_params.pop("action_type", "train"))
            protocol = merged_params.pop("protocol", None)
            exp_bridge = merged_params.pop("bridge", None)
            params = merged_params.pop("params", {})
            metrics = merged_params.pop("metrics", {})
            if isinstance(params, str):
                try:
                    import json
                    params = json.loads(params)
                except:
                    params = {}
            if isinstance(metrics, str):
                try:
                    import json
                    metrics = json.loads(metrics)
                except:
                    metrics = {}
            
            rec = record_service.record_experiment(
                bridge_id=exp_bridge or bridge_id or protocol or "unknown",
                action=exp_type,
                params=params,
                result=metrics,
                note=note,
            )
            return _ok({
                "record_id": rec.get("id"),
                "message": f"实验已记录: {rec.get('id')}",
                "record": rec,
                "need_refresh": True,
            })

        if action == "compare_models":
            model_a = merged_params.pop("model_a", None)
            model_b = merged_params.pop("model_b", None)
            bridge_a = merged_params.pop("bridge_a", None)
            bridge_b = merged_params.pop("bridge_b", None)
            
            if not (model_a and model_b):
                return _ok({
                    "status": "missing_params",
                    "hint": "请提供两个模型路径。格式: '对比模型 model_a=xxx model_b=yyy' 或参数 'model_a' / 'model_b'",
                })
            
            # 如果提供了 bridge，尝试从 registry 获取模型路径和指标
            # 这里简化处理，直接返回对比框架
            from services.compare_service import compare_bridges
            if bridge_a and bridge_b:
                result = compare_bridges(bridge_a, bridge_b)
                return _ok({**result, "need_refresh": True})
            
            # 直接模型路径对比（需要评估服务支持）
            return _ok({
                "model_a": {"path": model_a, "metrics": {}, "config": {}},
                "model_b": {"path": model_b, "metrics": {}, "config": {}},
                "comparison": {
                    "f1_diff": 0, "precision_diff": 0, "recall_diff": 0,
                    "position_mae_diff": 0, "depth_mae_diff": 0,
                    "winner": "tie",
                    "summary": "模型对比功能待完善，建议使用 evaluate 服务分别评估两模型后再对比",
                },
                "need_refresh": True,
            })

        if action == "compare":
            # 三种取参优先级：
            # 1. 结构化 params.bridge_a / bridge_b
            # 2. 「对比 A B」— text 里后两个 bridge 名/id
            # 3. req.bridge + req.bridge_b（前端 ExecuteTool 调用）
            import re
            a = (merged_params.pop("bridge_a", None) or
                 merged_params.pop("bridge1", None) or
                 merged_params.pop("a", None))
            b = (merged_params.pop("bridge_b", None) or
                 merged_params.pop("bridge2", None) or
                 merged_params.pop("b", None))
            if not (a and b):
                # text 里的两个候选：bridge_XX / "桥X" / 中文桥名
                cands = re.findall(r"bridge_\w+|[^\s,，]+桥[^\s,，]*|[^\s,，]\S{0,12}", full_text)
                # 过滤掉命令词本身
                kw_set = set(config.COMMANDS.keys()) | {"vs", "对比", "compare"}
                cands = [c for c in cands if c not in kw_set and len(c) >= 2]
                if len(cands) >= 2:
                    a, b = cands[0], cands[1]
                elif len(cands) == 1:
                    # 只识别到一个 — 用 req.bridge_b 兜底
                    a = a or cands[0]
            a = a or req.bridge
            b = b or getattr(req, "bridge_b", None)
            if not (a and b):
                return _ok({
                    "status": "missing_params",
                    "hint": "请提供两个桥梁名/id。格式："
                            "'对比 bridge_01 bridge_02' 或参数 'bridge_a' / 'bridge_b'",
                    "example": {"text": "对比 bridge_01 bridge_02"},
                })
            result = compare_service.compare_bridges(a, b)
            return _ok({**result, "need_refresh": True, "bridge_id": bridge_id})

        if action == "pipeline.execute":
            pipelines = merged_params.pop("pipelines", [])
            mode = merged_params.pop("mode", "quick")
            stages = merged_params.pop("stages", None)
            auto_sync = merged_params.pop("auto_sync_dashboard", True)
            # record_exp handled by pipeline_executor internally
            
            if not pipelines:
                return _ok({"status": "missing_params", "hint": "请提供 pipelines 参数，如 pipelines=pipeline_2_single_crack_bp"})
            
            from services.pipeline_executor import executor
            task_id = await executor.run_pipeline(
                pipelines=pipelines,
                mode=mode,
                stages=stages,
                progress_callback=lambda tid, stage, msg, pct: (
                    emit_progress("pipeline", stage, msg, percent=pct or 0, pipeline_id=pipelines[0] if pipelines else None)
                ),
                auto_sync_dashboard=auto_sync,
            )
            
            return _ok({
                "task_id": task_id,
                "pipelines": pipelines,
                "mode": mode,
                "message": f"Pipeline 任务已启动: {task_id}",
            })

        return _ok({"note": f"{action} 已识别但未实现"})
    except HTTPException:
        raise
    except Exception as e:
        return _fail(e)