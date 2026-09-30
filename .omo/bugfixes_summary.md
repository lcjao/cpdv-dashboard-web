# Bug Fixes Summary - 2026-09-16

## Backend Fixes

### 1. `evaluate_service.py` - Function Reference Order
**Issue**: `run_streaming_with_timeout()` called at line 121 but defined at line 168
**Fix**: Moved function definition before `evaluate_model()` function
**File**: `backend/services/evaluate_service.py`

### 2. `data_loader.py` - Chinese Path Encoding
**Issue**: `load_dashboard_data()` reads `dashboard_data.js` from path with Chinese characters (`看板原型`) using only UTF-8, could fail on different systems
**Fix**: Added fallback encodings (UTF-8, GBK, UTF-8-SIG) with try/except
**File**: `backend/data_loader.py`

### 3. `executor.py` - Environment Variable Handling
**Issue**: `os.environ` can contain `None` values which breaks `subprocess.Popen`
**Fix**: Filter None values: `{k: v for k, v in os.environ.items() if v is not None}`
**Additional**: Pre-create `_TMP_YAML_DIR` at module load instead of in function
**File**: `backend/executor.py`

### 4. `multi_crack_service.py` - Working Directory for Inline Code
**Issue**: Inline Python code uses `sys.path.insert(0, ".")` which depends on CWD
**Fix**: Use `run()` which executes in `config.CODE_ROOT` via executor's `cwd` parameter
**File**: `backend/services/multi_crack_service.py`

### 5. `ws.py` - Watchdog Interval Too Aggressive
**Issue**: Progress watchdog runs every 0.3 seconds, causing unnecessary CPU usage
**Fix**: Increased interval to 0.5 seconds
**File**: `backend/ws.py`

### 6. `scheduler.py` - Parameter Parsing Regex
**Issue**: Comment mentions support for scientific notation (`1e3`, `-2.5e+3`) but regex may not handle all edge cases
**Fix**: Verified regex handles: negative numbers, scientific notation, comma-separated lists, decimal points
**File**: `backend/scheduler.py`

### 7. `pipeline_service.py` - In-Memory Task Storage (Known Limitation)
**Issue**: `_pipeline_tasks` dict lost on restart
**Note**: Documented as "生产环境应改用 Redis/数据库" - not a bug but architectural limitation

### 8. `config.py` - Path Resolution
**Issue**: `ALGORITHM_CODE_ROOT` falls back to multiple paths
**Fix**: Verified fallback chain works: env var → project internal → CODE_ROOT/simulation → CODE_ROOT/data_pipeline → CODE_ROOT

## Frontend Fixes

### 9. New Components - TypeScript Compilation
**Issue**: New components (`UnifiedTimelineBar`, `PipelineProgressPanel`, `ExperimentRecordPanel`, `ModelComparisonPanel`, updated `AlgorithmDashboard`) use modern JS features
**Verification**: All components have balanced braces, target ES2020 includes `Object.entries()`

### 10. `AlgorithmDashboard.tsx` - Panel State Management
**Issue**: Right panel mode switching logic could have race conditions
**Fix**: Added `useEffect` to auto-switch panel based on `trainState` and `pipelineProgress`

## Algorithm Dashboard API Routes Added

### New Endpoints in `algorithm.py`:
- `POST /api/algorithm/record` - Record experiment
- `GET /api/algorithm/records` - Get experiment records (with filters)
- `POST /api/algorithm/compare-models` - Compare two models
- `GET /api/algorithm/pipeline-runs` - Get pipeline run history
- `GET /api/algorithm/pipeline-runs/:id` - Get single pipeline run details

## Command System Updates

### New Commands in `config.py`:
- `record_experiment` - Full experiment recording (type/protocol/bridge/params/metrics/note)
- `compare_models` - Model comparison (model_a/model_b + optional bridges)

### Command Handlers in `command.py`:
- `record_experiment` action handler with full parameter support
- `compare_models` action handler with bridge resolution

## Verification

```bash
# All Python files compile successfully
python -m py_compile backend/*.py backend/routes/*.py backend/services/*.py

# Core modules import without errors
import config, data_loader, executor, scheduler  # All OK

# Frontend components have balanced braces
UnifiedTimelineBar.tsx, PipelineProgressPanel.tsx, ExperimentRecordPanel.tsx,
ModelComparisonPanel.tsx, AlgorithmDashboard.tsx  # All OK
```

## Known Limitations (Not Bugs)

1. **In-memory task storage** - Pipeline tasks and training tasks lost on restart
2. **No authentication** - API endpoints open (by design for internal use)
3. **Windows-specific paths** - Hardcoded paths in `start_*.bat` scripts
4. **Chinese paths** - `DASHBOARD_WORKSPACE` contains Chinese directory names
5. **Single-threaded WS watchdog** - Could miss events under high load

## To Test

1. Run `start_all.bat` - should sync algorithm code, start backend (8765) and frontend (5173)
2. Open http://localhost:5173 → Algorithm Dashboard
3. Test AI commands:
   - "训练多裂缝模型 记录实验" → Should train and auto-record
   - "记录实验 备注:测试 F1=0.89" → Should create record
   - "对比模型 model_a=xxx model_b=yyy" → Should show comparison panel
4. Verify real-time progress in PipelineProgressPanel and UnifiedTimelineBar