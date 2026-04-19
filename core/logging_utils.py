import re
import traceback as tb
from .models import AuditLog, ErrorLog


def parse_user_agent(ua_string):
    ua = ua_string or ''
    result = {'device_type': 'Desktop', 'browser': 'Unknown', 'os_info': 'Unknown'}

    # Device type
    mobile_keywords = ['Mobile', 'Android', 'iPhone', 'iPad', 'iPod', 'Opera Mini', 'IEMobile']
    tablet_keywords = ['iPad', 'Tablet', 'PlayBook', 'Silk']
    if any(k in ua for k in tablet_keywords):
        result['device_type'] = 'Tablet'
    elif any(k in ua for k in mobile_keywords):
        result['device_type'] = 'Mobile'

    # Browser
    if 'Edg/' in ua:
        m = re.search(r'Edg/([\d.]+)', ua)
        result['browser'] = f"Edge {m.group(1)}" if m else 'Edge'
    elif 'Chrome/' in ua and 'Safari/' in ua:
        m = re.search(r'Chrome/([\d.]+)', ua)
        result['browser'] = f"Chrome {m.group(1).split('.')[0]}" if m else 'Chrome'
    elif 'Firefox/' in ua:
        m = re.search(r'Firefox/([\d.]+)', ua)
        result['browser'] = f"Firefox {m.group(1).split('.')[0]}" if m else 'Firefox'
    elif 'Safari/' in ua and 'Chrome' not in ua:
        m = re.search(r'Version/([\d.]+)', ua)
        result['browser'] = f"Safari {m.group(1).split('.')[0]}" if m else 'Safari'
    elif 'Opera' in ua or 'OPR/' in ua:
        result['browser'] = 'Opera'

    # OS
    if 'Windows NT 10' in ua:
        result['os_info'] = 'Windows 10/11'
    elif 'Windows' in ua:
        result['os_info'] = 'Windows'
    elif 'Mac OS X' in ua:
        m = re.search(r'Mac OS X ([\d_]+)', ua)
        ver = m.group(1).replace('_', '.') if m else ''
        result['os_info'] = f"macOS {ver}".strip()
    elif 'Android' in ua:
        m = re.search(r'Android ([\d.]+)', ua)
        result['os_info'] = f"Android {m.group(1)}" if m else 'Android'
    elif 'iPhone OS' in ua or 'iPad' in ua:
        m = re.search(r'OS ([\d_]+)', ua)
        ver = m.group(1).replace('_', '.') if m else ''
        result['os_info'] = f"iOS {ver}".strip()
    elif 'Linux' in ua:
        result['os_info'] = 'Linux'

    return result


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def log_action(request, action, module='', object_type='', object_id=None, object_repr='', details=''):
    if not request.user.is_authenticated:
        return
    ua = request.META.get('HTTP_USER_AGENT', '')
    device = parse_user_agent(ua)
    AuditLog.objects.create(
        user=request.user,
        action=action,
        module=module,
        object_type=object_type,
        object_id=object_id,
        object_repr=str(object_repr)[:200],
        details=details,
        ip_address=get_client_ip(request),
        user_agent=ua[:500],
        device_type=device['device_type'],
        browser=device['browser'],
        os_info=device['os_info'],
        url=request.path[:500],
        method=request.method,
    )


def log_error(request, exception):
    ua = request.META.get('HTTP_USER_AGENT', '')
    device = parse_user_agent(ua)
    ErrorLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        url=request.path[:500],
        method=request.method,
        error_type=type(exception).__name__,
        error_message=str(exception)[:1000],
        traceback=tb.format_exc()[:5000],
        ip_address=get_client_ip(request),
        user_agent=ua[:500],
        device_type=device['device_type'],
        browser=device['browser'],
        os_info=device['os_info'],
    )
