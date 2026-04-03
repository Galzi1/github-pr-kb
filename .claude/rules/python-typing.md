---
paths:
  - "**/*.py"
---

# Python 3.13 Type Hinting Standards

Follow these rules to ensure the codebase remains type-safe, maintainable, and leverages the latest Python 3.13+ capabilities.

## 1. Strict `Any` Policy
The use of `typing.Any` is a failure of the type system. You must exhaust all other options before using it. `Any` is ONLY permitted in two scenarios:
1. **External Boundaries**: The type is explicitly `Any` in a third-party library NOT defined in this repository, and you are passing it through.
2. **Absolute Last Resort**: There is literally NO other applicable type (e.g., `object`, `Generics`, `Protocols`, or `TypeVar` cannot describe the behavior).

### Alternatives to `Any` (Use these first):
- **`object`**: Use when a function accepts any object but only performs operations common to all objects (like `str()` or `id()`).
- **Generics (`T`)**: Use when the type is unknown but consistent across multiple arguments or return values.
- **Protocols (`typing.Protocol`)**: Use structural typing to define what an object *does* (e.g., has a `.close()` method) rather than what it *is*.
- **`typing.TypeAlias`**: Use to name complex types for clarity.

## 2. Modern Syntax (Python 3.10 - 3.13)
- **Built-in Generics**: Use `list[int]`, `dict[str, int]`, and `tuple[str, ...]` instead of `List`, `Dict`, or `Tuple` from `typing`.
- **Union Shorthand**: Always use `int | str` instead of `Union[int, str]`.
- **Optional Shorthand**: Always use `str | None` instead of `Optional[str]`. Ensure `None` is the last element in the union.
- **Type Parameters**: Use the Python 3.12+ syntax for generics: `def get_first[T](items: list[T]) -> T:`.

## 3. Python 3.13 Specific Features
- **TypeIs (PEP 742)**: Use `typing.TypeIs` for type-narrowing functions to provide better feedback to type checkers.
  ```python
  def is_str_list(val: list[object]) -> TypeIs[list[str]]:
      return all(isinstance(x, str) for x in val)
  ```
- **ReadOnly (PEP 705)**: Use `ReadOnly[]` within `TypedDict` to mark items that should not be modified.
  ```python
  class User(TypedDict):
      id: ReadOnly[int]
      name: str
  ```
- **Type Parameter Defaults (PEP 696)**: Use defaults for generics when applicable: `class Box[T = str]: ...`.

## 4. Function Annotation Best Practices
- **Arguments**: Prefer Abstract/Structural types. Use `Iterable`, `Sequence`, or `Mapping` for inputs to allow maximum flexibility.
- **Return Types**: Prefer Concrete types. Return `list[str]` or `dict[str, int]` rather than `Sequence` or `Mapping` to make it easier for callers to use the result.
- **Avoid Union Returns**: Try to avoid returning `int | str`. If a function must return multiple types, consider using a `Generic` or refactoring.
- **Self**: Use the `Self` type for methods that return an instance of their own class (e.g., factory methods or fluent APIs).

## 5. Documentation & Style
- **Type Aliases**: Use `type MyAlias = str | int` (Python 3.12+ syntax) for complex types.
- **NewType**: Use `NewType` for "ID" types or cases where you want to distinguish between two identical underlying types (e.g., `UserId = NewType('UserId', int)`).
