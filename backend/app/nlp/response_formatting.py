"""
Response Formatting and Insight Generation Module

Provides:
- Natural language summaries of query results
- Comparative analysis ("up 23% vs last month")
- Anomaly detection and highlighting
- Insight generation with recommendations
"""

import json
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.llm_provider import get_llm_provider
from app.prompts.registry import get_prompt, PromptType


class InsightType(Enum):
    TREND = "trend"
    ANOMALY = "anomaly"
    COMPARISON = "comparison"
    CORRELATION = "correlation"
    SEGMENTATION = "segmentation"
    RECOMMENDATION = "recommendation"


@dataclass
class DataPoint:
    """A single data point from results"""
    value: float
    label: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Comparison:
    """A comparison between values"""
    metric: str
    current_value: float
    previous_value: float
    change_absolute: float
    change_percent: float
    direction: str  # up, down, flat
    description: str


@dataclass
class Anomaly:
    """Detected anomaly in data"""
    description: str
    value: float
    expected_range: Tuple[float, float]
    severity: str  # high, medium, low
    suspected_cause: Optional[str] = None


@dataclass
class Insight:
    """Generated insight"""
    type: InsightType
    title: str
    description: str
    impact: str  # high, medium, low
    confidence: float
    supporting_data: Dict[str, Any] = field(default_factory=dict)


class ComparativeAnalyzer:
    """Analyze data for comparisons and trends"""
    
    def calculate_comparison(
        self,
        current: float,
        previous: float,
        metric_name: str = "value"
    ) -> Comparison:
        """Calculate comparison between two values"""
        
        change_absolute = current - previous
        change_percent = ((current - previous) / previous * 100) if previous != 0 else 0
        
        if change_percent > 5:
            direction = "up"
        elif change_percent < -5:
            direction = "down"
        else:
            direction = "flat"
        
        # Generate description
        if abs(change_percent) < 1:
            description = f"unchanged from previous"
        elif change_percent > 0:
            description = f"up {abs(change_percent):.1f}% vs previous"
        else:
            description = f"down {abs(change_percent):.1f}% vs previous"
        
        return Comparison(
            metric=metric_name,
            current_value=current,
            previous_value=previous,
            change_absolute=change_absolute,
            change_percent=change_percent,
            direction=direction,
            description=description
        )
    
    def calculate_trend(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """Calculate trend from a series of values"""
        
        if len(values) < 2:
            return {"trend": "insufficient_data"}
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        
        mean_x = sum(x) / n
        mean_y = sum(values) / n
        
        # Calculate slope
        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine trend direction
        if slope > 0.01 * mean_y:
            trend = "increasing"
        elif slope < -0.01 * mean_y:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Calculate growth rate
        if values[0] != 0:
            total_change = ((values[-1] - values[0]) / abs(values[0])) * 100
        else:
            total_change = 0
        
        # Calculate volatility (coefficient of variation)
        if mean_y != 0:
            cv = (statistics.stdev(values) / mean_y) * 100 if len(values) > 1 else 0
        else:
            cv = 0
        
        return {
            "trend": trend,
            "slope": slope,
            "total_change_percent": total_change,
            "volatility": cv,
            "start_value": values[0],
            "end_value": values[-1],
            "min_value": min(values),
            "max_value": max(values),
            "avg_value": mean_y
        }
    
    def compare_periods(
        self,
        current_period: List[DataPoint],
        previous_period: List[DataPoint],
        metric_name: str = "value"
    ) -> Comparison:
        """Compare two periods of data"""
        
        current_total = sum(dp.value for dp in current_period)
        previous_total = sum(dp.value for dp in previous_period)
        
        return self.calculate_comparison(current_total, previous_total, metric_name)


class AnomalyDetector:
    """Detect anomalies in data"""
    
    def detect_anomalies(
        self,
        values: List[float],
        labels: Optional[List[str]] = None,
        method: str = "iqr"
    ) -> List[Anomaly]:
        """Detect anomalies in a series of values"""
        
        if len(values) < 4:
            return []
        
        anomalies = []
        
        if method == "iqr":
            # Interquartile Range method
            sorted_values = sorted(values)
            q1 = statistics.median(sorted_values[:len(sorted_values)//2])
            q3 = statistics.median(sorted_values[len(sorted_values)//2:])
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for i, value in enumerate(values):
                if value < lower_bound or value > upper_bound:
                    severity = "high" if value < lower_bound - iqr or value > upper_bound + iqr else "medium"
                    
                    anomalies.append(Anomaly(
                        description=f"{'Low' if value < lower_bound else 'High'} value detected",
                        value=value,
                        expected_range=(lower_bound, upper_bound),
                        severity=severity,
                        suspected_cause=None
                    ))
        
        elif method == "zscore":
            # Z-score method
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            
            if stdev > 0:
                for i, value in enumerate(values):
                    zscore = abs((value - mean) / stdev)
                    
                    if zscore > 2:
                        severity = "high" if zscore > 3 else "medium"
                        
                        anomalies.append(Anomaly(
                            description=f"Unusual value (z-score: {zscore:.2f})",
                            value=value,
                            expected_range=(mean - 2*stdev, mean + 2*stdev),
                            severity=severity
                        ))
        
        return anomalies
    
    def detect_change_points(
        self,
        values: List[float],
        threshold: float = 0.2
    ) -> List[Dict]:
        """Detect significant change points in time series"""
        
        if len(values) < 3:
            return []
        
        change_points = []
        
        for i in range(1, len(values)):
            if values[i-1] != 0:
                change = (values[i] - values[i-1]) / abs(values[i-1])
                
                if abs(change) > threshold:
                    change_points.append({
                        "index": i,
                        "from_value": values[i-1],
                        "to_value": values[i],
                        "change_percent": change * 100,
                        "direction": "up" if change > 0 else "down"
                    })
        
        return change_points


class ResponseFormatter:
    """Format natural language responses with insights"""
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider or get_llm_provider()
        self.comparative_analyzer = ComparativeAnalyzer()
        self.anomaly_detector = AnomalyDetector()
    
    async def format_response(
        self,
        query: str,
        results: Dict[str, Any],
        previous_results: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Format a complete response with summary, insights, and follow-ups"""
        
        # Extract data points
        data_points = self._extract_data_points(results)
        
        # Generate insights
        insights = await self._generate_insights(
            query, results, data_points, previous_results
        )
        
        # Generate natural language summary
        summary = await self._generate_summary(
            query, results, insights, user_preferences
        )
        
        # Generate follow-up suggestions
        follow_ups = await self._generate_follow_ups(query, results, insights)
        
        return {
            "executive_summary": summary.get("executive_summary", ""),
            "detailed_response": summary.get("full_response", ""),
            "insights": [self._insight_to_dict(i) for i in insights],
            "comparisons": self._extract_comparisons(insights),
            "anomalies": self._extract_anomalies(insights),
            "follow_up_suggestions": follow_ups,
            "data_summary": {
                "total_rows": len(results.get("rows", [])),
                "columns": results.get("columns", []),
                "time_range": self._extract_time_range(results)
            }
        }
    
    def _extract_data_points(self, results: Dict[str, Any]) -> List[DataPoint]:
        """Extract data points from query results"""
        points = []
        rows = results.get("rows", [])
        
        for row in rows:
            if isinstance(row, dict):
                # Find numeric value
                for key, value in row.items():
                    if isinstance(value, (int, float)):
                        points.append(DataPoint(
                            value=float(value),
                            label=str(row.get(row.keys()[0], "")),
                            metadata=row
                        ))
                        break
        
        return points
    
    async def _generate_insights(
        self,
        query: str,
        results: Dict[str, Any],
        data_points: List[DataPoint],
        previous_results: Optional[Dict[str, Any]]
    ) -> List[Insight]:
        """Generate insights from data"""
        
        insights = []
        values = [dp.value for dp in data_points]
        
        if not values:
            return insights
        
        # Trend analysis
        if len(values) > 2:
            trend = self.comparative_analyzer.calculate_trend(values)
            
            if trend["trend"] != "stable":
                insights.append(Insight(
                    type=InsightType.TREND,
                    title=f"{trend['trend'].capitalize()} trend detected",
                    description=f"Values are {trend['trend']} with {abs(trend['total_change_percent']):.1f}% change overall",
                    impact="medium",
                    confidence=0.8,
                    supporting_data=trend
                ))
        
        # Anomaly detection
        anomalies = self.anomaly_detector.detect_anomalies(values)
        for anomaly in anomalies:
            insights.append(Insight(
                type=InsightType.ANOMALY,
                title=f"Anomaly: {anomaly.description}",
                description=f"Value {anomaly.value:.2f} is outside expected range ({anomaly.expected_range[0]:.2f} - {anomaly.expected_range[1]:.2f})",
                impact=anomaly.severity,
                confidence=0.75,
                supporting_data={
                    "value": anomaly.value,
                    "expected_range": anomaly.expected_range
                }
            ))
        
        # Comparison with previous results
        if previous_results:
            prev_points = self._extract_data_points(previous_results)
            prev_values = [dp.value for dp in prev_points]
            
            if values and prev_values:
                current_total = sum(values)
                prev_total = sum(prev_values)
                
                comparison = self.comparative_analyzer.calculate_comparison(
                    current_total, prev_total, "total"
                )
                
                insights.append(Insight(
                    type=InsightType.COMPARISON,
                    title=f"Period comparison: {comparison.description}",
                    description=f"Current period ({current_total:.2f}) vs previous ({prev_total:.2f})",
                    impact="high" if abs(comparison.change_percent) > 20 else "medium",
                    confidence=0.85,
                    supporting_data={
                        "current": current_total,
                        "previous": prev_total,
                        "change_percent": comparison.change_percent
                    }
                ))
        
        # Segmentation insight (if grouped data)
        rows = results.get("rows", [])
        if len(rows) > 1:
            total = sum(values)
            if total > 0:
                # Find largest segment
                max_idx = values.index(max(values))
                max_value = values[max_idx]
                max_share = (max_value / total) * 100
                
                if max_share > 50:
                    label = rows[max_idx].get(list(rows[max_idx].keys())[0], "One segment")
                    insights.append(Insight(
                        type=InsightType.SEGMENTATION,
                        title=f"{label} dominates with {max_share:.1f}%",
                        description=f"One segment accounts for more than half of the total",
                        impact="high",
                        confidence=0.9,
                        supporting_data={
                            "segment": label,
                            "share": max_share
                        }
                    ))
        
        # Use LLM for additional insights
        llm_insights = await self._get_llm_insights(query, results, insights)
        insights.extend(llm_insights)
        
        return insights
    
    async def _get_llm_insights(
        self,
        query: str,
        results: Dict[str, Any],
        existing_insights: List[Insight]
    ) -> List[Insight]:
        """Get additional insights from LLM"""
        
        try:
            prompt_template = get_prompt("insight_generator", PromptType.INSIGHT_GENERATION)
            
            prompt = prompt_template.render(
                query=query,
                results_summary=json.dumps({
                    "row_count": len(results.get("rows", [])),
                    "columns": results.get("columns", []),
                    "sample": results.get("rows", [])[:5]
                }),
                previous_results="",
                user_context="{}"
            )
            
            result = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt="Generate insightful, actionable observations from data."
            )
            
            llm_insights = []
            for i in result.get("key_insights", []):
                try:
                    insight_type = InsightType(i.get("type", "recommendation"))
                except ValueError:
                    insight_type = InsightType.RECOMMENDATION
                
                llm_insights.append(Insight(
                    type=insight_type,
                    title=i.get("title", ""),
                    description=i.get("description", ""),
                    impact=i.get("impact", "medium"),
                    confidence=i.get("confidence", 0.5)
                ))
            
            return llm_insights
            
        except Exception:
            return []
    
    async def _generate_summary(
        self,
        query: str,
        results: Dict[str, Any],
        insights: List[Insight],
        user_preferences: Optional[Dict]
    ) -> Dict[str, str]:
        """Generate natural language summary"""
        
        try:
            prompt_template = get_prompt("response_formatter", PromptType.RESPONSE_FORMATTING)
            
            prompt = prompt_template.render(
                query=query,
                results=json.dumps({
                    "rows": results.get("rows", [])[:10],
                    "columns": results.get("columns", [])
                }),
                insights=json.dumps([self._insight_to_dict(i) for i in insights]),
                viz_config="{}",
                user_preferences=json.dumps(user_preferences or {})
            )
            
            result = await self.llm_provider.generate_json(
                prompt=prompt,
                system_prompt="Write clear, concise responses for analytics queries."
            )
            
            return {
                "executive_summary": result.get("executive_summary", ""),
                "full_response": result.get("full_response", "")
            }
            
        except Exception as e:
            # Fallback summary
            rows = results.get("rows", [])
            return {
                "executive_summary": f"Query returned {len(rows)} results.",
                "full_response": f"I found {len(rows)} results for your query."
            }
    
    async def _generate_follow_ups(
        self,
        query: str,
        results: Dict[str, Any],
        insights: List[Insight]
    ) -> List[Dict]:
        """Generate follow-up question suggestions"""
        
        follow_ups = []
        
        # Based on insights
        for insight in insights:
            if insight.type == InsightType.TREND:
                follow_ups.append({
                    "question": "What factors contributed to this trend?",
                    "type": "drill_down"
                })
            elif insight.type == InsightType.COMPARISON:
                follow_ups.append({
                    "question": "How does this compare to the same period last year?",
                    "type": "comparison"
                })
            elif insight.type == InsightType.ANOMALY:
                follow_ups.append({
                    "question": "What caused this anomaly?",
                    "type": "investigate"
                })
        
        # Generic follow-ups
        rows = results.get("rows", [])
        if len(rows) > 0:
            follow_ups.extend([
                {"question": "Can you break this down by category?", "type": "breakdown"},
                {"question": "Show me this over time", "type": "trend"},
                {"question": "What are the top 10 items?", "type": "ranking"}
            ])
        
        # Remove duplicates and limit
        seen = set()
        unique = []
        for f in follow_ups:
            if f["question"] not in seen:
                seen.add(f["question"])
                unique.append(f)
        
        return unique[:5]
    
    def _insight_to_dict(self, insight: Insight) -> Dict:
        """Convert insight to dictionary"""
        return {
            "type": insight.type.value,
            "title": insight.title,
            "description": insight.description,
            "impact": insight.impact,
            "confidence": insight.confidence,
            "supporting_data": insight.supporting_data
        }
    
    def _extract_comparisons(self, insights: List[Insight]) -> List[Dict]:
        """Extract comparison insights"""
        return [
            self._insight_to_dict(i) for i in insights
            if i.type == InsightType.COMPARISON
        ]
    
    def _extract_anomalies(self, insights: List[Insight]) -> List[Dict]:
        """Extract anomaly insights"""
        return [
            self._insight_to_dict(i) for i in insights
            if i.type == InsightType.ANOMALY
        ]
    
    def _extract_time_range(self, results: Dict[str, Any]) -> Optional[str]:
        """Extract time range from results if present"""
        # This would parse date columns
        return None


# Global instance
_formatter: Optional[ResponseFormatter] = None


def get_response_formatter() -> ResponseFormatter:
    """Get global response formatter instance"""
    global _formatter
    if _formatter is None:
        _formatter = ResponseFormatter()
    return _formatter


# Convenience functions
async def format_query_response(
    query: str,
    results: Dict[str, Any],
    previous_results: Optional[Dict[str, Any]] = None,
    user_preferences: Optional[Dict] = None
) -> Dict[str, Any]:
    """Format a complete response for a query"""
    formatter = get_response_formatter()
    return await formatter.format_response(
        query, results, previous_results, user_preferences
    )


async def generate_insights(
    query: str,
    results: Dict[str, Any],
    previous_results: Optional[Dict[str, Any]] = None
) -> List[Dict]:
    """Generate insights from query results"""
    formatter = get_response_formatter()
    data_points = formatter._extract_data_points(results)
    insights = await formatter._generate_insights(query, results, data_points, previous_results)
    return [formatter._insight_to_dict(i) for i in insights]
