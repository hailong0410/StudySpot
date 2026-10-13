"""Pure rules for StudySpot discovery, report validation and report age."""
from datetime import datetime
from typing import Any, Mapping

CROWD = {"low": "Not busy", "medium": "Somewhat busy", "high": "Very busy"}
NOISE = {"quiet": "Quiet", "moderate": "Some conversation", "loud": "Loud"}


def parse_filters(q: str, study: str, outlets: str, atmosphere: str) -> dict[str, str]:
    """Trim search to 120 characters and accept only the current filter choices."""
    if study not in ("", "individual", "group") or outlets not in ("", "yes") or atmosphere not in ("", "quiet"):
        raise ValueError("Choose one of the available filters.")
    return {"q": q.strip()[:120], "study": study, "outlets": outlets, "atmosphere": atmosphere}


def build_space_query(filters: Mapping[str, str]) -> tuple[str, list[str]]:
    """Build a parameterized search; percent, underscore and slash are literal."""
    conditions: list[str] = []
    args: list[str] = []
    if filters["q"]:
        escaped = filters["q"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append("name LIKE ? ESCAPE '\\'")
        args.append("%" + escaped + "%")
    if filters["study"]:
        conditions.append("study_type IN (?, 'both')")
        args.append(filters["study"])
    if filters["outlets"]:
        conditions.append("outlets = 1")
    if filters["atmosphere"]:
        conditions.append("atmosphere = 'quiet'")
    sql = "SELECT * FROM study_spaces" + (" WHERE " + " AND ".join(conditions) if conditions else "") + " ORDER BY name"
    return sql, args


def validate_report_fields(crowd: str | None, noise: str | None) -> tuple[str, str]:
    """Both fields must be one of the allowed crowd/noise values."""
    if crowd not in CROWD or noise not in NOISE:
        raise ValueError("Select a crowd level and a noise level.")
    assert crowd is not None and noise is not None
    return crowd, noise


def report_view(row: Mapping[str, Any] | None, now: datetime) -> dict[str, Any] | None:
    """A report is stale at 60 minutes; display full minutes, hours or days.
    Future timestamps have zero displayed age. A missing row gives None.
    """
    if not row:
        return None
    posted = datetime.fromisoformat(row["created_at"])
    minutes = max(0, int((now - posted).total_seconds() // 60))
    age = "Just now" if minutes == 0 else (f"{minutes} min ago" if minutes < 60 else (f"{minutes // 60} hours ago" if minutes < 1440 else f"{minutes // 1440} days ago"))
    return dict(row) | {"age": age, "stale": minutes >= 60, "crowd_label": CROWD[row["crowd"]], "noise_label": NOISE[row["noise"]], "display_time": posted.strftime("%Y-%m-%d %H:%M UTC")}
