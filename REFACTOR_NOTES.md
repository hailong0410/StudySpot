# ICA14 — Refactor the Legacy Pricing Module

**Student:** Hai Long Ha — Group 6  
**Branch:** `refactor/ica14-pricing`  
**Environment:** Python 3.12.14, pytest 9.2.0, radon 6.0.1.

## Worksheet 1 — Understanding before changing anything

### What do t, q, u, d, c, w mean?

The public signature stays `calc(t, q, u, d, c=None, w=False)`.

| Parameter | Meaning and existing behavior |
| --- | --- |
| `t` | Event type: concert, lecture, sports, workshop. Other values raise `ValueError("bad type")`. |
| `q` | Quantity. Values <= 0 raise `ValueError("bad qty")`; values > 10 raise `ValueError("too many")`. Integer type is not enforced. |
| `u` | User dictionary or None. Optional keys: role, verified, years, first_purchase. Unknown roles get no role discount. |
| `d` | Day of week, conventionally 0 = Monday through 6 = Sunday. Only 5 and 6 trigger weekend prices; other values are not rejected. |
| `c` | Optional coupon: WELCOME10, HALFOFF, FREEDRINK. Unknown codes raise `ValueError("bad coupon")`. |
| `w` | Waitlist flag. A truthy value adds $2 before calculating the service fee. |

### In what order are discounts applied? Does the order matter?

1. Select the event's base price, then validate quantity. Preserve this order so an invalid event is reported before an invalid quantity.
2. Multiply base price by quantity.
3. Apply the role discount: verified student 0.8; unverified student 0.9; staff 0.85; alumni with at least 10 years 0.85; other alumni 0.95.
4. Subtract a flat $5 for quantities >= 5, except workshops.
5. Apply the coupon: WELCOME10 multiplies by 0.9 only for first purchases; HALFOFF multiplies by 0.5 only for lectures; FREEDRINK leaves the price unchanged.
6. Add $2 if waitlisted.
7. Clamp a negative subtotal to zero.
8. Add the service fee: zero for nonpositive subtotals; $1 below $20; $2.50 from $20 to below $100; $5 from $100 upward.
9. Use Python's `round(total + fee, 2)` once, at the end.

Order matters: a flat reduction and a percentage reduction do not commute, and the fee depends on the resulting subtotal. The supplied `test_bulk_discount_applies_before_coupon` pins five weekday lectures for a verified student with HALFOFF: `(25 * 0.8 - 5) * 0.5 + 1 = 8.50`. Applying the coupon before the bulk reduction would instead produce $6.00.

### Which code can never run? How do you know?

For ordinary valid ticket inputs (integer quantity 1–10, supported events, and ordinary user dictionaries), the assignment `total = 0.0` under `if total < 0` cannot run. Quantities 1–4 do not receive a flat reduction, and all multipliers are positive. For quantities 5–10, the lowest discounted subtotal is five lectures for a verified student with HALFOFF: `(5 * 5 * 0.8 - 5) * 0.5 = 7.50`. Workshops do not receive the bulk reduction. Waitlisting only increases the subtotal. Therefore the zero-fee outcome is also unreachable in that ordinary input domain.

This is domain reasoning, not a claim that the 24 tests prove universal unreachability. The original does not fully constrain numeric inputs or custom Python objects. The defensive clamp and nonpositive fee branch were retained. The initial `base_price = 0` is also a redundant assignment: every successful event branch overwrites it, while the fallback raises an exception.

### What looks like a bug but is pinned by a test?

| Surprising behavior | Supplied evidence / decision |
| --- | --- |
| FREEDRINK has no effect on the ticket price. | `test_freedrink_changes_nothing`; preserved. A drink may be handled outside ticket pricing. |
| HALFOFF silently does nothing for non-lecture events. | `test_halfoff_only_lectures`; preserved. |
| WELCOME10 silently does nothing without first_purchase. | `test_welcome_coupon_needs_first_purchase`; preserved. |
| Workshops do not get the bulk discount. | `test_bulk_discount_not_for_workshops`; preserved. |
| A waitlisted purchase still pays a service fee after the $2 addition. | `test_waitlist_fee` pins a $5 lecture at $8 total; preserved. |

Other observations are not directly pinned by the supplied tests: fractional quantities and out-of-range days are not rejected; exact fee thresholds and exception messages are not comprehensively covered. No new validation rules were introduced.

## Plan — Seven small steps

Rename the price local, then extract base-price selection, quantity validation, role discounting, bulk discounting, coupon application, and fee calculation. Preserve the public parameters, validation order, operation order, arithmetic, and final rounding.

## Worksheet 2 — Refactoring log

Each step was produced with AI assistance, inspected as a diff, and followed by the unchanged test suite before committing. This records the executed AI-assisted work; it does not claim an independent human review or classroom pair session.

| # | Refactoring | AI or by hand? | Tests after | Kept or reverted? Why? | Commit |
| --- | --- | --- | --- | --- | --- |
| 1 | Rename local p to base_price | AI-assisted | 24 passed | Kept: clearer name; public parameters unchanged. | `14edcc0` |
| 2 | Extract `_base_price(event_type, day)` | AI-assisted | 24 passed | Kept: isolates prices and event validation without changing comparisons. | `43a0ed4` |
| 3 | Extract `_validate_quantity(quantity)` | AI-assisted | 24 passed | Kept: preserves boundaries, messages, and validation order. | `80d6937` |
| 4 | Extract `_apply_role_discount(total, user)` | AI-assisted | 24 passed | Kept: preserves dictionary defaults, truthiness, and multipliers. | `af42761` |
| 5 | Extract `_apply_bulk_discount(total, event_type, quantity)` | AI-assisted | 24 passed | Kept: preserves the workshop exception and position before coupons. | `541eae0` |
| 6 | Extract `_apply_coupon(total, event_type, user, coupon)` | AI-assisted | 24 passed | Kept: preserves eligibility, no-op coupons, and invalid-code errors. | `6e9ae50` |
| 7 | Extract `_service_fee(total)` | AI-assisted | 24 passed | Kept: preserves strict thresholds, calculation after waitlist, and final rounding. | `a4e3592` |

Baseline commit: `922bd42`. No failing step was accepted. No supplied expected value was changed. The StudySpot branch retains the baseline and all seven refactoring commits as descendants of StudySpot main.

## Worksheet 3 — Before and after (radon)

All measurements concern `legacy_pricing.py` only, using the same radon version. The baseline matches the handout.

| Measure | Before | After |
| --- | --- | --- |
| Highest function CC (grade) | calc: 31, E | _base_price: 9, B |
| Public calc CC | 31, E | 3, A |
| Average function CC | 31.00, E | 5.29, B |
| Number of functions | 1 | 7 |
| Maintainability index | 53.94, A | 49.77, A |
| Lines of code (radon raw SLOC) | 63 | 80 |
| Characterization tests passing | 24 / 24 | 24 / 24 |

Final CC values: `_base_price` 9; `_apply_coupon` 8; `_apply_role_discount` 7; `_service_fee` 4; `calc` 3; `_validate_quantity` 3; `_apply_bulk_discount` 3.

## Trade-offs and debrief

The main benefit is a short `calc` function that describes the pricing pipeline in order. Helpers have separate business responsibilities, and the highest individual CC falls from E to B. The lower average partly reflects distributing decisions across more functions; the business rules did not disappear. Summed function CC rises from 31 to 37 because each of the six added functions contributes a baseline complexity of one.

MI decreases by 4.17 points while remaining grade A. Extraction adds definitions, calls, parameters, and returns, increasing SLOC; MI also depends on Halstead volume and comment density. This is a trade-off rather than improvement in every metric. Readers can locate each rule more easily but must follow helper calls. No comments or blank lines were added merely to inflate MI.

A lookup table and a parameter object were not needed for this exercise. Keeping the original comparisons and arithmetic makes preservation easier to review. The discount helpers return a total rather than introducing extra multiplications on paths that originally did nothing. Floating-point operations and final rounding remain in the same order.

Possible later changes need separate requirements and tests: enforce integer quantities and valid days, decide whether ineligible coupons should raise errors, clarify waitlist billing, and consider currency-safe arithmetic. These would change behavior and were not included.

The safest changes were small extractions with an unchanged test suite and a diff read after each step. AI helped perform one responsibility at a time; tests and diff inspection checked the result. Characterization tests document today's behavior, including surprising behavior, so structural cleanup and bug fixing were kept as separate decisions. Unusual inputs and future rule interactions remain limitations of the supplied coverage.

## Verification and evidence

- The supplied `test_legacy_pricing.py` is byte-for-byte unchanged. SHA-256: `dfbb5feacb70d8ceec00b79185892ce3317f083eb77ce0612f701bd5119fd5cd`.
- All 24 tests passed at baseline and after every refactoring step.
- `python verify_behavior.py` compared the final code with the unchanged original over 27,000 cases. All return values or exception types/messages matched. The matrix covers event types, quantity boundaries and selected fractions, user roles, day values, supported/invalid coupons, and waitlist combinations. This is additional evidence, not a proof for every possible Python input.
- Original source and baseline/final command outputs are in `ICA14/evidence/`.
- `git diff --check` passed.

Reproduce from the repository root:

```bash
cd ICA14
python -m pip install -r requirements.txt
python -m pytest -q
python -m radon cc -s -a legacy_pricing.py
python -m radon mi -s legacy_pricing.py
python -m radon raw legacy_pricing.py
python verify_behavior.py
```

## StudySpot integration and submission

Repository: https://github.com/hailong0410/StudySpot  
Branch: https://github.com/hailong0410/StudySpot/tree/refactor/ica14-pricing

The baseline and seven refactoring commits were replayed on StudySpot main (`343aebb`). Each replayed version passed the original 24 tests with StudySpot's pinned pytest 8.4.2; the original standalone measurements above used pytest 9.2.0. The production module and supplied tests are unchanged from the verified standalone deliverable. `ICA14/pytest.ini` provides an explicit configuration for running this exercise from its own directory. The module is an independent course exercise in `ICA14/`, not a pricing feature integrated into the StudySpot application.

`REFACTOR_NOTES.md` is at the repository root. Supporting files and verification evidence are in `ICA14/`. Only these new assignment paths were added; existing StudySpot application files and main were not changed. Local repository-wide check results are recorded in `ICA14/evidence/studyspot-checks.txt`. The branch is published on GitHub. Post the branch URL above on Brightspace; no Brightspace submission is claimed. The optional own-project extension was not performed.
