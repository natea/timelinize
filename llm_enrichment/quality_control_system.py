"""
Quality Control and Validation System for Timelinize LLM Enrichments

This module implements comprehensive quality control mechanisms to ensure
the accuracy, consistency, and reliability of LLM-generated enrichments.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re
from datetime import datetime
import json


# Quality Control Levels
class QualityLevel(Enum):
    HIGH = "high"        # Passes all checks with high confidence
    MEDIUM = "medium"    # Passes most checks, minor issues
    LOW = "low"          # Significant issues found
    FAILED = "failed"    # Critical issues, should not be used


# Validation Results
@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]


@dataclass
class QualityReport:
    """Overall quality report for an enrichment"""
    enrichment_id: int
    overall_level: QualityLevel
    overall_score: float
    validation_results: List[ValidationResult]
    timestamp: datetime
    recommendations: List[str]


# Abstract Base Classes
class Validator(ABC):
    """Abstract base class for validators"""
    
    @abstractmethod
    def validate(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate an enrichment and return results"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return validator name"""
        pass


# Content Validators
class LengthValidator(Validator):
    """Validates appropriate length of generated content"""
    
    def __init__(self, min_length: int = 10, max_length: int = 1000):
        self.min_length = min_length
        self.max_length = max_length
    
    def get_name(self) -> str:
        return "content_length"
    
    def validate(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        content = enrichment.get("content", "")
        length = len(content)
        
        issues = []
        suggestions = []
        
        if length < self.min_length:
            issues.append(f"Content too short ({length} chars, minimum {self.min_length})")
            suggestions.append("Consider requesting more detailed enrichment")
            score = length / self.min_length
        elif length > self.max_length:
            issues.append(f"Content too long ({length} chars, maximum {self.max_length})")
            suggestions.append("Consider summarizing or splitting content")
            score = self.max_length / length
        else:
            score = 1.0
        
        return ValidationResult(
            check_name=self.get_name(),
            passed=len(issues) == 0,
            score=score,
            issues=issues,
            suggestions=suggestions,
            metadata={"length": length}
        )


class CoherenceValidator(Validator):
    """Validates semantic coherence and relevance"""
    
    def get_name(self) -> str:
        return "coherence"
    
    def validate(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        content = enrichment.get("content", "")
        original_text = context.get("original_text", "")
        
        issues = []
        score = 1.0
        
        # Check for common coherence issues
        if content.count("...") > 3:
            issues.append("Excessive ellipses detected")
            score -= 0.1
        
        if re.search(r'\b(\w+)\s+\1\b', content):
            issues.append("Repeated words detected")
            score -= 0.1
        
        # Check relevance to original content
        if original_text:
            original_words = set(original_text.lower().split())
            enrichment_words = set(content.lower().split())
            overlap = len(original_words & enrichment_words) / max(len(original_words), 1)
            
            if overlap < 0.1:
                issues.append("Low relevance to original content")
                score -= 0.3
        
        return ValidationResult(
            check_name=self.get_name(),
            passed=score > 0.7,
            score=max(0, score),
            issues=issues,
            suggestions=["Review enrichment for relevance"] if issues else [],
            metadata={"coherence_score": score}
        )


class FactualConsistencyValidator(Validator):
    """Validates factual consistency with source data"""
    
    def get_name(self) -> str:
        return "factual_consistency"
    
    def validate(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        content = enrichment.get("content", "")
        original_data = context.get("original_data", {})
        
        issues = []
        score = 1.0
        
        # Check dates
        date_pattern = r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b'
        enrichment_dates = re.findall(date_pattern, content)
        
        if original_data.get("timestamp"):
            original_date = datetime.fromtimestamp(original_data["timestamp"] / 1000)
            for date_str in enrichment_dates:
                # Simple date validation - would be more sophisticated in production
                if str(original_date.year) not in date_str:
                    issues.append(f"Potential date inconsistency: {date_str}")
                    score -= 0.2
        
        # Check for hallucinated information
        suspicious_phrases = [
            "it is known that",
            "studies show",
            "research indicates",
            "experts say"
        ]
        
        for phrase in suspicious_phrases:
            if phrase in content.lower():
                issues.append(f"Potential hallucination indicator: '{phrase}'")
                score -= 0.1
        
        return ValidationResult(
            check_name=self.get_name(),
            passed=score > 0.7,
            score=max(0, score),
            issues=issues,
            suggestions=["Verify factual claims"] if issues else [],
            metadata={"detected_dates": enrichment_dates}
        )


# Theme Validators
class ThemeConsistencyValidator(Validator):
    """Validates theme assignments are consistent and appropriate"""
    
    def __init__(self, theme_taxonomy: Dict[str, Any]):
        self.theme_taxonomy = theme_taxonomy
    
    def get_name(self) -> str:
        return "theme_consistency"
    
    def validate(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        themes = enrichment.get("themes", [])
        
        issues = []
        score = 1.0
        
        if not themes:
            issues.append("No themes assigned")
            score = 0.0
        else:
            # Check confidence distribution
            confidences = [t.get("confidence", 0) for t in themes]
            
            if max(confidences) < 0.5:
                issues.append("All theme confidences are low")
                score -= 0.3
            
            if len(themes) > 5:
                issues.append(f"Too many themes assigned ({len(themes)})")
                score -= 0.2
            
            # Check for conflicting themes
            theme_ids = [t.get("theme_id") for t in themes]
            if self._has_conflicting_themes(theme_ids):
                issues.append("Conflicting themes detected")
                score -= 0.3
        
        return ValidationResult(
            check_name=self.get_name(),
            passed=score > 0.6,
            score=max(0, score),
            issues=issues,
            suggestions=["Review theme assignments"] if issues else [],
            metadata={"theme_count": len(themes)}
        )
    
    def _has_conflicting_themes(self, theme_ids: List[int]) -> bool:
        # Define conflicting theme pairs
        conflicts = [
            (101, 201),  # Work meetings vs Family events
            (302, 304),  # Fitness vs Nutrition (not conflicting, just example)
        ]
        
        for id1, id2 in conflicts:
            if id1 in theme_ids and id2 in theme_ids:
                return True
        return False


# Format Validators
class JSONFormatValidator(Validator):
    """Validates JSON format for structured outputs"""
    
    def get_name(self) -> str:
        return "json_format"
    
    def validate(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        content = enrichment.get("content", "")
        expected_format = context.get("expected_format", "text")
        
        if expected_format != "json":
            return ValidationResult(
                check_name=self.get_name(),
                passed=True,
                score=1.0,
                issues=[],
                suggestions=[],
                metadata={}
            )
        
        issues = []
        score = 1.0
        
        try:
            parsed = json.loads(content)
            
            # Check for expected fields
            required_fields = context.get("required_fields", [])
            for field in required_fields:
                if field not in parsed:
                    issues.append(f"Missing required field: {field}")
                    score -= 0.2
            
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON: {str(e)}")
            score = 0.0
        
        return ValidationResult(
            check_name=self.get_name(),
            passed=score > 0.8,
            score=max(0, score),
            issues=issues,
            suggestions=["Fix JSON formatting"] if issues else [],
            metadata={}
        )


# Confidence Validators
class ConfidenceCalibrationValidator(Validator):
    """Validates that confidence scores are well-calibrated"""
    
    def get_name(self) -> str:
        return "confidence_calibration"
    
    def validate(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        confidence = enrichment.get("confidence_score", 0)
        content_length = len(enrichment.get("content", ""))
        
        issues = []
        score = 1.0
        
        # Check if confidence matches content quality indicators
        if confidence > 0.9 and content_length < 50:
            issues.append("High confidence with minimal content")
            score -= 0.3
        
        if confidence < 0.3:
            issues.append("Very low confidence - consider re-processing")
            score -= 0.2
        
        # Check confidence distribution across batch
        batch_confidences = context.get("batch_confidences", [])
        if batch_confidences and len(batch_confidences) > 10:
            avg_confidence = sum(batch_confidences) / len(batch_confidences)
            if abs(confidence - avg_confidence) > 0.4:
                issues.append("Confidence significantly differs from batch average")
                score -= 0.1
        
        return ValidationResult(
            check_name=self.get_name(),
            passed=score > 0.7,
            score=max(0, score),
            issues=issues,
            suggestions=["Review confidence scoring"] if issues else [],
            metadata={"confidence": confidence}
        )


# Main Quality Control System
class QualityControlSystem:
    """Main system for quality control and validation"""
    
    def __init__(self):
        self.validators: List[Validator] = []
        self.thresholds = {
            QualityLevel.HIGH: 0.9,
            QualityLevel.MEDIUM: 0.7,
            QualityLevel.LOW: 0.5,
            QualityLevel.FAILED: 0.0
        }
    
    def register_validator(self, validator: Validator):
        """Register a validator"""
        self.validators.append(validator)
    
    def validate_enrichment(self, enrichment: Dict[str, Any], context: Dict[str, Any]) -> QualityReport:
        """Validate an enrichment and generate quality report"""
        validation_results = []
        total_score = 0
        total_weight = 0
        
        for validator in self.validators:
            try:
                result = validator.validate(enrichment, context)
                validation_results.append(result)
                
                # Weight by validator importance
                weight = self._get_validator_weight(validator)
                total_score += result.score * weight
                total_weight += weight
                
            except Exception as e:
                # Handle validator errors gracefully
                validation_results.append(
                    ValidationResult(
                        check_name=validator.get_name(),
                        passed=False,
                        score=0.0,
                        issues=[f"Validator error: {str(e)}"],
                        suggestions=["Fix validator implementation"],
                        metadata={}
                    )
                )
        
        overall_score = total_score / total_weight if total_weight > 0 else 0.0
        overall_level = self._determine_quality_level(overall_score)
        recommendations = self._generate_recommendations(validation_results)
        
        return QualityReport(
            enrichment_id=enrichment.get("id", 0),
            overall_level=overall_level,
            overall_score=overall_score,
            validation_results=validation_results,
            timestamp=datetime.now(),
            recommendations=recommendations
        )
    
    def _get_validator_weight(self, validator: Validator) -> float:
        """Get weight for a validator (some are more important)"""
        weights = {
            "factual_consistency": 2.0,
            "coherence": 1.5,
            "theme_consistency": 1.5,
            "content_length": 1.0,
            "json_format": 1.0,
            "confidence_calibration": 0.8
        }
        return weights.get(validator.get_name(), 1.0)
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score"""
        for level in [QualityLevel.HIGH, QualityLevel.MEDIUM, QualityLevel.LOW]:
            if score >= self.thresholds[level]:
                return level
        return QualityLevel.FAILED
    
    def _generate_recommendations(self, results: List[ValidationResult]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        failed_checks = [r for r in results if not r.passed]
        if len(failed_checks) > 3:
            recommendations.append("Consider re-processing with improved prompts")
        
        for result in failed_checks:
            recommendations.extend(result.suggestions)
        
        return list(set(recommendations))  # Remove duplicates


# Human Review System
class HumanReviewQueue:
    """Manages items requiring human review"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.review_threshold = QualityLevel.LOW
    
    async def add_for_review(self, enrichment_id: int, quality_report: QualityReport):
        """Add an enrichment to human review queue"""
        if quality_report.overall_level.value <= self.review_threshold.value:
            await self.db.execute(
                """
                INSERT INTO human_review_queue 
                (enrichment_id, quality_level, quality_score, issues, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    enrichment_id,
                    quality_report.overall_level.value,
                    quality_report.overall_score,
                    json.dumps([r.issues for r in quality_report.validation_results if r.issues]),
                    self._calculate_priority(quality_report),
                    datetime.now()
                ]
            )
    
    def _calculate_priority(self, report: QualityReport) -> int:
        """Calculate review priority (1-5, 5 being highest)"""
        if report.overall_level == QualityLevel.FAILED:
            return 5
        elif report.overall_level == QualityLevel.LOW:
            return 3
        else:
            return 1


# Continuous Improvement System
class QualityMetricsCollector:
    """Collects metrics for continuous improvement"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def record_validation(self, report: QualityReport):
        """Record validation metrics"""
        for result in report.validation_results:
            key = f"{result.check_name}_score"
            if key not in self.metrics:
                self.metrics[key] = []
            self.metrics[key].append(result.score)
    
    def get_insights(self) -> Dict[str, Any]:
        """Generate insights from collected metrics"""
        insights = {}
        
        for metric, values in self.metrics.items():
            if values:
                insights[metric] = {
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "failing_rate": len([v for v in values if v < 0.7]) / len(values)
                }
        
        return insights