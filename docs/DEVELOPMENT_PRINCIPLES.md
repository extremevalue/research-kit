# Development Principles

Non-negotiable rules for building and maintaining the Research Validation System.

---

## 1. CLI is the Only Interface

All interactions go through the `research` CLI. No direct file edits. No internal script calls.

**Why:** The CLI validates schemas, enforces gates, maintains audit trails. Bypassing it breaks everything.

**Enforced by:** Skill with `allowed-tools: Bash, Read, Glob, Grep` (no Write/Edit).

---

## 2. Deterministic Code for Decisions

Testing, validation, and gate decisions are made by deterministic code, not LLM judgment.

| LLM Does | LLM Does NOT |
|----------|--------------|
| Extract metadata from documents | Decide if p-value is "good enough" |
| Interpret results (personas) | Skip data audit because "it looks fine" |
| Generate reports | Override gate failures |
| Suggest improvements | Modify parameters after seeing results |

---

## 3. Schema Validation on All Writes

Every write to catalog, validations, or data-registry is validated against JSON Schema.

```python
validate_against_schema(data, "catalog-entry.schema.json")  # Throws if invalid
write_to_disk(data)
```

---

## 4. Gates Cannot Be Skipped

The validation pipeline has seven stages. Each must pass before proceeding.

```
HYPOTHESIS → DATA_AUDIT → IS_TESTING → STATISTICAL → REGIME → OOS → DETERMINATION
```

No shortcuts. No "let's skip data audit this time."

---

## 5. OOS is One Shot

Out-of-sample testing happens exactly once. No retries. No parameter adjustments after.

**Why:** Multiple OOS attempts IS p-hacking.

---

## 6. Parameters Lock Before Testing

All parameters locked at HYPOTHESIS stage, before any testing.

Locked items:
- Strategy parameters
- IS/OOS date ranges
- Success criteria

---

## 7. Reproducibility

Every validation must be reproducible by someone else.

| Element | Preserved In |
|---------|-------------|
| Parameters | hypothesis.json |
| Date ranges | hypothesis.json |
| Algorithm code | validations/X/is_test/main.py |
| Results | results.json |
| Random seeds | config (if applicable) |
| Data sources | Recorded with paths/versions |

---

## 8. Lineage Tracking

When ideas spawn from analysis, track parent-child relationships.

```json
{
  "id": "IDEA-001",
  "lineage": {
    "parent": "STRAT-001",
    "source": "persona_analysis",
    "persona": "risk-manager"
  }
}
```

Enables: `research catalog list --derived-from STRAT-001`

---

## 9. Workspace Separation

User data (workspace) is completely separate from application code.

- Tool: `/path/to/research-system/` (the repo)
- Workspace: `~/my-research/` (user data)

Users upgrade tool without losing data. Backup = backup workspace.

---

## 10. Fail Loudly

When something goes wrong, error immediately with clear message. Never silently continue.

```python
# Wrong
try:
    validate_data()
except:
    pass

# Right
validate_data()  # Throws with clear message
```

---

## 11. Audit Trail

Every significant action logged with timestamp.

```
2025-12-18 14:23:01 | [STRAT-001] GATE DATA_AUDIT: PASSED
2025-12-18 14:23:45 | [STRAT-001] IS_TESTING started
2025-12-18 14:25:12 | [STRAT-001] IS_TESTING completed: alpha=3.2%
```

---

## 12. QC Native First

Data hierarchy (in order of preference):

1. QC Native (always first)
2. QC Object Store (uploaded)
3. Internal Purchased (paid, never delete)
4. Internal Curated (validated free)
5. Internal Experimental (unverified)

---

## 13. Bonferroni Correction

Multiple tests = stricter threshold.

```
Threshold = 0.01 / number_of_tests
```

3 tests → threshold = 0.0033

---

## 14. Nothing Thrown Away

Failed tests generate learnings. Learnings spawn new ideas. The catalog grows.

```
STRAT-001 (INVALIDATED)
└── IDEA-001 (UNTESTED) - "What if we add regime filter?"
```

Even failures contribute to the knowledge base.

---

## Checklist

Before any change:

- [ ] Exposed through CLI (not direct file access)
- [ ] Schema validation on writes
- [ ] Gates enforced (no bypass)
- [ ] Errors fail loudly
- [ ] Actions logged
- [ ] Reproducible by others
