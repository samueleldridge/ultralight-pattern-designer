from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
from sqlalchemy import select, and_
from app.database import AsyncSessionLocal
from app.models import QuestionHistory


class EvalMetricType(str, Enum):
    """Types of evaluation metrics"""
    SQL_SYNTAX = "sql_syntax"  # Does SQL parse correctly?
    SQL_EXECUTION = "sql_execution"  # Does SQL execute without error?
    RESULT_CORRECTNESS = "result_correctness"  # Are results numerically correct?
    SEMANTIC_SIMILARITY = "semantic_similarity"  # Is generated SQL semantically equivalent to expected?
    USER_SATISFACTION = "user_satisfaction"  # Did user find answer helpful?
    LATENCY = "latency"  # Response time
    COST = "cost"  # Token/cost efficiency
    RETRY_COUNT = "retry_count"  # How many retries needed?


@dataclass
class EvalMetric:
    """Individual metric measurement"""
    metric_type: EvalMetricType
    score: float  # 0.0 to 1.0 for binary metrics, actual value for continuous
    raw_value: Any  # Original measurement
    threshold: float  # Minimum acceptable score
    passed: bool
    details: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EvalResult:
    """Complete evaluation result for a single query"""
    query_id: str
    question: str
    expected_sql: Optional[str]
    generated_sql: str
    metrics: List[EvalMetric]
    overall_score: float
    passed: bool
    agent_steps: List[Dict]
    execution_time_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "query_id": self.query_id,
            "question": self.question,
            "expected_sql": self.expected_sql,
            "generated_sql": self.generated_sql,
            "metrics": [
                {
                    "type": m.metric_type.value,
                    "score": m.score,
                    "raw_value": m.raw_value,
                    "threshold": m.threshold,
                    "passed": m.passed,
                    "details": m.details
                }
                for m in self.metrics
            ],
            "overall_score": self.overall_score,
            "passed": self.passed,
            "agent_steps": self.agent_steps,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class SQLEvaluator:
    """Evaluate SQL correctness and semantic equivalence"""
    
    def __init__(self):
        from app.database.dialect import SQLValidator
        self.validator = SQLValidator
    
    async def evaluate_syntax(self, sql: str, dialect: str = "postgresql") -> EvalMetric:
        """Check if SQL is syntactically valid"""
        from app.database.dialect import SQLValidator, SQLDialect
        
        validator = SQLValidator(SQLDialect(dialect))
        result = validator.validate(sql)
        
        return EvalMetric(
            metric_type=EvalMetricType.SQL_SYNTAX,
            score=1.0 if result["valid"] else 0.0,
            raw_value=result,
            threshold=1.0,
            passed=result["valid"],
            details="; ".join(result["errors"]) if not result["valid"] else None
        )
    
    async def evaluate_execution(
        self, 
        sql: str, 
        config: Any,
        timeout: int = 30
    ) -> EvalMetric:
        """Check if SQL executes without error"""
        from app.database.executor import QueryExecutor
        
        executor = QueryExecutor()
        start = datetime.utcnow()
        
        try:
            result = await executor.execute(sql, config, timeout_seconds=timeout)
            execution_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            return EvalMetric(
                metric_type=EvalMetricType.SQL_EXECUTION,
                score=1.0 if result["success"] else 0.0,
                raw_value={"success": result["success"], "execution_time_ms": execution_time},
                threshold=1.0,
                passed=result["success"],
                details=result.get("error") if not result["success"] else None
            )
        except Exception as e:
            return EvalMetric(
                metric_type=EvalMetricType.SQL_EXECUTION,
                score=0.0,
                raw_value={"error": str(e)},
                threshold=1.0,
                passed=False,
                details=str(e)
            )
    
    async def evaluate_semantic_similarity(
        self,
        generated_sql: str,
        expected_sql: str
    ) -> EvalMetric:
        """Compare semantic equivalence of two SQL queries"""
        import sqlglot
        
        try:
            # Parse both queries and normalize
            generated_parsed = sqlglot.parse_one(generated_sql)
            expected_parsed = sqlglot.parse_one(expected_sql)
            
            # Normalize (remove aliases, order, etc)
            generated_normalized = generated_parsed.sql(normalize=True)
            expected_normalized = expected_parsed.sql(normalize=True)
            
            # Check if normalized forms match
            exact_match = generated_normalized == expected_normalized
            
            # Check structure similarity
            generated_tables = set(t.name for t in generated_parsed.find_all(sqlglot.exp.Table))
            expected_tables = set(t.name for t in expected_parsed.find_all(sqlglot.exp.Table))
            
            table_overlap = len(generated_tables & expected_tables) / max(len(expected_tables), 1)
            
            # Overall semantic score
            if exact_match:
                score = 1.0
            elif table_overlap >= 0.8:
                score = 0.7  # Good table overlap but different query structure
            elif table_overlap >= 0.5:
                score = 0.4  # Some overlap
            else:
                score = 0.0  # No meaningful overlap
            
            return EvalMetric(
                metric_type=EvalMetricType.SEMANTIC_SIMILARITY,
                score=score,
                raw_value={
                    "exact_match": exact_match,
                    "table_overlap": table_overlap,
                    "generated_normalized": generated_normalized,
                    "expected_normalized": expected_normalized
                },
                threshold=0.7,  # 70% similarity threshold
                passed=score >= 0.7,
                details=f"Table overlap: {table_overlap:.0%}, Exact match: {exact_match}"
            )
            
        except Exception as e:
            return EvalMetric(
                metric_type=EvalMetricType.SEMANTIC_SIMILARITY,
                score=0.0,
                raw_value={"error": str(e)},
                threshold=0.7,
                passed=False,
                details=f"Parse error: {str(e)}"
            )
    
    async def evaluate_result_correctness(
        self,
        generated_sql: str,
        expected_sql: str,
        config: Any
    ) -> EvalMetric:
        """Compare execution results for correctness"""
        from app.database.executor import QueryExecutor
        
        executor = QueryExecutor()
        
        try:
            # Execute both queries
            generated_result = await executor.execute(generated_sql, config)
            expected_result = await executor.execute(expected_sql, config)
            
            if not generated_result["success"] or not expected_result["success"]:
                return EvalMetric(
                    metric_type=EvalMetricType.RESULT_CORRECTNESS,
                    score=0.0,
                    raw_value={"error": "Execution failed"},
                    threshold=0.9,
                    passed=False
                )
            
            gen_data = generated_result["data"]["rows"]
            exp_data = expected_result["data"]["rows"]
            
            # Compare row counts
            row_count_match = len(gen_data) == len(exp_data)
            
            # Compare first few values (if numeric)
            values_match = True
            if gen_data and exp_data and len(gen_data) > 0 and len(exp_data) > 0:
                for key in gen_data[0].keys():
                    if key in exp_data[0]:
                        gen_val = gen_data[0][key]
                        exp_val = exp_data[0][key]
                        
                        # Numeric comparison with tolerance
                        if isinstance(gen_val, (int, float)) and isinstance(exp_val, (int, float)):
                            if abs(gen_val - exp_val) > 0.01 * abs(exp_val):
                                values_match = False
                                break
                        # String comparison
                        elif str(gen_val) != str(exp_val):
                            values_match = False
                            break
            
            score = 1.0 if (row_count_match and values_match) else 0.5 if row_count_match else 0.0
            
            return EvalMetric(
                metric_type=EvalMetricType.RESULT_CORRECTNESS,
                score=score,
                raw_value={
                    "generated_row_count": len(gen_data),
                    "expected_row_count": len(exp_data),
                    "row_count_match": row_count_match,
                    "values_match": values_match
                },
                threshold=0.9,
                passed=score >= 0.9,
                details=f"Rows: {len(gen_data)} vs {len(exp_data)}, Values match: {values_match}"
            )
            
        except Exception as e:
            return EvalMetric(
                metric_type=EvalMetricType.RESULT_CORRECTNESS,
                score=0.0,
                raw_value={"error": str(e)},
                threshold=0.9,
                passed=False,
                details=str(e)
            )


class AgentEvaluator:
    """Evaluate end-to-end agent performance"""
    
    def __init__(self):
        self.sql_evaluator = SQLEvaluator()
    
    async def evaluate_query(
        self,
        question: str,
        expected_sql: Optional[str],
        agent_config: Dict,
        db_config: Any
    ) -> EvalResult:
        """Run complete evaluation of a query through the agent"""
        import uuid
        from app.agent.workflow import workflow_app
        from app.agent.state import AgentState
        
        query_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Run agent workflow
        initial_state = AgentState(
            query=question,
            tenant_id="eval",
            user_id="eval",
            workflow_id=query_id,
            started_at=start_time.isoformat(),
            investigation_history=[],
            retry_count=0,
            sql_valid=True,
            needs_clarification=False,
            investigation_complete=False
        )
        
        # Execute workflow and collect steps
        steps = []
        final_state = None
        
        async for state in workflow_app.astream(initial_state):
            steps.append({
                "step": state.get("current_step"),
                "status": state.get("step_status"),
                "message": state.get("step_message")
            })
            final_state = state
        
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Get generated SQL
        generated_sql = final_state.get("sql", "")
        
        # Evaluate all metrics
        metrics = []
        
        # 1. Syntax
        syntax_metric = await self.sql_evaluator.evaluate_syntax(generated_sql)
        metrics.append(syntax_metric)
        
        # 2. Execution (if syntax passed)
        if syntax_metric.passed:
            exec_metric = await self.sql_evaluator.evaluate_execution(generated_sql, db_config)
            metrics.append(exec_metric)
            
            # 3. Semantic similarity (if we have expected SQL)
            if expected_sql:
                semantic_metric = await self.sql_evaluator.evaluate_semantic_similarity(
                    generated_sql, expected_sql
                )
                metrics.append(semantic_metric)
                
                # 4. Result correctness
                if exec_metric.passed:
                    result_metric = await self.sql_evaluator.evaluate_result_correctness(
                        generated_sql, expected_sql, db_config
                    )
                    metrics.append(result_metric)
        
        # 5. Latency
        latency_metric = EvalMetric(
            metric_type=EvalMetricType.LATENCY,
            score=1.0 if execution_time < 5000 else 0.5 if execution_time < 10000 else 0.0,
            raw_value=execution_time,
            threshold=0.7,
            passed=execution_time < 10000,
            details=f"Execution time: {execution_time}ms"
        )
        metrics.append(latency_metric)
        
        # 6. Retry count
        retry_metric = EvalMetric(
            metric_type=EvalMetricType.RETRY_COUNT,
            score=1.0 if final_state.get("retry_count", 0) == 0 else 0.5,
            raw_value=final_state.get("retry_count", 0),
            threshold=1.0,
            passed=final_state.get("retry_count", 0) <= 1,
            details=f"Retries needed: {final_state.get('retry_count', 0)}"
        )
        metrics.append(retry_metric)
        
        # Calculate overall score
        overall_score = sum(m.score for m in metrics) / len(metrics) if metrics else 0.0
        
        # Determine pass/fail
        critical_metrics = [EvalMetricType.SQL_SYNTAX, EvalMetricType.SQL_EXECUTION]
        critical_passed = all(
            m.passed for m in metrics 
            if m.metric_type in critical_metrics
        )
        
        return EvalResult(
            query_id=query_id,
            question=question,
            expected_sql=expected_sql,
            generated_sql=generated_sql,
            metrics=metrics,
            overall_score=overall_score,
            passed=critical_passed and overall_score >= 0.7,
            agent_steps=steps,
            execution_time_ms=execution_time
        )


class EvaluationSuite:
    """Run evaluation suite on test dataset"""
    
    def __init__(self):
        self.evaluator = AgentEvaluator()
        self.results: List[EvalResult] = []
    
    async def run_dataset(
        self,
        test_cases: List[Dict],
        db_config: Any,
        parallel: int = 5
    ) -> Dict[str, Any]:
        """Run evaluation on full test dataset"""
        
        async def eval_single(test_case: Dict) -> EvalResult:
            return await self.evaluator.evaluate_query(
                question=test_case["question"],
                expected_sql=test_case.get("expected_sql"),
                agent_config={},
                db_config=db_config
            )
        
        # Run evaluations with semaphore for parallelism
        semaphore = asyncio.Semaphore(parallel)
        
        async def eval_with_limit(test_case: Dict) -> EvalResult:
            async with semaphore:
                return await eval_single(test_case)
        
        # Execute all evaluations
        self.results = await asyncio.gather(*[
            eval_with_limit(tc) for tc in test_cases
        ])
        
        # Calculate aggregate metrics
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        
        metric_breakdown = {}
        for metric_type in EvalMetricType:
            scores = [
                m.score for r in self.results 
                for m in r.metrics if m.metric_type == metric_type
            ]
            if scores:
                metric_breakdown[metric_type.value] = {
                    "mean": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores),
                    "pass_rate": sum(1 for s in scores if s >= 0.7) / len(scores)
                }
        
        return {
            "total_queries": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "mean_overall_score": sum(r.overall_score for r in self.results) / total if total > 0 else 0,
            "mean_execution_time_ms": sum(r.execution_time_ms for r in self.results) / total if total > 0 else 0,
            "metric_breakdown": metric_breakdown,
            "detailed_results": [r.to_dict() for r in self.results]
        }
    
    def save_report(self, filepath: str):
        """Save evaluation report to file"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_evaluations": len(self.results),
            "results": [r.to_dict() for r in self.results]
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
    
    def compare_to_baseline(self, baseline_path: str) -> Dict:
        """Compare current results to baseline"""
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)
        
        current_pass_rate = sum(1 for r in self.results if r.passed) / len(self.results)
        baseline_pass_rate = baseline.get("pass_rate", 0)
        
        return {
            "current_pass_rate": current_pass_rate,
            "baseline_pass_rate": baseline_pass_rate,
            "improvement": current_pass_rate - baseline_pass_rate,
            "regressions": [
                r.question for r in self.results 
                if not r.passed and r.question in [
                    b["question"] for b in baseline.get("results", []) 
                    if b.get("passed")
                ]
            ]
        }
