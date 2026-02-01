# Streaming Backend Process to Frontend

## Overview

The platform uses **Server-Sent Events (SSE)** to stream agent workflow steps from backend to frontend in real-time. This gives users transparency into the AI's thinking process without being overly technical.

## Why SSE?

| Approach | Pros | Cons |
|----------|------|------|
| **SSE** (chosen) | Simple HTTP, auto-reconnect, firewall-friendly, HTTP/2 efficient | One-way only |
| WebSocket | Bidirectional, lower latency | Complex scaling, firewall issues |
| Polling | Simple | Inefficient, high latency |

**For our use case:** SSE is perfect because:
- Agent workflow is primarily server→client updates
- HTTP-based (works through corporate firewalls)
- Auto-reconnect handles temporary disconnections
- Scales well on AWS (API Gateway supports SSE)

## User Experience

### What Users See

When a user asks: *"What was revenue last month?"*

They see a live progress panel:

```
━━━━━━━━━━ 30%

💭 Understanding your question...      [thinking]
🔍 Looking up your data structure...   [thinking] ← current
⚡ Writing the database query...        [pending]
✓ Validating for safety...            [pending]
📊 Fetching your data...              [pending]
📈 Finding patterns in your data...   [pending]
```

### Step Categories

| Category | Color | Meaning | Examples |
|----------|-------|---------|----------|
| **thinking** | amber | Analyzing/planning | Understanding question, looking up data |
| **action** | blue | Executing | Writing SQL, fetching data |
| **check** | green | Validating | Safety checks, verification |
| **error** | red | Problem solving | Fixing errors, retrying |

## Technical Implementation

### Backend (FastAPI)

```python
@router.get("/stream/{workflow_id}")
async def stream_workflow(workflow_id: str):
    """Stream workflow events via SSE"""
    return StreamingResponse(
        event_generator(workflow_id),
        media_type="text/event-stream"
    )

async def event_generator(workflow_id: str):
    """Generate SSE events"""
    async for state in workflow_app.astream(initial_state):
        event = {
            "step": state["current_step"],      # e.g., "fetch_context"
            "status": state["step_status"],     # e.g., "running"
            "message": "Looking up your data...", # User-friendly
            "icon": "🔍",                       # Visual indicator
            "progress": 30,                     # Overall progress %
            "category": "thinking"              # UI styling
        }
        yield f"data: {json.dumps(event)}\n\n"
```

### Frontend (React)

```typescript
// Connect to SSE
const eventSource = new EventSource(`/api/stream/${workflow_id}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  // Update steps
  setSteps(prev => [...prev, {
    name: data.step,
    message: data.message,
    icon: data.icon,
    progress: data.progress,
    status: data.status
  }]);
};
```

### Event Flow

```
User submits query
       ↓
POST /api/query → Returns workflow_id
       ↓
GET /api/stream/{workflow_id} (SSE connection)
       ↓
┌─────────────────────────────────────────┐
│  Agent Workflow Streaming               │
│                                         │
│  1. classify_intent    → "Understanding"│
│  2. fetch_context      → "Looking up..."│
│  3. generate_sql       → "Writing..."   │
│  4. validate_sql       → "Validating"   │
│  5. execute_sql        → "Fetching..."  │
│  6. analyze_results    → "Analyzing"    │
│  7. generate_viz       → "Creating..."  │
└─────────────────────────────────────────┘
       ↓
Complete → Close SSE connection
```

## Step Messages

### Mapping Technical → User-Friendly

| Technical Step | User-Friendly Message | Icon | Category |
|----------------|----------------------|------|----------|
| `classify_intent` | "Understanding your question..." | 💭 | thinking |
| `fetch_context` | "Looking up your data structure..." | 🔍 | thinking |
| `generate_sql` | "Writing the database query..." | ⚡ | action |
| `validate_sql` | "Double-checking the query..." | ✓ | check |
| `execute_sql` | "Fetching your data..." | 📊 | action |
| `analyze_error` | "Looking into the issue..." | 🔧 | error |
| `analyze_results` | "Finding patterns in your data..." | 📈 | thinking |
| `generate_viz` | "Creating your visualization..." | 📉 | action |

## Progress Calculation

Progress is calculated based on which step is currently running:

```python
STEP_ORDER = [
    "classify_intent",   # 0%
    "fetch_context",     # 15%
    "generate_sql",      # 30%
    "validate_sql",      # 45%
    "execute_sql",       # 60%
    "analyze_results",   # 75%
    "generate_viz",      # 90%
    "end"                # 100%
]

progress = (current_step_index / len(STEP_ORDER)) * 100
```

## AWS Deployment

### API Gateway WebSocket API

For production on AWS, SSE works well with:

```yaml
# API Gateway HTTP API with SSE
Routes:
  - Path: /api/stream/{workflow_id}
    Method: GET
    Integration: Lambda (or ECS/ELB)
    
# Alternative: WebSocket API for more complex needs
Routes:
  - $connect: Authorize connection
  - $disconnect: Cleanup
  - $default: Message handling
```

### Lambda + Function URLs

```yaml
# Lambda Function URL with streaming
FunctionName: query-stream
Runtime: python3.11
FunctionUrlConfig:
  AuthType: NONE
  InvokeMode: RESPONSE_STREAM  # Enable streaming
```

### ECS/Fargate (Recommended)

For persistent connections:

```yaml
# ECS Service with ALB
Service:
  LoadBalancers:
    - ContainerName: api
      ContainerPort: 8000
      Protocol: HTTP
  
# ALB supports SSE natively
```

## Error Handling

### Connection Drops

```typescript
// Frontend auto-reconnect
eventSource.onerror = (error) => {
  console.log('Connection lost, retrying...');
  // Browser auto-reconnects SSE
  // Or implement exponential backoff
};
```

### Timeout Handling

```python
# Backend timeout
async def event_generator(workflow_id: str):
    try:
        async for state in workflow_app.astream(initial_state):
            yield event
    except asyncio.TimeoutError:
        yield {
            "step": "error",
            "message": "Query took too long. Try a more specific question."
        }
```

## Testing

### Manual Test

```bash
# Start query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was revenue?", "tenant_id": "demo", "user_id": "demo"}'

# Stream results
curl http://localhost:8000/api/stream/{workflow_id}
```

### Expected Output

```
data: {"step": "classify_intent", "message": "Understanding your question...", "progress": 0}

data: {"step": "fetch_context", "message": "Looking up your data structure...", "progress": 15}

data: {"step": "generate_sql", "message": "Writing the database query...", "progress": 30}

data: {"step": "validate_sql", "message": "Double-checking the query...", "progress": 45}

data: {"step": "execute_sql", "message": "Fetching your data...", "progress": 60}

data: {"step": "end", "message": "Done!", "progress": 100}
```

## Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Connection setup | < 100ms | First event delivery |
| Step latency | < 500ms | Time between steps |
| Total streaming | 2-10s | Depends on query complexity |
| Concurrent streams | 1000+ | Per server |

## Security

### Connection Authentication

```python
@router.get("/stream/{workflow_id}")
async def stream_workflow(
    workflow_id: str,
    token: str = Query(...)  # JWT or session token
):
    # Verify user owns this workflow
    if not await verify_workflow_access(workflow_id, token):
        raise HTTPException(403)
    
    return StreamingResponse(event_generator(workflow_id))
```

### Rate Limiting

```python
# Limit concurrent streams per user
@limiter.limit("10/minute")
async def stream_workflow(...):
    ...
```

## Summary

The streaming implementation provides:

1. **Transparency**: Users see exactly what the AI is doing
2. **Engagement**: Progress bar and animations keep users engaged
3. **Trust**: Visibility into the process builds confidence
4. **Performance**: SSE is efficient and scales well
5. **AWS-Ready**: Works with API Gateway, Lambda, ECS

**User-friendly, informative, but not overwhelming.**
