# Agent Guidance


## Code Style

- Always add imports at the top of the file unless avoiding a circular dependency. If you
  need to put an import somewhere else, add a comment as to why.


## Tests

- Prefer class-based tests
- Each test class should typically test only one app function/class
- Avoid testing external library internals
- Use `pytest.param` with `id` when passing parametrization parameters that are: more than
  a single value AND where one of the values does not already clearly indicate the purpose
  of the case. Otherwise, don't give parametrization cases ids.
- Use Star Trek TNG-themed fake values.
