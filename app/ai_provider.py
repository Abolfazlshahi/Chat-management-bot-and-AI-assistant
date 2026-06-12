import copy

import httpx


def _fill(node, mapping):
    """جایگزینی {system_prompt} و {user_message} در کل body_template."""
    if isinstance(node, str):
        out = node
        for k, v in mapping.items():
            out = out.replace("{" + k + "}", v)
        return out
    if isinstance(node, list):
        return [_fill(x, mapping) for x in node]
    if isinstance(node, dict):
        return {k: _fill(v, mapping) for k, v in node.items()}
    return node


def _resolve_path(data, path):
    """مثل choices.0.message.content را از پاسخ JSON بیرون می‌کشد."""
    cur = data
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


async def call_ai(api: dict, system_prompt: str, user_message: str):
    """خروجی: (پاسخ متنی، تعداد توکن مصرف‌شده یا None)."""
    mapping = {"system_prompt": system_prompt, "user_message": user_message}
    body = _fill(copy.deepcopy(api["body_template"]), mapping)
    headers = _fill(copy.deepcopy(api.get("headers", {})), mapping)
    method = api.get("method", "POST").upper()

    async with httpx.AsyncClient(timeout=90) as client:
        if method == "GET":
            resp = await client.get(api["endpoint"], headers=headers, params=body)
        else:
            resp = await client.request(method, api["endpoint"], headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    answer = _resolve_path(data, api["response_path"])
    if answer is None:
        raise ValueError("پاسخ معتبری از API دریافت نشد (response_path را بررسی کن).")

    tokens = None
    usage_path = api.get("usage_path")
    if usage_path:
        try:
            raw = _resolve_path(data, usage_path)
            tokens = int(raw) if raw is not None else None
        except Exception:
            tokens = None
    return str(answer), tokens