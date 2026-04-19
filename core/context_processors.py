from django.db.models import F
from .models import RestaurantSettings, Ingredient, Order


def restaurant_settings(request):
    settings = RestaurantSettings.get_settings()
    return {
        'currency': settings.currency_symbol,
        'restaurant_name': settings.restaurant_name,
    }


def user_permissions(request):
    if not request.user.is_authenticated:
        return {'user_perms': set()}
    if request.user.is_superuser:
        return {'user_perms': {'dashboard', 'orders', 'menu', 'tables', 'kitchen', 'inventory', 'expenses', 'staff', 'roles', 'reports', 'settings', 'logs'}}
    try:
        staff = request.user.staff_profile
        if staff.role:
            return {'user_perms': set(staff.role.permissions)}
    except Exception:
        pass
    return {'user_perms': set()}


def notifications(request):
    if not request.user.is_authenticated:
        return {'notifications': [], 'notif_count': 0}

    notifs = []

    low_stock = Ingredient.objects.filter(quantity__lte=F('min_stock'))
    for ing in low_stock[:5]:
        notifs.append({
            'type': 'warning',
            'title': f'{ing.name} - Low Stock',
            'message': f'Only {ing.quantity} {ing.get_unit_display()} left (min: {ing.min_stock})',
            'url': '/inventory/?low_stock=1',
        })

    pending_orders = Order.objects.filter(status='pending').count()
    if pending_orders > 0:
        notifs.append({
            'type': 'info',
            'title': f'{pending_orders} Pending Order{"s" if pending_orders > 1 else ""}',
            'message': 'Orders waiting to be prepared',
            'url': '/kitchen/',
        })

    return {
        'notifications': notifs,
        'notif_count': len(notifs),
    }


def language_context(request):
    lang = request.session.get('lang', 'en')
    return {'current_lang': lang}


def user_avatar(request):
    if not request.user.is_authenticated:
        return {'user_avatar_url': ''}
    try:
        staff = request.user.staff_profile
        if staff.avatar:
            return {'user_avatar_url': staff.avatar.url}
    except Exception:
        pass
    return {'user_avatar_url': ''}
