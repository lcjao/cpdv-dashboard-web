# Algorithm Dashboard Redesign Plan

## Overview
Redesign the algorithm dashboard to integrate three core capabilities:
1. **Pipeline Progress Tracking** - Real-time monitoring of pipeline execution via WebSocket
2. **Experiment Recording** - AI Control Panel issues "record experiment" commands, dashboard syncs and displays
3. **Model Comparison** - Side-by-side model pros/cons with metrics

## Architecture

### Component Hierarchy
```
AlgorithmDashboard (main)
├── TopBar (library selector, sync, view mode)
├── LeftPanel (ModuleTree - navigation)
├── CenterPanel (UnifiedTimelineBar)
│   ├── PipelineRuns view
│   ├── Experiments view (merged with existing)
│   └── Commits view
└── RightPanel (Dynamic Panels)
    ├── PipelineProgressPanel (when pipeline running)
    ├── ExperimentRecordPanel (when protocol selected)
    ├── ModelComparisonPanel (when compare triggered)
    └── ContractPanel (existing - protocol details)
```

### Data Flow
```
User (AI Control Panel) 
    → Natural language "记录实验 F1=0.89"
    → LLM parses → cb_record_experiment tool
    → Backend /api/command → record_service.append_record()
    → records.jsonl appended
    → Sync script reads records.jsonl → timeline.json experiments[]
    → TimelineBar (experiments view) auto-updates
    → RightPanel ExperimentRecordCard shows latest
    
Pipeline Execution:
    → cb_train / cb_pipeline_run
    → Backend train_service / pipeline_service
    → WS emits 'train' or 'pipeline' events
    → ProgressContext → useTagProgress('train') 
    → PipelineProgressPanel + TimelineBar real-time update
    → On completion → auto record_experiment → records.jsonl
```

### State Management
- **Global**: `ProgressContext` for WS events (already exists)
- **Local**: React useState for panel visibility, selected items
- **Server State**: React hooks (useTraining, useRecord, useCompare) for REST API
- **Derived**: timeline.json from sync script (polling or manual refresh)

## New Components

### 1. PipelineProgressPanel
Shows real-time pipeline/training progress:
- Stage indicator (data_gen → phase1 → phase2 → phase3 → eval → done)
- Progress bar with percentage
- Epoch/loss display
- Cancel button (AbortController integration)
- Auto-shows when train/pipeline status is running

### 2. ExperimentRecordPanel
- Latest experiment card (ID, time, type, key metrics F1/MAE)
- "Record Experiment" button → modal for note input → calls cb_record
- "View History" → switches CenterPanel to experiments view
- Auto-refreshes from records.jsonl via timeline.json

### 3. ModelComparisonPanel
- Two-model selector (base vs target)
- Metrics comparison table (F1, Precision, Recall, MAE_pos, MAE_depth)
- Winner badge
- Architectural diff summary
- "Record Comparison" button

### 4. UnifiedTimelineBar (Enhanced)
Three tabs:
- **Pipeline Runs**: Shows pipeline execution history with inline progress bars
- **Experiments**: Existing experiment cards + new auto-recorded ones
- **Commits**: Git history (existing)

## Type Definitions (Additions)

```typescript
// Pipeline run record
interface PipelineRunRecord {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  durationMs?: number;
  stages: PipelineStage[];
  metrics?: Record<string, number>;
  error?: string;
}

interface PipelineStage {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  progress?: number;
  logs?: string[];
}

// Experiment record (extends existing)
interface ExperimentRecord {
  id: string;
  timestamp: string;
  type: 'train' | 'evaluate' | 'predict' | 'compare' | 'multi_crack_train' | 'pipeline_run';
  protocol?: string;
  bridge?: string;
  params: Record<string, any>;
  metrics?: Record<string, number>;
  note: string;
  pipelineRunId?: string;  // Link to pipeline run
}

// Model comparison result
interface ModelComparison {
  modelA: { path: string; metrics: Record<string, number>; config: any };
  modelB: { path: string; metrics: Record<string, number>; config: any };
  comparison: {
    f1_diff: number;
    precision_diff: number;
    recall_diff: number;
    position_mae_diff: number;
    depth_mae_diff: number;
    winner: 'a' | 'b' | 'tie';
    summary: string;
  };
}
```

## Backend Changes

### New/Updated Routes
- `POST /api/algorithm/record` - Record experiment (already exists via record_service)
- `GET /api/algorithm/records` - Fetch records with filters
- `POST /api/algorithm/compare` - Compare two models (use compare_service)
- `GET /api/algorithm/pipeline-runs` - List pipeline run history
- `GET /api/algorithm/pipeline-runs/:id` - Get pipeline run details

### WebSocket Events
- `train` - Training progress (existing)
- `pipeline` - Pipeline execution progress (new)
- `record` - Experiment recorded notification (new)

## AI Control Panel Integration

### New Commands in COMMAND_META
```python
{
  "name": "cb_record_experiment",
  "chinese": "记录实验",
  "params": ["note", "type", "protocol", "bridge", "params", "metrics"],
  "llm_tool": true,
  "quick": false
},
{
  "name": "cb_compare_models",
  "chinese": "对比模型",
  "params": ["model_a", "model_b", "bridge_a", "bridge_b"],
  "llm_tool": true,
  "quick": false
}
```

### Tool Definitions (cpdv-tools.ts)
Auto-generated from COMMAND_META - no manual changes needed.

## Implementation Priority

### Phase 1: Core UI (High)
1. New AlgorithmDashboard.tsx with three-panel layout
2. PipelineProgressPanel component
3. ExperimentRecordPanel component
4. ModelComparisonPanel component
5. Updated TimelineBar with pipeline runs tab

### Phase 2: Backend Integration (High)
1. Update algorithm.py routes for pipeline-runs, compare, records
2. Ensure WebSocket emits pipeline events
3. Update sync script to include pipeline runs in timeline.json

### Phase 3: AI Integration (High)
1. Add cb_record_experiment, cb_compare_models to COMMAND_META
2. Verify tool loop handles new commands
3. Test end-to-end: AI command → dashboard update

### Phase 4: Polish (Medium)
1. Loading states, error handling
2. Keyboard shortcuts
3. Responsive layout
4. Documentation

## Files to Modify/Create

### New Files
- `frontend/src/components/algorithm/PipelineProgressPanel.tsx`
- `frontend/src/components/algorithm/ExperimentRecordPanel.tsx`
- `frontend/src/components/algorithm/ModelComparisonPanel.tsx`
- `frontend/src/components/algorithm/UnifiedTimelineBar.tsx` (replaces TimelineBar)

### Modified Files
- `frontend/src/components/algorithm/AlgorithmDashboard.tsx` (major rewrite)
- `frontend/src/hooks/useAlgorithmDashboard.ts` (add usePipelineRuns, useCompareModels)
- `frontend/src/lib/algorithm-api.ts` (add new API functions)
- `frontend/src/lib/algorithm-types.ts` (add new types)
- `backend/routes/algorithm.py` (add new endpoints)
- `backend/config.py` (add new COMMAND_META entries)

### Removed Files
- `frontend/src/components/algorithm/PipelineBuilder.tsx` (no longer needed)
- `frontend/src/components/algorithm/PipelineCanvas.tsx`
- `frontend/src/components/algorithm/NodePalette.tsx`
- `frontend/src/components/algorithm/NodeEditor.tsx`