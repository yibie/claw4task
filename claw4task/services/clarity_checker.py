"""Task clarity checker - validates and improves task descriptions."""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ClarityCheckResult:
    """Result of clarity check."""
    score: int  # 0-100
    is_clear: bool
    issues: List[str]
    suggestions: List[str]
    improved_description: Optional[str] = None


class TaskClarityChecker:
    """Checks task clarity and provides feedback or auto-rewrite."""
    
    MIN_ACCEPTABLE_SCORE = 60
    GOOD_SCORE = 80
    
    def check_clarity(self, task_data: Dict) -> ClarityCheckResult:
        """Check task clarity and return result."""
        issues = []
        suggestions = []
        score = 0
        
        # Check title
        title = task_data.get("title", "")
        if len(title) < 10:
            issues.append("Title is too short")
            suggestions.append("Expand title to clearly describe the deliverable")
        else:
            score += 15
            
        action_words = ["build", "create", "fix", "optimize", "implement", "write"]
        if any(word in title.lower() for word in action_words):
            score += 5
        
        # Check description
        description = task_data.get("description", "")
        if len(description) < 50:
            issues.append("Description is too brief")
            suggestions.append("Add more context about what needs to be done")
        else:
            score += 20
            
        # Check for vague terms
        vague_terms = ["etc", "something", "somehow", "maybe"]
        if any(term in description.lower() for term in vague_terms):
            issues.append("Description contains vague terms")
            suggestions.append("Replace vague terms with specific details")
        else:
            score += 5
        
        # Check requirements
        requirements = task_data.get("requirements", {})
        if not requirements:
            issues.append("No technical requirements specified")
            suggestions.append("Add requirements: technology stack, constraints")
        else:
            score += 15
        
        # Check acceptance criteria
        criteria = task_data.get("acceptance_criteria", {})
        if not criteria:
            issues.append("No acceptance criteria defined")
            suggestions.append("Define what 'done' means")
        else:
            score += 15
        
        # Check examples
        if task_data.get("examples"):
            score += 10
        else:
            suggestions.append("Consider adding input/output examples")
        
        # Check estimated hours
        if task_data.get("estimated_hours"):
            score += 10
        else:
            suggestions.append("Add estimated hours")
        
        is_clear = score >= self.MIN_ACCEPTABLE_SCORE
        
        improved = None
        if not is_clear:
            improved = self._rewrite_description(task_data, issues)
        
        return ClarityCheckResult(
            score=min(score, 100),
            is_clear=is_clear,
            issues=issues,
            suggestions=suggestions,
            improved_description=improved
        )
    
    def _rewrite_description(self, task_data: Dict, issues: List[str]) -> str:
        """Generate improved description."""
        title = task_data.get("title", "")
        description = task_data.get("description", "")
        
        parts = [f"**{title}**\n\n"]
        parts.append(f"**Objective:** {description}\n\n")
        
        if "requirements" in str(issues).lower():
            parts.append("**Requirements:**\n")
            parts.append("- Technology stack: [specify]\n")
            parts.append("- Performance criteria: [specify]\n\n")
        
        if "acceptance" in str(issues).lower():
            parts.append("**Acceptance Criteria:**\n")
            parts.append("- [ ] [Specific deliverable]\n")
            parts.append("- [ ] Tests pass\n\n")
        
        parts.append("**Notes:**\n")
        parts.append("- Estimated effort: [X] hours\n")
        parts.append("- Priority: [High/Medium/Low]")
        
        return "".join(parts)
