"""Bounded menu previews; uses the existing menu snapshot and candidate rules."""

from .menu_change_governance import MenuChangeGovernanceError, _menu_values, stable_sha256


MAX_BATCH_ITEMS = 100


def build_batch_preview(snapshots, operation, value=None):
    if not isinstance(snapshots, list) or not 1 <= len(snapshots) <= MAX_BATCH_ITEMS:
        raise MenuChangeGovernanceError("BATCH_SIZE_INVALID")
    if operation == "set_price":
        proposed = _menu_values({"list_price": value}, "batch")
    elif operation == "set_categories":
        proposed = _menu_values({"pos_category_ids": value}, "batch")
    elif operation == "pause":
        proposed = {"available_in_pos": False}
    elif operation == "archive":
        proposed = {"active": False, "available_in_pos": False}
    elif operation == "reactivate":
        proposed = {"active": True, "available_in_pos": True}
    else:
        raise MenuChangeGovernanceError("BATCH_OPERATION_INVALID")
    # canonical serialization rejects NaN and infinity as well as invalid prices.
    stable_sha256(proposed)
    rows, seen = [], set()
    for snapshot in snapshots:
        before = _menu_values(snapshot, "before")
        code = before.get("thing_code")
        if not code or code in seen:
            raise MenuChangeGovernanceError("BATCH_IDENTITY_MISSING_OR_DUPLICATE")
        seen.add(code)
        after = {**before, **proposed}
        diff = {key: {"before": before.get(key), "after": after[key]}
                for key in proposed if before.get(key) != after[key]}
        rows.append({"before": before, "after": after, "diff": diff})
    preview = {"schema": "wuchang-menu-batch-preview/1.0", "operation": operation,
               "rows": rows, "changed_count": sum(bool(row["diff"]) for row in rows),
               "product_write": False}
    preview["sha256"] = stable_sha256(preview)
    return preview


def build_reversal_values(before, proposed, current):
    before = _menu_values(before, "before")
    proposed = _menu_values(proposed, "proposed")
    current = _menu_values(current, "current")
    if current != {**before, **proposed}:
        raise MenuChangeGovernanceError("REVERSAL_BASE_CHANGED")
    if "image_sha256" in proposed:
        raise MenuChangeGovernanceError("REVERSAL_IMAGE_PREIMAGE_UNAVAILABLE")
    if not proposed or not set(proposed).issubset(before):
        raise MenuChangeGovernanceError("REVERSAL_PREIMAGE_INCOMPLETE")
    return {key: before[key] for key in proposed}
