# ICA14 — Refactor the Legacy Pricing Module

Hai Long Ha — Group 6. This independent course exercise is stored inside StudySpot.

Branch: https://github.com/hailong0410/StudySpot/tree/refactor/ica14-pricing

Completed worksheets and commit log: [REFACTOR_NOTES.md](../REFACTOR_NOTES.md).

From the repository root:

```bash
cd ICA14
python -m pip install -r requirements.txt
python -m pytest -q
python verify_behavior.py
python -m radon cc -s -a legacy_pricing.py
python -m radon mi -s legacy_pricing.py
python -m radon raw legacy_pricing.py
```

Expected: 24 tests pass; 27,000 cases match; calc CC 3 (A); maximum function CC 9 (B); MI 49.77 (A).

`evidence/` contains the unchanged original module, before/after measurements, and replay/integration check outputs. The supplied test file and public calc signature are unchanged. Pricing is not wired into the StudySpot application.

The baseline and seven refactoring steps are separate commits on this branch. Submit this branch URL on Brightspace. See [SUBMISSION_GUIDE_VI.md](SUBMISSION_GUIDE_VI.md).
