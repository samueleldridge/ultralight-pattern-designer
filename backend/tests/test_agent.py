"""
Unit and integration tests for agent workflow nodes.

Tests cover:
- Individual node functions (classify, context, generate, validate, execute)
- Workflow routing logic
- Error handling and retry logic
- State management
"""

import json
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.agent.state import AgentState
from app.agent.nodes.classify import classify_intent_node, router
from app.agent.nodes.context import fetch_context_node
from app.agent.nodes.generate import generate_sql_node, generate_sql_node_v2
from app.agent.nodes.validate import validate_sql_node, validation_router
from app.agent.nodes.execute import execute_sql_node, execution_router
from app.agent.nodes.analyze import analyze_results_node, generate_viz_node
from app.agent.nodes.error import analyze_error_node, error_router
from app.agent.nodes.utility import ask_clarification_node, end_node, should_investigate


# =============================================================================
# Classify Node Tests
# =============================================================================

@pytest.mark.agent
class TestClassifyNode:
    """Test intent classification node."""
    
    @pytest.mark.asyncio
    async def test_classify_simple_query(self, sample_agent_state, mock_llm_provider):
        """Simple query should be classified as 'simple'."""
        mock_llm_provider.generate.return_value = json.dumps({
            "intent": "simple",
            "reasoning": "Direct lookup query"
        })
        
        result = await classify_intent_node(sample_agent_state)
        
        assert result["current_step"] == "classify_intent"
        assert result["step_status"] == "complete"
        assert result["intent"] == "simple"
        assert result["needs_clarification"] is False
    
    @pytest.mark.asyncio
    async def test_classify_complex_query(self, sample_agent_state, mock_llm_provider):
        """Complex query should be classified as 'complex'."""
        mock_llm_provider.generate.return_value = json.dumps({
            "intent": "complex",
            "reasoning": "Requires multiple joins"
        })
        
        sample_agent_state["query"] = "What is the average revenue per customer by region?"
        result = await classify_intent_node(sample_agent_state)
        
        assert result["intent"] == "complex"
    
    @pytest.mark.asyncio
    async def test_classify_clarify_needed(self, sample_agent_state, mock_llm_provider):
        """Ambiguous query should need clarification."""
        mock_llm_provider.generate.return_value = json.dumps({
            "intent": "clarify",
            "reasoning": "Missing time range"
        })
        
        result = await classify_intent_node(sample_agent_state)
        
        assert result["intent"] == "clarify"
        assert result["needs_clarification"] is True
        assert "clarification_question" in result
    
    @pytest.mark.asyncio
    async def test_classify_investigate_query(self, sample_agent_state, mock_llm_provider):
        """Investigation query should be classified as 'investigate'."""
        mock_llm_provider.generate.return_value = json.dumps({
            "intent": "investigate",
            "reasoning": "Asking 'why' question"
        })
        
        sample_agent_state["query"] = "Why did sales drop last month?"
        result = await classify_intent_node(sample_agent_state)
        
        assert result["intent"] == "investigate"
    
    @pytest.mark.asyncio
    async def test_classify_handles_invalid_json(self, sample_agent_state, mock_llm_provider):
        """Should handle invalid JSON response gracefully."""
        mock_llm_provider.generate.return_value = "invalid json"
        
        result = await classify_intent_node(sample_agent_state)
        
        assert result["intent"] == "simple"  # Default fallback
        assert result["step_status"] == "complete"
    
    def test_router_clarification(self):
        """Router should return ask_clarification when needed."""
        state = {"needs_clarification": True}
        assert router(state) == "ask_clarification"
    
    def test_router_fetch_context(self):
        """Router should return fetch_context when no clarification needed."""
        state = {"needs_clarification": False}
        assert router(state) == "fetch_context"


# =============================================================================
# Context Node Tests
# =============================================================================

@pytest.mark.agent
class TestContextNode:
    """Test context fetching node."""
    
    @pytest.mark.asyncio
    async def test_fetch_context_populates_all_fields(self, sample_agent_state):
        """Should populate all context fields."""
        result = await fetch_context_node(sample_agent_state)
        
        assert result["current_step"] == "fetch_context"
        assert result["step_status"] == "complete"
        assert "user_context" in result
        assert "schema_context" in result
        assert "few_shot_examples" in result
        assert "semantic_definitions" in result
    
    @pytest.mark.asyncio
    async def test_fetch_context_handles_errors(self, sample_agent_state):
        """Should handle fetch errors gracefully."""
        # State should still be returned even if fetches fail
        result = await fetch_context_node(sample_agent_state)
        
        assert result["step_status"] == "complete"
        assert isinstance(result["user_context"], dict)
        assert isinstance(result["schema_context"], dict)
    
    @pytest.mark.asyncio
    async def test_fetch_context_empty_connection_id(self):
        """Should handle missing connection_id."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            connection_id=None,
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await fetch_context_node(state)
        
        assert result["step_status"] == "complete"
        assert "schema_context" in result


# =============================================================================
# Generate Node Tests
# =============================================================================

@pytest.mark.agent
class TestGenerateNode:
    """Test SQL generation node."""
    
    @pytest.mark.asyncio
    async def test_generate_sql_success(self, sample_agent_state, mock_llm_provider):
        """Should generate SQL successfully."""
        mock_llm_provider.generate_json.return_value = {
            "sql": "SELECT SUM(total) as revenue FROM orders",
            "explanation": "Calculate total revenue",
            "chart_type": "metric",
            "confidence": 0.95
        }
        
        result = await generate_sql_node(sample_agent_state)
        
        assert result["current_step"] == "generate_sql"
        assert result["step_status"] == "complete"
        assert "sql" in result
        assert "SELECT" in result["sql"]
        assert "visualization_config" in result
    
    @pytest.mark.asyncio
    async def test_generate_sql_handles_error(self, sample_agent_state, mock_llm_provider):
        """Should handle generation errors."""
        mock_llm_provider.generate_json.side_effect = Exception("LLM error")
        
        result = await generate_sql_node(sample_agent_state)
        
        assert result["step_status"] == "error"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_generate_sql_empty_response(self, sample_agent_state, mock_llm_provider):
        """Should handle empty SQL response."""
        mock_llm_provider.generate_json.return_value = {
            "sql": "",
            "explanation": "",
            "chart_type": "table"
        }
        
        result = await generate_sql_node(sample_agent_state)
        
        assert result["step_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_generate_sql_v2_success(self, sample_agent_state, mock_llm_provider):
        """Should generate SQL with v2 (enhanced) node."""
        mock_llm_provider.generate_json.side_effect = [
            {
                "entities": ["orders.total", "orders.created_at"],
                "time_range": "last month",
                "aggregations": ["SUM"],
                "filters": [],
                "edge_cases": []
            },
            {
                "sql": "SELECT SUM(total) FROM orders WHERE created_at > NOW() - INTERVAL '1 month'",
                "explanation": "Revenue for last month",
                "chart_type": "metric",
                "parameters": [],
                "estimated_rows": 1
            }
        ]
        
        result = await generate_sql_node_v2(sample_agent_state)
        
        assert result["current_step"] == "generate_sql_v2"
        assert result["step_status"] == "complete"
        assert "sql" in result
        assert "analysis" in result
    
    @pytest.mark.asyncio
    async def test_generate_sql_with_context(self, sample_agent_state, mock_llm_provider):
        """Should use context in SQL generation."""
        mock_llm_provider.generate_json.return_value = {
            "sql": "SELECT * FROM orders WHERE created_at > '2024-01-01'",
            "explanation": "Recent orders",
            "chart_type": "table",
            "confidence": 0.9
        }
        
        result = await generate_sql_node(sample_agent_state)
        
        # Verify context was included in prompt
        call_args = mock_llm_provider.generate_json.call_args
        assert call_args is not None
        prompt = call_args.kwargs.get("prompt", "")
        assert "orders" in prompt or "Context:" in prompt


# =============================================================================
# Validate Node Tests
# =============================================================================

@pytest.mark.agent
class TestValidateNode:
    """Test SQL validation node."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_select(self):
        """Valid SELECT should pass validation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="SELECT * FROM orders WHERE status = 'active'",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await validate_sql_node(state)
        
        assert result["current_step"] == "validate_sql"
        assert result["step_status"] == "complete"
        assert result["sql_valid"] is True
        assert result["validation_error"] is None
    
    @pytest.mark.asyncio
    async def test_validate_rejects_delete(self):
        """DELETE should fail validation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="DELETE FROM orders WHERE id = 1",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await validate_sql_node(state)
        
        assert result["sql_valid"] is False
        assert result["validation_error"] is not None
        assert "DELETE" in result["validation_error"]
    
    @pytest.mark.asyncio
    async def test_validate_rejects_drop(self):
        """DROP should fail validation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="DROP TABLE orders",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await validate_sql_node(state)
        
        assert result["sql_valid"] is False
        assert "DROP" in result["validation_error"]
    
    @pytest.mark.asyncio
    async def test_validate_rejects_update(self):
        """UPDATE should fail validation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="UPDATE orders SET status = 'cancelled'",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await validate_sql_node(state)
        
        assert result["sql_valid"] is False
        assert "UPDATE" in result["validation_error"]
    
    @pytest.mark.asyncio
    async def test_validate_rejects_truncate(self):
        """TRUNCATE should fail validation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="TRUNCATE TABLE orders",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await validate_sql_node(state)
        
        assert result["sql_valid"] is False
        assert "TRUNCATE" in result["validation_error"]
    
    @pytest.mark.asyncio
    async def test_validate_rejects_insert(self):
        """INSERT should fail validation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="INSERT INTO orders (id) VALUES (1)",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await validate_sql_node(state)
        
        assert result["sql_valid"] is False
        assert "INSERT" in result["validation_error"]
    
    @pytest.mark.asyncio
    async def test_validate_rejects_missing_from(self):
        """SELECT without FROM should fail validation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="SELECT 1",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await validate_sql_node(state)
        
        assert result["sql_valid"] is False
        assert "FROM" in result["validation_error"]
    
    def test_validation_router_valid(self):
        """Router should route to execute when valid."""
        state = {"sql_valid": True}
        assert validation_router(state) == "execute"
    
    def test_validation_router_invalid(self):
        """Router should route to analyze_error when invalid."""
        state = {"sql_valid": False}
        assert validation_router(state) == "analyze_error"


# =============================================================================
# Execute Node Tests
# =============================================================================

@pytest.mark.agent
class TestExecuteNode:
    """Test SQL execution node."""
    
    @pytest.mark.asyncio
    async def test_execute_empty_sql(self):
        """Empty SQL should return error."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await execute_sql_node(state)
        
        assert result["step_status"] == "error"
        assert "execution_error" in result
    
    @pytest.mark.asyncio
    async def test_execute_sets_step_status(self):
        """Should set step status appropriately."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            sql="SELECT 1 as test",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await execute_sql_node(state)
        
        assert result["current_step"] == "execute_sql"
        assert result["step_status"] in ["complete", "error"]
    
    def test_execution_router_success(self):
        """Router should route to analyze_results on success."""
        state = {"execution_result": {"rows": []}}
        assert execution_router(state) == "analyze_results"
    
    def test_execution_router_error(self):
        """Router should route to analyze_error on failure."""
        state = {"execution_error": "Connection failed"}
        assert execution_router(state) == "analyze_error"


# =============================================================================
# Analyze Node Tests
# =============================================================================

@pytest.mark.agent
class TestAnalyzeNode:
    """Test result analysis node."""
    
    @pytest.mark.asyncio
    async def test_analyze_empty_results(self, sample_agent_state, mock_llm_provider):
        """Empty results should provide helpful message."""
        sample_agent_state["execution_result"] = {
            "rows": [],
            "row_count": 0,
            "columns": []
        }
        
        result = await analyze_results_node(sample_agent_state)
        
        assert result["current_step"] == "analyze_results"
        assert result["step_status"] == "complete"
        assert "insights" in result
        assert "follow_up_suggestions" in result
        assert len(result["follow_up_suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_with_results(self, sample_agent_state, mock_llm_provider):
        """Should analyze results and generate insights."""
        mock_llm_provider.generate.return_value = json.dumps({
            "summary": "Revenue increased by 15%",
            "insights": ["Strong growth in Q4", "Mobile sales leading"],
            "follow_ups": ["What drove Q4 growth?", "Compare to last year"]
        })
        
        sample_agent_state["execution_result"] = {
            "rows": [{"month": "2024-01", "revenue": 100000}],
            "row_count": 1,
            "columns": ["month", "revenue"]
        }
        
        result = await analyze_results_node(sample_agent_state)
        
        assert result["insights"] is not None
        assert len(result["follow_up_suggestions"]) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_handles_json_error(self, sample_agent_state, mock_llm_provider):
        """Should handle invalid JSON response."""
        mock_llm_provider.generate.return_value = "invalid json"
        
        sample_agent_state["execution_result"] = {
            "rows": [{"test": 1}],
            "row_count": 1,
            "columns": ["test"]
        }
        
        result = await analyze_results_node(sample_agent_state)
        
        assert result["step_status"] == "complete"
        assert result["insights"] is not None
        assert len(result["follow_up_suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_generate_viz_table_default(self, sample_agent_state):
        """Should default to table visualization."""
        sample_agent_state["execution_result"] = {
            "rows": [{"a": 1, "b": 2}],
            "row_count": 1,
            "columns": ["a", "b"]
        }
        
        result = await generate_viz_node(sample_agent_state)
        
        assert result["current_step"] == "generate_viz"
        assert result["step_status"] == "complete"
        assert "visualization_config" in result
        assert result["visualization_config"]["type"] == "table"
    
    @pytest.mark.asyncio
    async def test_generate_viz_detects_line_chart(self, sample_agent_state):
        """Should detect time series for line chart."""
        sample_agent_state["execution_result"] = {
            "rows": [
                {"date": "2024-01-01", "value": 100},
                {"date": "2024-01-02", "value": 200}
            ],
            "row_count": 2,
            "columns": ["date", "value"]
        }
        sample_agent_state["visualization_config"] = {"type": "table"}
        
        result = await generate_viz_node(sample_agent_state)
        
        assert result["visualization_config"]["type"] == "line"
        assert result["visualization_config"]["x_axis"] == "date"


# =============================================================================
# Error Node Tests
# =============================================================================

@pytest.mark.agent
class TestErrorNode:
    """Test error analysis node."""
    
    @pytest.mark.asyncio
    async def test_analyze_validation_error(self, sample_agent_state, mock_llm_provider):
        """Should analyze validation error."""
        mock_llm_provider.generate.return_value = json.dumps({
            "can_fix": True,
            "suggestion": "SELECT * FROM orders",
            "user_question": None
        })
        
        sample_agent_state["validation_error"] = "Query missing FROM clause"
        sample_agent_state["sql"] = "SELECT *"
        sample_agent_state["retry_count"] = 0
        
        result = await analyze_error_node(sample_agent_state)
        
        assert result["current_step"] == "analyze_error"
        assert result["step_status"] == "complete"
    
    @pytest.mark.asyncio
    async def test_analyze_max_retries_reached(self, sample_agent_state, mock_llm_provider):
        """Should ask for clarification after max retries."""
        mock_llm_provider.generate.return_value = json.dumps({
            "can_fix": True,
            "suggestion": "SELECT * FROM orders",
            "user_question": None
        })
        
        sample_agent_state["validation_error"] = "Syntax error"
        sample_agent_state["retry_count"] = 3  # Max retries
        
        result = await analyze_error_node(sample_agent_state)
        
        assert result["needs_clarification"] is True
    
    @pytest.mark.asyncio
    async def test_analyze_cannot_fix(self, sample_agent_state, mock_llm_provider):
        """Should ask for clarification when error can't be fixed."""
        mock_llm_provider.generate.return_value = json.dumps({
            "can_fix": False,
            "suggestion": None,
            "user_question": "What time period are you interested in?"
        })
        
        sample_agent_state["validation_error"] = "Ambiguous column reference"
        
        result = await analyze_error_node(sample_agent_state)
        
        assert result["needs_clarification"] is True
        assert "clarification_question" in result
    
    def test_error_router_retry(self):
        """Router should route to generate_sql for retry."""
        state = {"needs_clarification": False, "retry_count": 1, "sql": "SELECT 1"}
        assert error_router(state) == "generate_sql"
    
    def test_error_router_clarify(self):
        """Router should route to ask_clarification when needed."""
        state = {"needs_clarification": True}
        assert error_router(state) == "ask_clarification"
    
    def test_error_router_end(self):
        """Router should route to end when max retries reached."""
        state = {"needs_clarification": False, "retry_count": 3, "sql": "SELECT 1"}
        assert error_router(state) == "end"


# =============================================================================
# Utility Node Tests
# =============================================================================

@pytest.mark.agent
class TestUtilityNodes:
    """Test utility nodes."""
    
    @pytest.mark.asyncio
    async def test_ask_clarification(self):
        """Should set clarification state."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            clarification_question="What date range?",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await ask_clarification_node(state)
        
        assert result["current_step"] == "ask_clarification"
        assert result["step_status"] == "complete"
        assert result["needs_clarification"] is True
    
    @pytest.mark.asyncio
    async def test_end_node(self):
        """Should mark workflow as complete."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        result = await end_node(state)
        
        assert result["current_step"] == "end"
        assert result["step_status"] == "complete"
    
    def test_should_investigate_incomplete(self):
        """Should route to investigate when investigation incomplete."""
        state = {
            "intent": "investigate",
            "investigation_complete": False
        }
        assert should_investigate(state) == "investigate"
    
    def test_should_investigate_complete(self):
        """Should route to generate_viz when investigation complete."""
        state = {
            "intent": "investigate",
            "investigation_complete": True
        }
        assert should_investigate(state) == "generate_viz"
    
    def test_should_investigate_simple_query(self):
        """Should route to generate_viz for simple queries."""
        state = {
            "intent": "simple",
            "investigation_complete": False
        }
        assert should_investigate(state) == "generate_viz"


# =============================================================================
# State Management Tests
# =============================================================================

@pytest.mark.agent
class TestStateManagement:
    """Test agent state transitions."""
    
    def test_state_initialization(self):
        """Should initialize state with required fields."""
        state = AgentState(
            query="Test query",
            tenant_id="tenant-1",
            user_id="user-1",
            workflow_id="wf-1",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        assert state["query"] == "Test query"
        assert state["retry_count"] == 0
        assert state["sql_valid"] is True
    
    def test_state_mutation(self):
        """Should allow state mutation."""
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        # Simulate workflow progression
        state["current_step"] = "generate_sql"
        state["sql"] = "SELECT * FROM orders"
        state["retry_count"] = 1
        
        assert state["current_step"] == "generate_sql"
        assert state["sql"] == "SELECT * FROM orders"
        assert state["retry_count"] == 1
    
    def test_investigation_history_accumulation(self):
        """Investigation history should accumulate across iterations."""
        from operator import add
        
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="w1",
            investigation_history=[{"step": 1, "finding": "First"}],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        # Simulate adding to history (using Annotated add behavior)
        new_entries = [{"step": 2, "finding": "Second"}]
        combined = add(state["investigation_history"], new_entries)
        
        assert len(combined) == 2
        assert combined[0]["step"] == 1
        assert combined[1]["step"] == 2


# =============================================================================
# Workflow Integration Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.agent
class TestWorkflowIntegration:
    """Integration tests for complete workflow."""
    
    @pytest.mark.asyncio
    async def test_simple_query_workflow(self, mock_llm_provider):
        """Test complete workflow for simple query."""
        # Mock LLM responses for each step
        mock_llm_provider.generate.side_effect = [
            # classify
            json.dumps({"intent": "simple", "reasoning": "Direct lookup"}),
            # analyze results (if reached)
            json.dumps({
                "summary": "Test summary",
                "insights": ["Test insight"],
                "follow_ups": ["Follow up?"]
            })
        ]
        
        mock_llm_provider.generate_json.return_value = {
            "sql": "SELECT COUNT(*) as total FROM orders",
            "explanation": "Count orders",
            "chart_type": "metric",
            "confidence": 0.95
        }
        
        # Initialize state
        state = AgentState(
            query="How many orders?",
            tenant_id="t1",
            user_id="u1",
            workflow_id="wf-1",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        # Run through nodes
        state = await classify_intent_node(state)
        assert state["intent"] == "simple"
        assert router(state) == "fetch_context"
        
        state = await fetch_context_node(state)
        assert state["current_step"] == "fetch_context"
        
        state = await generate_sql_node(state)
        assert state["sql"] is not None
        assert "SELECT" in state["sql"]
        
        state = await validate_sql_node(state)
        assert state["sql_valid"] is True
        assert validation_router(state) == "execute"
    
    @pytest.mark.asyncio
    async def test_clarification_workflow(self, mock_llm_provider):
        """Test workflow that requires clarification."""
        mock_llm_provider.generate.return_value = json.dumps({
            "intent": "clarify",
            "reasoning": "Missing time range"
        })
        
        state = AgentState(
            query="What was revenue?",
            tenant_id="t1",
            user_id="u1",
            workflow_id="wf-1",
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        state = await classify_intent_node(state)
        assert state["needs_clarification"] is True
        assert router(state) == "ask_clarification"
        
        state = await ask_clarification_node(state)
        assert state["current_step"] == "ask_clarification"
    
    @pytest.mark.asyncio
    async def test_retry_workflow(self, mock_llm_provider):
        """Test workflow with SQL retry after error."""
        mock_llm_provider.generate.return_value = json.dumps({
            "can_fix": True,
            "suggestion": "SELECT * FROM orders WHERE 1=1",
            "user_question": None
        })
        
        state = AgentState(
            query="Test",
            tenant_id="t1",
            user_id="u1",
            workflow_id="wf-1",
            sql="SELECT * FROM",  # Invalid SQL
            validation_error="Incomplete SQL",
            investigation_history=[],
            retry_count=0,
            sql_valid=False,
            needs_clarification=False,
            investigation_complete=False
        )
        
        state = await analyze_error_node(state)
        
        assert state["retry_count"] == 1
        assert error_router(state) == "generate_sql"
