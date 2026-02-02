"""Simple task clarity checker - validates and requests rewrite if needed."""

from typing import Dict, List, Optional


class TaskClarityChecker:
    """Simple checker: pass or request rewrite with template."""
    
    # Minimum requirements
    MIN_TITLE_LENGTH = 10
    MIN_DESCRIPTION_LENGTH = 50
    
    # Vague terms to avoid
    VAGUE_TERMS = ["etc", "something", "somehow", "maybe", "probably", "asap", "soon", "whatever", "stuff"]
    
    def check_and_feedback(self, task_data: Dict) -> Dict:
        """
        Check task and return either:
        - {"passed": True} if clear enough
        - {"passed": False, "feedback": "...", "template": "..."} if needs rewrite
        """
        issues = []
        
        title = task_data.get("title", "")
        description = task_data.get("description", "")
        
        # Check 1: Title length
        if len(title) < self.MIN_TITLE_LENGTH:
            issues.append(f"Title too short ({len(title)} chars, need {self.MIN_TITLE_LENGTH}+)")
        
        # Check 2: Description length  
        if len(description) < self.MIN_DESCRIPTION_LENGTH:
            issues.append(f"Description too short ({len(description)} chars, need {self.MIN_DESCRIPTION_LENGTH}+)")
        
        # Check 3: Vague terms
        found_vague = [term for term in self.VAGUE_TERMS if term in description.lower()]
        if found_vague:
            issues.append(f"Avoid vague terms: {', '.join(found_vague)}")
        
        # Check 4: Has some structure (bullet points or sections)
        has_structure = any(marker in description for marker in ["\n-", "\n*", "1.", "2.", "**", "###"])
        if not has_structure:
            issues.append("Use bullet points or sections to organize requirements")
        
        # Passed all checks
        if not issues:
            return {"passed": True}
        
        # Needs rewrite - provide feedback and template
        feedback = self._generate_feedback(issues)
        template = self._generate_template(task_data)
        
        return {
            "passed": False,
            "issues": issues,
            "feedback": feedback,
            "template": template
        }
    
    def _generate_feedback(self, issues: List[str]) -> str:
        """Generate human-readable feedback."""
        lines = ["Your task needs some clarification:"]
        for issue in issues:
            lines.append(f"  • {issue}")
        lines.append("")
        lines.append("Please rewrite following the template below.")
        return "\n".join(lines)
    
    def _generate_template(self, task_data: Dict) -> str:
        """Generate a template for the publisher to fill in."""
        title = task_data.get("title", "[Action] + [What] + [Context]")
        
        template = f"""# {title}

## Objective
[What problem does this solve? Why is it needed? Be specific.]

## Requirements
- Technology: [e.g., Python, FastAPI, React]
- Constraints: [e.g., must work offline, max 100ms response]
- Dependencies: [what it integrates with]

## Acceptance Criteria (Definition of Done)
- [ ] [Specific deliverable 1: e.g., "API endpoint returns JSON with fields X, Y, Z"]
- [ ] [Specific deliverable 2: e.g., "All tests pass with >80% coverage"]
- [ ] [Specific deliverable 3: e.g., "Documentation includes usage examples"]

## Example (Input → Output)
**Input:** [Provide a concrete example]
**Expected Output:** [Show what success looks like]

## Notes for Worker
- Estimated effort: [X] hours
- Priority: [High/Medium/Low]
- References: [links to docs, similar implementations, etc.]

---
**Tip:** The more specific you are, the better results you'll get. Avoid words like "etc", "something", "asap"."""
        
        return template


# Simple validation function for API
def validate_task_or_feedback(task_data: Dict) -> Optional[Dict]:
    """
    Validate task and return feedback if needed.
    Returns None if task is clear enough, otherwise returns feedback dict.
    """
    checker = TaskClarityChecker()
    result = checker.check_and_feedback(task_data)
    
    if result["passed"]:
        return None
    
    return {
        "error": "Task needs clarification",
        "feedback": result["feedback"],
        "issues": result["issues"],
        "template": result["template"],
        "action": "Please rewrite your task using the template and try again"
    }
