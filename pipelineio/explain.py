def explain_meta_diff(old_meta: dict[str, object], new_meta: dict[str, object]) -> str | None:
    if old_meta == new_meta:
        return None

    if old_meta.get("exists") != new_meta.get("exists"):
        if new_meta.get("exists"):
            return "input created"
        return "input deleted"

    if old_meta.get("mtime_ns") != new_meta.get("mtime_ns"):
        return "mtime changed"

    if old_meta.get("size") != new_meta.get("size"):
        return "size changed"

    if old_meta.get("type") == "http" and new_meta.get("type") == "http":
        if old_meta.get("etag") != new_meta.get("etag"):
            return "etag changed"
        if old_meta.get("last_modified") != new_meta.get("last_modified"):
            return "last_modified changed"

    return "metadata changed"
