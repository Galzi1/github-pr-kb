---
paths:
  - "**/*.{js,ts,py,java,go,cpp,cs,rs,php,rb}"
---

# Clean Code Standards (Uncle Bob & Pragmatic Refinement)

Follow these principles to ensure code is readable, maintainable, and professional. 

## 1. Meaningful Names
- **Intention-Revealing**: Use names that tell why it exists, what it does, and how it is used.
- **Pronounceable & Searchable**: Avoid abbreviations; use `generationTimestamp` instead of `genymdhms`.
- **Vocabulary**: Use nouns for classes (`Customer`) and verbs for methods/functions (`postPayment`).
- **Constants**: Replace magic numbers with named constants (e.g., `MAX_RETRIES`).

## 2. Functions & Methods
- **Small & Single Purpose**: Functions should do one thing and do it well (SRP).
- **One Level of Abstraction**: Keep all statements within a function at the same level of abstraction.
- **Minimal Arguments**: Prefer 0-2 arguments. If you need more than 3, wrap them in an object.
- **Command-Query Separation**: Functions should either do something or answer something, never both.

## 3. Comments & Documentation
- **Explain Yourself in Code**: If code requires a comment to be understood, try refactoring the names or structure first.
- **Legal/Informative Only**: Use comments for legal headers, complex regex explanations, or "Why" decisions (not "What").
- **Delete Dead Code**: Never leave commented-out code in the codebase; use version control for history.

## 4. Error Handling
- **Use Exceptions**: Prefer throwing exceptions over returning error codes.
- **The "Null" Rule**: Do not return `null` or pass `null` into methods to avoid defensive null-checking proliferation.

## 5. Pragmatic Adjustments (Caveats)
*Follow these to avoid the "Ugly" side of dogmatic Clean Code application:*

- **Avoid Function Fragmentation**: Do not break functions into tiny pieces if it makes the logic harder to follow. A 20-line function that is easy to read is better than five 4-line functions that force the reader to jump between files.
- **Balance with Deep Modules**: Favor "deep" modules (simple interface, complex internal logic) over "shallow" modules that just wrap simple logic in many layers.
- **Valuable Comments**: Do not dogmatically delete comments that provide critical context or explain non-obvious algorithms (e.g., performance optimizations or domain-specific math).
- **Context over Dogma**: Rules are guides, not laws. If following a rule makes the code more complex or fragile, prioritize clarity and the "Principle of Least Surprise".
