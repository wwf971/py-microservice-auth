import re

SERVICE_ID_PATTERN = re.compile(r"^[0-9a-z]+$")


def validate_service_id(service_id: str) -> bool:
    if not service_id:
        return False
    return SERVICE_ID_PATTERN.fullmatch(service_id) is not None


def has_permission(permission_codes, permission_code_required, permission_include_by_code=None) -> bool:
    permission_code_set = {int(permission_code) for permission_code in permission_codes or []}
    permission_include_by_code = permission_include_by_code or {}

    if int(permission_code_required) in permission_code_set:
        return True

    permission_code_pending = list(permission_code_set)
    permission_code_checked = set()
    while permission_code_pending:
        permission_code = permission_code_pending.pop()
        if permission_code in permission_code_checked:
            continue
        permission_code_checked.add(permission_code)

        for permission_code_included in permission_include_by_code.get(permission_code, []):
            permission_code_included = int(permission_code_included)
            if permission_code_included == int(permission_code_required):
                return True
            permission_code_pending.append(permission_code_included)

    return False


def has_service_permission(
    service_permission_items,
    service_id,
    permission_code_required,
    permission_include_by_service_code=None,
) -> bool:
    permission_codes = [
        item.get("permission_code")
        for item in service_permission_items or []
        if item.get("service_id") == service_id
    ]
    permission_include_by_service_code = permission_include_by_service_code or {}
    permission_include_by_code = permission_include_by_service_code.get(service_id, {})
    return has_permission(permission_codes, permission_code_required, permission_include_by_code)
