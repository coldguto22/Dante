# Item 7 design: extract `SelectionPolicy`

**Status:** implemented and tested  
**Date:** 2026-11-05

## Problem

`InitiativeRunner.cycle()` currently combines prompt construction,
authorization, selection, execution, feedback, and persistence. That makes it
hard to compare selection mechanisms without changing unrelated behavior.

## Expected behavior

Extract a small `SelectionPolicy` protocol with one method that receives the
authorized candidates and their original proposal order and returns the
selected candidate. Implement `NoveltyPolicy` with the exact current rule:

```python
max(candidates, key=(1.0 - similarity, -original_index))
```

No motivation variable is added. Repetition/saturation remains a later,
separate experiment in which only that variable changes and the predicted
selection movement is tested.

## Verification and risks

Golden tests use fixed candidates, similarities, and proposal order to assert
the same selections as the pre-extraction runner. Existing initiative tests
remain the regression suite. The extraction does not alter authorization,
prompting, persistence, execution, or feedback.

## Implementation note (2026-11-05)

`SelectionPolicy` and `NoveltyPolicy` are implemented in
`src/dante/selection_policy.py`, and `InitiativeRunner` delegates only its
existing candidate selection expression to the policy. The full test suite
passes; no new motivation variable was introduced.
