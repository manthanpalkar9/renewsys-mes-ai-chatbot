import re
from dataclasses import dataclass
from typing import Optional

PROHIBITED_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter",
    "truncate", "create", "grant", "revoke", "replace",
    "merge", "upsert", "exec", "execute", "xp_cmd",
    "sp_executesql", "openrowset", "opendatasource",
    "bulk", "load data", "into outfile",
]

@dataclass
class SafetyCheckResult:
    is_safe: bool
    violations: list[str]
    warnings: list[str]
    sanitized_sql: Optional[str] = None
    safety_note: str = "PROPOSED TECHNICAL SAFETY CONTROL"

class SQLSafetyService:
    MAX_SQL_LENGTH = 5000
    MAX_JOINS = 10

    def validate(self, sql: str) -> SafetyCheckResult:
        violations = []
        warnings = []
        if not sql or not sql.strip(): return SafetyCheckResult(False, ["Empty SQL statement"], [])
        if len(sql) > self.MAX_SQL_LENGTH: warnings.append("SQL exceeds max length")
        sql_lower = sql.lower().strip()
        sql_no_comments = re.sub(r'--[^\n]*', '', sql_lower)
        sql_no_comments = re.sub(r'/\*.*?\*/', '', sql_no_comments, flags=re.DOTALL).strip()
        first_token = sql_no_comments.split()[0] if sql_no_comments.split() else ""
        if first_token != "select": violations.append("SQL must start with SELECT.")
        for keyword in PROHIBITED_KEYWORDS:
            pattern = rf'(?:^|\s|;){re.escape(keyword)}(?:\s|\(|;|$)'
            if re.search(pattern, sql_no_comments):
                violations.append(f"Prohibited keyword '{keyword}' detected.")
        statements = [s.strip() for s in sql_no_comments.split(";") if s.strip()]
        if len(statements) > 1: violations.append("Multiple SQL statements detected.")
        join_count = len(re.findall(r'\bjoin\b', sql_no_comments))
        if join_count > self.MAX_JOINS: warnings.append("High number of JOINs")
        is_safe = len(violations) == 0
        sanitized = sql if is_safe else None
        return SafetyCheckResult(is_safe, violations, warnings, sanitized)

sql_safety_service = SQLSafetyService()
