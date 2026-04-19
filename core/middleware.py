import re
from .logging_utils import log_action, log_error


SKIP_PATHS = ['/static/', '/media/', '/favicon.ico', '/login/']

MODULE_MAP = {
    '/dashboard': 'dashboard',
    '/orders': 'orders',
    '/menu': 'menu',
    '/categories': 'menu',
    '/tables': 'tables',
    '/kitchen': 'kitchen',
    '/inventory': 'inventory',
    '/expenses': 'expenses',
    '/staff': 'staff',
    '/settings': 'settings',
    '/reports': 'reports',
    '/logs': 'logs',
}

PAGE_NAMES = {
    '/': 'Home',
    '/dashboard/': 'Dashboard',
    '/orders/': 'Order List',
    '/orders/new/': 'New Order',
    '/menu/': 'Menu List',
    '/menu/add/': 'Add Menu Item',
    '/categories/': 'Category List',
    '/categories/add/': 'Add Category',
    '/tables/': 'Table List',
    '/tables/add/': 'Add Table',
    '/kitchen/': 'Kitchen Display',
    '/inventory/': 'Inventory',
    '/inventory/add/': 'Add Ingredient',
    '/inventory/stock-movement/': 'Stock Movement',
    '/expenses/': 'Expenses',
    '/expenses/add/': 'Add Expense',
    '/expenses/categories/': 'Expense Categories',
    '/staff/': 'Staff List',
    '/staff/add/': 'Add Staff',
    '/reports/sales/': 'Sales Report',
    '/reports/daily/': 'Daily Summary',
    '/settings/': 'General Settings',
    '/settings/profile/': 'Profile Settings',
    '/settings/payment-methods/': 'Payment Methods',
    '/settings/roles/': 'Roles & Permissions',
    '/logs/': 'System Logs',
}


def detect_module(path):
    for prefix, module in MODULE_MAP.items():
        if path.startswith(prefix):
            return module
    if path == '/':
        return 'system'
    return 'system'


def detect_page_name(path):
    if path in PAGE_NAMES:
        return PAGE_NAMES[path]
    pk_match = re.search(r'/(\d+)/', path)
    if pk_match:
        base = re.sub(r'/\d+/', '/#/', path)
        if '/edit/' in path:
            module = detect_module(path)
            return f"Edit {module.title()} #{pk_match.group(1)}"
        if '/delete/' in path:
            module = detect_module(path)
            return f"Delete {module.title()} #{pk_match.group(1)}"
        if '/receipt/' in path:
            return f"Receipt Order #{pk_match.group(1)}"
        module = detect_module(path)
        return f"{module.title()} Detail #{pk_match.group(1)}"
    return path


def detect_action(request, path):
    method = request.method
    if method == 'GET':
        return 'view'
    if method == 'POST':
        if '/add/' in path or '/new/' in path or '/create/' in path or '/mark/' in path:
            return 'create'
        if '/edit/' in path:
            return 'update'
        if '/delete/' in path:
            return 'delete'
        if '/status/' in path:
            return 'status_change'
        if '/pay' in path or '/paid' in path:
            return 'payment'
        if '/stock-movement/' in path:
            return 'stock'
        if '/toggle/' in path:
            return 'update'
        if '/discount/' in path:
            return 'update'
        if '/login/' in path:
            return 'login'
        return 'update'
    return 'other'


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if any(request.path.startswith(p) for p in SKIP_PATHS):
            return response

        if not request.user.is_authenticated:
            return response

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return response

        path = request.path
        module = detect_module(path)
        pk_match = re.search(r'/(\d+)/', path)
        object_id = int(pk_match.group(1)) if pk_match else None

        if request.method == 'GET':
            page_name = detect_page_name(path)
            log_action(
                request,
                action='view',
                module=module,
                object_type=module.title(),
                object_id=object_id,
                object_repr=path,
                details=f"Visited: {page_name}",
            )

        elif request.method == 'POST':
            action = detect_action(request, path)
            details = ''
            if action == 'status_change':
                status_match = re.search(r'/status/(\w+)/', path)
                if status_match:
                    details = f"Status changed to: {status_match.group(1)}"
            elif action == 'create':
                details = f"Created new {module}"
            elif action == 'update':
                details = f"Updated {module} #{object_id}" if object_id else f"Updated {module}"
            elif action == 'delete':
                details = f"Deleted {module} #{object_id}" if object_id else f"Deleted {module}"
            elif action == 'payment':
                details = f"Payment processed for order #{object_id}" if object_id else "Payment processed"

            log_action(
                request,
                action=action,
                module=module,
                object_type=module.title(),
                object_id=object_id,
                object_repr=path,
                details=details,
            )

        return response

    def process_exception(self, request, exception):
        try:
            log_error(request, exception)
        except Exception:
            pass
        return None
