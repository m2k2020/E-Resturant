from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def permission_required(perm):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                staff = request.user.staff_profile
                if staff.has_permission(perm):
                    return view_func(request, *args, **kwargs)
            except Exception:
                pass
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('home')
        return wrapper
    return decorator
