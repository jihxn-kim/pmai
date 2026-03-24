CODE_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "score": {"type": "integer", "minimum": 1, "maximum": 10},
        "file_comments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "comment": {"type": "string"},
                    "severity": {"type": "string", "enum": ["critical", "warning", "info"]}
                },
                "required": ["file", "line", "comment", "severity"]
            }
        },
        "overall_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["type", "description", "priority"]
            }
        }
    },
    "required": ["summary", "score", "file_comments", "overall_issues"]
}

PROJECT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "progress_assessment": {"type": "string"},
        "progress_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "delays": {"type": "array", "items": {"type": "object"}},
        "risks": {"type": "array", "items": {"type": "object"}},
        "recommendations": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["progress_assessment", "progress_score", "delays", "risks", "recommendations"]
}

TEST_SCENARIO_SCHEMA = {
    "type": "object",
    "properties": {
        "test_scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string", "enum": ["happy_path", "edge_case", "error_case"]},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "expected_result": {"type": "string"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["name", "description", "category", "steps", "expected_result", "priority"]
            }
        }
    },
    "required": ["test_scenarios"]
}

BRIEFING_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "completed_tasks": {"type": "integer"},
        "merged_prs": {"type": "integer"},
        "in_progress": {"type": "array", "items": {"type": "string"}},
        "delayed_items": {"type": "array", "items": {"type": "object"}},
        "risk_analysis": {"type": "string"},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "workload_per_member": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["summary", "completed_tasks", "merged_prs"]
}
