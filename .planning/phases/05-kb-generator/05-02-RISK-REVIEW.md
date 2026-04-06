# Risk Review: Plan 05-02 — Index Generation for KBGenerator

**Reviewed:** 2026-04-06
**Plan:** `.planning/phases/05-kb-generator/05-02-PLAN.md`
**Overall Risk Level:** Low (conditional on Plan 01 being complete first)

## 1. Plan Summary

**Purpose:** Add `_generate_index()` to `KBGenerator` so that every call to `generate_all()` produces a `kb/INDEX.md` file listing all articles grouped by category with counts, summaries, links, and `[review]` markers. This completes requirement KB-03 and finalizes KB-04 (index rebuild after incremental article additions).

**Key components touched:**
- `src/github_pr_kb/generator.py` — new `_generate_index` method + modification to `generate_all()`
- `tests/test_generator.py` — six new test functions for index behavior

**Stated assumptions:**
- Plan 01 has been executed and the `KBGenerator` class, `_write_atomic`, `_save_manifest`, `generate_all()`, and all existing tests are in place
- Articles have consistent YAML frontmatter with `category`, `needs_review`, `confidence`, and `comment_id` fields
- The first `# ` heading in each article is the summary text

**Theory of success:** The index can be built by scanning all `.md` files in `kb/` subdirectories, parsing their frontmatter, grouping by category, and writing a single markdown file. Because the generator controls frontmatter format, parsing is reliable.

## 2. Assumptions & Evidence

| # | Assumption | Explicit/Implicit | Justified? | Blast Radius if Wrong |
|---|-----------|-------------------|------------|----------------------|
| A1 | **Plan 01 is complete** — `KBGenerator`, `_write_atomic`, `generate_all()`, manifest, tests all exist | Explicit (frontmatter `depends_on: ["05-01"]`) | **NOT YET** — `generator.py` is currently a one-line stub and `tests/test_generator.py` does not exist. No 05-01-SUMMARY.md found. | **Foundational** — Plan 02 cannot execute at all without Plan 01. Every test fixture, every method call, every import depends on Plan 01's output. |
| A2 | Frontmatter is parseable by reading lines between `---` delimiters | Implicit | Justified — the generator writes its own frontmatter with known fields and `_yaml_str` quoting. No external tool modifies these files. | **Structural** — If any article has malformed frontmatter, the index builder skips it (plan says "log warning and skip"), so blast radius is limited to missing index entries, not crashes. |
| A3 | The first `# ` heading in each article is the summary | Implicit | Justified — `_build_article` in Plan 01 writes `# {classified.summary}` immediately after frontmatter. | **Peripheral** — If the heading format changed, index entries would show wrong text but the system wouldn't break. |
| A4 | Category values are filesystem directory names (e.g., `architecture_decision`) | Explicit (from D-10, CONTEXT.md) | Justified — `CategoryLiteral` enforces the exact values at the Pydantic level. | **Peripheral** — Already validated by type system. |
| A5 | `.replace("_", " ").title()` produces correct display names for all categories | Explicit in plan task 4 | Justified for current categories (`architecture_decision` -> "Architecture Decision", `code_pattern` -> "Code Pattern", etc.). | **Peripheral** — Only fails if a category name has unusual casing needs. Current `CategoryLiteral` values are all clean. |
| A6 | Scanning subdirectories for `.md` files won't pick up stray files | Implicit | Partially justified — the plan excludes `INDEX.md` but doesn't mention other potential `.md` files at `kb/` root level (e.g., a README.md someone places there). | **Structural** — Could produce a bogus index entry with a frontmatter parse failure. The skip-on-error handling mitigates this. |
| A7 | `_write_atomic` is available and works for `INDEX.md` | Implicit | Justified — Plan 01 copies it into `generator.py`. | **Peripheral** — Direct dependency, but low risk given it's a known pattern. |

## 3. Ipcha Mistabra — Devil's Advocacy

### 3a. The Inversion Test

**Plan claim:** "The index is fully regenerated from scratch on every run — this is simpler and more reliable than incremental index updates."

**Inversion:** Full regeneration is actually *more fragile* than incremental. Consider: every run must scan the entire `kb/` directory, parse every article's frontmatter, and rebuild the index. If the KB grows to hundreds or thousands of articles, this becomes non-trivially slow and amplifies the impact of any single malformed file. An incremental approach that maintains index state in the manifest would be more resilient.

**Assessment:** The inversion is weak. At the scale this project targets (PRs from a single repo, likely tens to low hundreds of articles), full regeneration is trivially fast. The simplicity advantage dominates. The plan is sound on this point.

---

**Plan claim:** "Parsing frontmatter by reading lines between `---` delimiters is sufficient — no YAML library needed."

**Inversion:** Hand-rolled YAML parsing is a maintenance risk. YAML has edge cases: multi-line values, colons in values, trailing whitespace, BOM markers. A proper parser would handle these automatically.

**Assessment:** The inversion is dismissible here because the generator *writes its own frontmatter* with controlled field values and `_yaml_str` quoting. The parser only reads what the generator wrote. This is a closed loop — the plan is sound.

### 3b. The Little Boy from Copenhagen

**A new engineer joining next month:** Would understand the plan easily. Index generation from filesystem scan is a straightforward concept. The plan's test names clearly describe expected behavior.

**An SRE at 3 AM:** Not relevant — this is a local file generation tool, not a service.

**A user who manually edits KB articles:** This is the interesting outsider. If a user edits an article's frontmatter (changes category, fixes the summary heading), the next `generate_all()` run would regenerate the index based on the edited file. This is actually *correct behavior* — the plan handles it by design (D-14: regenerated from filesystem state). However, if a user *adds* a new `.md` file manually without going through the generator, it would appear in the index. This could be a feature or a bug depending on perspective. The plan doesn't address this explicitly, but the behavior is reasonable.

### 3c. Failure of Imagination

**Scenario 1: Encoding issues on Windows.** The plan reads `.md` files to parse frontmatter. If any file was written with a different encoding (e.g., a BOM-prefixed UTF-8 file), the `---` delimiter matching could fail. The `_write_atomic` pattern uses `encoding="utf-8"` explicitly, so generator-written files are safe. But manually placed files could cause issues.

**Mitigation already in plan:** "log warning and skip" for unparseable frontmatter. This is sufficient.

**Scenario 2: Empty KB directory.** If `generate_all()` is called with no classified files (or all are already in the manifest), `_generate_index` still runs and should produce a valid INDEX.md — either empty or with just the title. The plan doesn't explicitly test this edge case, but it's naturally handled if the grouping logic produces zero categories.

## 4. Risk Register

| Risk ID | Category | Description | Trigger | Prob | Severity | Priority | Detection | Mitigation | Contingency | Assumption |
|---------|----------|-------------|---------|------|----------|----------|-----------|------------|-------------|------------|
| R1 | Schedule | **Plan 01 not yet executed** — Plan 02 depends on a KBGenerator class, tests, and methods that do not exist yet | Attempting to execute Plan 02 before Plan 01 | High | Critical | Critical | `generator.py` is a stub; no `test_generator.py` | Execute Plan 01 first | N/A — cannot proceed without it | A1 |
| R2 | Technical | **Stray `.md` files in `kb/` cause index pollution** — User-placed or tool-generated markdown files without proper frontmatter appear as broken entries | Any `.md` file placed in a `kb/` subdirectory outside the generator flow | Low | Low | Low | Index contains entries with missing summaries or malformed links | The plan's skip-on-error for unparseable frontmatter handles this | Users can delete stray files | A6 |
| R3 | Technical | **`needs_review` frontmatter value is a string, not a boolean** — Plan says to check `needs_review` field from frontmatter parsing, but the frontmatter writes `true`/`false` as YAML strings. The parser must handle string-to-bool correctly | Every article with `needs_review: true` in frontmatter | Medium | Medium | Medium | `[review]` markers missing from index despite articles having `needs_review: true` | Plan should specify that the frontmatter parser checks for the string `"true"`, not a Python `True` boolean | Fixable in a follow-up without data loss | A2 |
| R4 | Technical | **Test fixture coupling to Plan 01** — The six new tests in Plan 02 need the fixtures and KBGenerator class from Plan 01. If Plan 01's fixture shape changes, Plan 02's tests may need adjustment | Plan 01 is implemented with different fixture design than Plan 02 assumes | Medium | Low | Low | Tests fail to import or instantiate fixtures | Plan 02 task says "read_first" includes current test file — executor will adapt | Adjust test code to match actual Plan 01 output | A1 |
| R5 | Technical | **Index file relative links depend on directory structure** — Index entry links like `gotcha/avoid-circular-imports.md` are relative to `kb/`. If INDEX.md is moved or the user opens it from a different working directory, links break | User views INDEX.md outside the `kb/` directory context | Low | Low | Low | Links are 404 when clicking in GitHub UI | This is inherent to relative markdown links — standard behavior | Document that INDEX.md should be viewed from `kb/` root | N/A |

### Risk Classification

- **Known Knowns:** R2 (stray files — handled by skip-on-error), R5 (relative links — standard markdown behavior)
- **Known Unknowns:** R3 (string vs. bool parsing — testable, should be validated), R4 (fixture coupling — depends on Plan 01 output)
- **Unknown Unknowns surfaced:** R1 is actually a known-known but is the most critical — it's a dependency sequencing issue, not a technical risk in the plan's logic itself.

## 5. Verdict & Recommendations

### Top 3 Risks

1. **R1 (Critical): Plan 01 must be executed first.** Generator.py is a stub. This plan cannot run.
2. **R3 (Medium): String-to-bool frontmatter parsing.** The plan should specify that when parsing `needs_review` from frontmatter text, it compares against the string `"true"`, not a Python boolean. This is a small but easy-to-miss detail that would cause `[review]` markers to silently disappear.
3. **R4 (Low): Fixture coupling.** Minor — the executor reads existing code before implementing, so adaptation is natural.

### Recommended Actions

- **Before executing:** Complete Plan 01 and verify its summary exists.
- **During implementation (R3):** When parsing frontmatter `needs_review`, explicitly compare `value.strip().lower() == "true"` rather than relying on truthiness.
- **Test addition:** Consider adding a test for empty-KB index generation (zero articles -> INDEX.md with just the title and no category headings).

### Open Questions

- None significant. The plan is well-specified and the context documents are thorough.

### What the Plan Does Well

- **Clear test-first structure** — Six named tests with precise expected behavior makes implementation unambiguous.
- **Consistent error handling** — "log warning and skip" for malformed frontmatter aligns with the project's D-18/D-19 pattern.
- **Full regeneration decision (D-14)** — Avoids the complexity of incremental index state management. The right call at this scale.
- **Category display name logic** — Simple `.replace("_", " ").title()` is elegant and covers all current `CategoryLiteral` values without a mapping table.
- **Explicit acceptance criteria** — Every criterion is machine-verifiable (grep for function names, run tests).
