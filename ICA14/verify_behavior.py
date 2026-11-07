"""Compare the refactor with the unchanged starter on an input matrix."""
from itertools import product

from evidence.original_legacy_pricing import calc as original
from legacy_pricing import calc as refactored


def outcome(function, arguments):
    try:
        return ("return", function(*arguments))
    except Exception as error:
        return ("raise", type(error).__name__, str(error))


def main():
    users = [
        None, {}, {"role": "visitor"},
        {"role": "student", "verified": True},
        {"role": "student", "verified": False},
        {"role": "student", "verified": True, "first_purchase": True},
        {"role": "staff"}, {"role": "alumni", "years": 9},
        {"role": "alumni", "years": 10}, {"role": "alumni"},
    ]
    cases = product(
        ["concert", "lecture", "sports", "workshop", "party"],
        [-1, 0, 0.1, 1, 4, 4.999, 5, 10, 11],
        users,
        [0, 4, 5, 6, 7],
        [None, "WELCOME10", "HALFOFF", "FREEDRINK", "FREE100", ""],
        [False, True],
    )
    checked = 0
    for arguments in cases:
        before = outcome(original, arguments)
        after = outcome(refactored, arguments)
        assert before == after, (arguments, before, after)
        checked += 1
    print(f"{checked:,} cases matched (return values or exception types/messages).")


if __name__ == "__main__":
    main()
