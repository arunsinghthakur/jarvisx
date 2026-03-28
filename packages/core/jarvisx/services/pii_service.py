import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import or_

from jarvisx.database.models import PIIPattern, ComplianceConfig

logger = logging.getLogger(__name__)


class PIISensitivity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PIIMaskStyle(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    HASH = "hash"


@dataclass
class PIIMatch:
    pattern_name: str
    category: str
    sensitivity: str
    original_value: str
    masked_value: str
    start_position: int
    end_position: int


@dataclass
class PIIScanResult:
    has_pii: bool
    matches: List[PIIMatch]
    categories_found: List[str]
    sensitivity_levels: List[str]
    original_text: str
    masked_text: str


class PIIService:
    def __init__(self, db: Session):
        self.db = db
        self._pattern_cache: Dict[str, List[PIIPattern]] = {}
    
    def get_patterns(self, organization_id: Optional[str] = None) -> List[PIIPattern]:
        cache_key = organization_id or "system"
        if cache_key in self._pattern_cache:
            return self._pattern_cache[cache_key]
        
        query = self.db.query(PIIPattern).filter(PIIPattern.is_active == True)
        
        if organization_id:
            query = query.filter(
                or_(
                    PIIPattern.is_system_pattern == True,
                    PIIPattern.organization_id == organization_id
                )
            )
        else:
            query = query.filter(PIIPattern.is_system_pattern == True)
        
        patterns = query.order_by(PIIPattern.category, PIIPattern.name).all()
        self._pattern_cache[cache_key] = patterns
        return patterns
    
    def get_compliance_config(self, organization_id: str) -> Optional[ComplianceConfig]:
        return self.db.query(ComplianceConfig).filter(
            ComplianceConfig.organization_id == organization_id
        ).first()
    
    def _mask_value(self, value: str, mask_char: str, mask_style: str) -> str:
        if not value:
            return value
        
        if mask_style == PIIMaskStyle.FULL:
            return mask_char * len(value)
        elif mask_style == PIIMaskStyle.PARTIAL:
            if len(value) <= 4:
                return mask_char * len(value)
            visible_chars = min(4, len(value) // 4)
            return value[:visible_chars] + mask_char * (len(value) - visible_chars * 2) + value[-visible_chars:]
        elif mask_style == PIIMaskStyle.HASH:
            import hashlib
            return f"[HASH:{hashlib.sha256(value.encode()).hexdigest()[:8]}]"
        else:
            return mask_char * len(value)
    
    def _should_process(self, organization_id: Optional[str], sensitivity_level: str) -> bool:
        if not organization_id:
            return True
        
        config = self.get_compliance_config(organization_id)
        if not config or not config.pii_detection_enabled:
            return False
        
        sensitivity_order = {PIISensitivity.LOW: 1, PIISensitivity.MEDIUM: 2, PIISensitivity.HIGH: 3}
        config_level = sensitivity_order.get(config.pii_sensitivity_level, 2)
        pattern_level = sensitivity_order.get(sensitivity_level, 2)
        
        return pattern_level >= config_level
    
    def scan(self, text: str, organization_id: Optional[str] = None) -> PIIScanResult:
        if not text:
            return PIIScanResult(
                has_pii=False,
                matches=[],
                categories_found=[],
                sensitivity_levels=[],
                original_text=text,
                masked_text=text
            )
        
        patterns = self.get_patterns(organization_id)
        matches: List[PIIMatch] = []
        categories_found: set = set()
        sensitivity_levels: set = set()
        
        for pattern in patterns:
            if not self._should_process(organization_id, pattern.sensitivity):
                continue
            
            try:
                regex = re.compile(pattern.pattern_regex, re.IGNORECASE)
                for match in regex.finditer(text):
                    original_value = match.group()
                    masked_value = self._mask_value(
                        original_value, 
                        pattern.mask_char, 
                        pattern.mask_style
                    )
                    
                    pii_match = PIIMatch(
                        pattern_name=pattern.name,
                        category=pattern.category,
                        sensitivity=pattern.sensitivity,
                        original_value=original_value,
                        masked_value=masked_value,
                        start_position=match.start(),
                        end_position=match.end()
                    )
                    matches.append(pii_match)
                    categories_found.add(pattern.category)
                    sensitivity_levels.add(pattern.sensitivity)
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern.name}': {e}")
                continue
        
        matches.sort(key=lambda m: m.start_position, reverse=True)
        
        masked_text = text
        for match in matches:
            masked_text = (
                masked_text[:match.start_position] + 
                match.masked_value + 
                masked_text[match.end_position:]
            )
        
        return PIIScanResult(
            has_pii=len(matches) > 0,
            matches=matches,
            categories_found=list(categories_found),
            sensitivity_levels=list(sensitivity_levels),
            original_text=text,
            masked_text=masked_text
        )
    
    def mask(self, text: str, organization_id: Optional[str] = None) -> str:
        result = self.scan(text, organization_id)
        return result.masked_text
    
    def detect(self, text: str, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = self.scan(text, organization_id)
        return [
            {
                "pattern_name": m.pattern_name,
                "category": m.category,
                "sensitivity": m.sensitivity,
                "value": m.original_value,
                "position": {"start": m.start_position, "end": m.end_position}
            }
            for m in result.matches
        ]
    
    def classify(self, text: str, organization_id: Optional[str] = None) -> Dict[str, Any]:
        result = self.scan(text, organization_id)
        
        category_counts: Dict[str, int] = {}
        sensitivity_counts: Dict[str, int] = {}
        
        for match in result.matches:
            category_counts[match.category] = category_counts.get(match.category, 0) + 1
            sensitivity_counts[match.sensitivity] = sensitivity_counts.get(match.sensitivity, 0) + 1
        
        max_sensitivity = PIISensitivity.LOW
        if PIISensitivity.HIGH in sensitivity_counts:
            max_sensitivity = PIISensitivity.HIGH
        elif PIISensitivity.MEDIUM in sensitivity_counts:
            max_sensitivity = PIISensitivity.MEDIUM
        
        return {
            "has_pii": result.has_pii,
            "total_matches": len(result.matches),
            "max_sensitivity": max_sensitivity,
            "categories": category_counts,
            "sensitivities": sensitivity_counts,
            "risk_level": "high" if max_sensitivity == PIISensitivity.HIGH else (
                "medium" if max_sensitivity == PIISensitivity.MEDIUM else "low"
            )
        }
    
    def get_report(self, text: str, organization_id: Optional[str] = None) -> Dict[str, Any]:
        result = self.scan(text, organization_id)
        classification = self.classify(text, organization_id)
        
        return {
            "summary": {
                "has_pii": result.has_pii,
                "total_pii_found": len(result.matches),
                "categories_found": result.categories_found,
                "risk_level": classification["risk_level"],
                "max_sensitivity": classification["max_sensitivity"]
            },
            "details": [
                {
                    "type": m.pattern_name,
                    "category": m.category,
                    "sensitivity": m.sensitivity,
                    "location": f"characters {m.start_position}-{m.end_position}",
                    "masked_value": m.masked_value
                }
                for m in result.matches
            ],
            "masked_text": result.masked_text,
            "recommendations": self._get_recommendations(result)
        }
    
    def _get_recommendations(self, result: PIIScanResult) -> List[str]:
        recommendations = []
        
        if not result.has_pii:
            return ["No PII detected. Text appears safe for processing."]
        
        if PIISensitivity.HIGH in result.sensitivity_levels:
            recommendations.append("HIGH SENSITIVITY: Contains highly sensitive PII. Consider additional encryption and access controls.")
        
        if "government_id" in result.categories_found:
            recommendations.append("Government IDs detected. Ensure compliance with data protection regulations.")
        
        if "financial" in result.categories_found:
            recommendations.append("Financial data detected. Ensure PCI-DSS compliance if processing payment information.")
        
        if "contact" in result.categories_found:
            recommendations.append("Contact information detected. Verify consent for processing under GDPR/CCPA.")
        
        recommendations.append(f"Total of {len(result.matches)} PII instances found. Use masked version for logging and non-essential processing.")
        
        return recommendations
    
    def clear_cache(self):
        self._pattern_cache.clear()
