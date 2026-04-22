from __future__ import annotations

AUTH_CODE_DESCRIPTIONS: dict[str, str] = {
    "00": "Approved",
    "05": "Do not honor",
    "14": "Invalid card number",
    "51": "Insufficient funds",
    "54": "Expired card",
    "57": "Transaction not permitted",
    "59": "Suspected fraud",
    "91": "Issuer or switch unavailable",
}


def format_top_auth_codes(items: list[tuple[str, int]]) -> str:
    if not items:
        return ""
    return ", ".join(f"{code} {AUTH_CODE_DESCRIPTIONS.get(code, 'Unknown')} x{count}" for code, count in items)
