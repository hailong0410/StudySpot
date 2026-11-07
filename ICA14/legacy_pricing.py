"""Ticket pricing for CampusEvents -- legacy module (ICA 24A).

This works, and it is tested (see test_legacy_pricing.py), but nobody wants to touch it.
Your job: refactor it without changing behavior, and measure the result with radon.
"""


def calc(t, q, u, d, c=None, w=False):
    # t = event type, q = quantity, u = user dict, d = day of week (0=Mon..6=Sun),
    # c = coupon code, w = waitlist
    base_price = _base_price(t, d)
    if q <= 0:
        raise ValueError("bad qty")
    if q > 10:
        raise ValueError("too many")
    total = base_price * q
    if u is not None:
        if u.get("role") == "student":
            if u.get("verified"):
                total = total * 0.8
            else:
                total = total * 0.9
        elif u.get("role") == "staff":
            total = total * 0.85
        elif u.get("role") == "alumni":
            if u.get("years", 0) >= 10:
                total = total * 0.85
            else:
                total = total * 0.95
    if q >= 5:
        if t != "workshop":
            total = total - 5.0
    if c is not None:
        if c == "WELCOME10":
            if u is not None and u.get("first_purchase"):
                total = total * 0.9
        elif c == "HALFOFF":
            if t == "lecture":
                total = total * 0.5
        elif c == "FREEDRINK":
            pass
        else:
            raise ValueError("bad coupon")
    if w:
        total = total + 2.0
    if total < 0:
        total = 0.0
    fee = 0.0
    if total > 0:
        if total < 20:
            fee = 1.0
        elif total < 100:
            fee = 2.5
        else:
            fee = 5.0
    return round(total + fee, 2)


def _base_price(event_type, day):
    base_price = 0
    if event_type == "concert":
        if day == 5 or day == 6:
            base_price = 25.0
        else:
            base_price = 20.0
    elif event_type == "lecture":
        base_price = 5.0
    elif event_type == "sports":
        if day == 5 or day == 6:
            base_price = 15.0
        else:
            base_price = 12.0
    elif event_type == "workshop":
        base_price = 30.0
    else:
        raise ValueError("bad type")
    return base_price
