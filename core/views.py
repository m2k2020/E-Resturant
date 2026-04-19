from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.core.paginator import Paginator
from datetime import timedelta
from .models import (
    Category, MenuItem, Table, Staff, Order, OrderItem,
    Ingredient, StockMovement, Attendance, RestaurantSettings,
    MenuItemIngredient, PaymentMethod, ExpenseCategory, Expense,
    Role, AVAILABLE_PERMISSIONS, AuditLog, ErrorLog,
)
from .forms import (
    CategoryForm, MenuItemForm, TableForm, StaffForm, OrderForm, OrderItemForm,
    IngredientForm, StockMovementForm, RestaurantSettingsForm,
    PaymentMethodForm, ExpenseCategoryForm, ExpenseForm,
)
from .decorators import permission_required
from .logging_utils import log_action


@login_required
def home(request):
    return render(request, 'core/home.html')


def deduct_stock(menu_item, qty, user=None):
    for link in menu_item.ingredient_links.select_related('ingredient'):
        ingredient = link.ingredient
        total_deduct = link.quantity_used * qty
        ingredient.quantity = max(0, ingredient.quantity - total_deduct)
        ingredient.save()
        StockMovement.objects.create(
            ingredient=ingredient,
            movement_type='out',
            quantity=total_deduct,
            notes=f'Auto-deducted: {qty}x {menu_item.name} sold',
            created_by=user,
        )


def restore_stock(menu_item, qty, user=None):
    for link in menu_item.ingredient_links.select_related('ingredient'):
        ingredient = link.ingredient
        total_restore = link.quantity_used * qty
        ingredient.quantity += total_restore
        ingredient.save()
        StockMovement.objects.create(
            ingredient=ingredient,
            movement_type='in',
            quantity=total_restore,
            notes=f'Auto-restored: {qty}x {menu_item.name} cancelled/removed',
            created_by=user,
        )


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    login_type = request.POST.get('login_type', 'standard')
    if request.method == 'POST':
        if login_type == 'pin':
            phone = request.POST.get('phone', '').strip()
            pin = request.POST.get('pin_code', '').strip()
            staff = Staff.objects.filter(phone=phone, pin_code=pin, is_active=True).first()
            if staff:
                login(request, staff.user, backend='django.contrib.auth.backends.ModelBackend')
                log_action(request, 'login', module='system', object_type='User', object_repr=staff.user.username, details=f'{staff.user.get_full_name()} logged in via PIN')
                return redirect('home')
            else:
                messages.error(request, 'Invalid phone number or PIN code.')
        else:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                log_action(request, 'login', module='system', object_type='User', object_repr=user.username, details=f'{user.get_full_name()} logged in')
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
    return render(request, 'core/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        log_action(request, 'logout', module='system', object_type='User', object_repr=request.user.username, details=f'{request.user.get_full_name()} logged out')
    logout(request)
    return redirect('login')


@login_required
@permission_required('dashboard')
def dashboard(request):
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = sum(o.total_amount for o in today_orders.filter(status='paid'))
    active_orders = Order.objects.filter(status__in=['pending', 'preparing', 'served']).count()
    available_tables = Table.objects.filter(status='available').count()
    total_tables = Table.objects.count()
    recent_orders = Order.objects.all()[:10]
    popular_items = (
        OrderItem.objects
        .filter(order__created_at__date=today)
        .values('menu_item__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )
    low_stock_count = Ingredient.objects.filter(quantity__lte=F('min_stock')).count()
    total_staff = Staff.objects.filter(is_active=True).count()
    today_expenses = sum(e.amount for e in Expense.objects.filter(date=today))
    today_profit = today_revenue - today_expenses

    context = {
        'today_orders_count': today_orders.count(),
        'today_revenue': today_revenue,
        'today_expenses': today_expenses,
        'today_profit': today_profit,
        'active_orders': active_orders,
        'available_tables': available_tables,
        'total_tables': total_tables,
        'recent_orders': recent_orders,
        'popular_items': popular_items,
        'low_stock_count': low_stock_count,
        'total_staff': total_staff,
    }
    return render(request, 'core/dashboard.html', context)


# ─── Category Views ───

@login_required
@permission_required('menu')
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'core/category_list.html', {'categories': categories})


@login_required
@permission_required('menu')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'core/category_form.html', {'form': form, 'title': 'Add Category'})


@login_required
@permission_required('menu')
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'core/category_form.html', {'form': form, 'title': 'Edit Category'})


@login_required
@permission_required('menu')
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully.')
        return redirect('category_list')
    return render(request, 'core/confirm_delete.html', {'object': category, 'type': 'category', 'back_url': 'category_list'})


# ─── Menu Item Views ───

@login_required
@permission_required('menu')
def menu_list(request):
    items = MenuItem.objects.select_related('category').all()
    categories = Category.objects.filter(is_active=True)
    category_filter = request.GET.get('category')
    if category_filter:
        items = items.filter(category_id=category_filter)
    return render(request, 'core/menu_list.html', {
        'items': items,
        'categories': categories,
        'selected_category': category_filter,
    })


def _save_ingredient_links(menu_item, post_data):
    import json
    links_data = post_data.get('ingredient_links', '[]')
    try:
        links = json.loads(links_data)
    except json.JSONDecodeError:
        links = []
    menu_item.ingredient_links.all().delete()
    for link in links:
        ing_id = link.get('ingredient_id')
        qty = link.get('quantity_used', 1)
        if ing_id:
            MenuItemIngredient.objects.create(
                menu_item=menu_item,
                ingredient_id=int(ing_id),
                quantity_used=float(qty),
            )


@login_required
@permission_required('menu')
def menu_create(request):
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save()
            _save_ingredient_links(item, request.POST)
            messages.success(request, 'Menu item created successfully.')
            return redirect('menu_list')
    else:
        form = MenuItemForm()
    ingredients = Ingredient.objects.all()
    return render(request, 'core/menu_form.html', {
        'form': form, 'title': 'Add Menu Item', 'ingredients': ingredients, 'existing_links': [],
    })


@login_required
@permission_required('menu')
def menu_edit(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            _save_ingredient_links(item, request.POST)
            messages.success(request, 'Menu item updated successfully.')
            return redirect('menu_list')
    else:
        form = MenuItemForm(instance=item)
    ingredients = Ingredient.objects.all()
    existing_links = list(item.ingredient_links.values('ingredient_id', 'quantity_used'))
    return render(request, 'core/menu_form.html', {
        'form': form, 'title': 'Edit Menu Item',
        'ingredients': ingredients, 'existing_links': existing_links,
    })


@login_required
@permission_required('menu')
def menu_delete(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Menu item deleted successfully.')
        return redirect('menu_list')
    return render(request, 'core/confirm_delete.html', {'object': item, 'type': 'menu item', 'back_url': 'menu_list'})


@login_required
@permission_required('menu')
def menu_toggle(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    item.is_available = not item.is_available
    item.save()
    status = 'available' if item.is_available else 'unavailable'
    messages.success(request, f'{item.name} is now {status}.')
    return redirect('menu_list')


# ─── Table Views ───

@login_required
@permission_required('tables')
def table_list(request):
    tables = Table.objects.all()
    active_orders = Order.objects.filter(
        table__isnull=False,
        status__in=['pending', 'preparing', 'served']
    ).select_related('table').prefetch_related('items')
    table_orders = {order.table_id: order for order in active_orders}
    for table in tables:
        table.active_order = table_orders.get(table.pk)
    return render(request, 'core/table_list.html', {'tables': tables})


@login_required
@permission_required('tables')
def table_create(request):
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Table created successfully.')
            return redirect('table_list')
    else:
        form = TableForm()
    return render(request, 'core/table_form.html', {'form': form, 'title': 'Add Table'})


@login_required
@permission_required('tables')
def table_edit(request, pk):
    table = get_object_or_404(Table, pk=pk)
    if request.method == 'POST':
        form = TableForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            messages.success(request, 'Table updated successfully.')
            return redirect('table_list')
    else:
        form = TableForm(instance=table)
    return render(request, 'core/table_form.html', {'form': form, 'title': 'Edit Table'})


@login_required
@permission_required('tables')
def table_delete(request, pk):
    table = get_object_or_404(Table, pk=pk)
    if request.method == 'POST':
        table.delete()
        messages.success(request, 'Table deleted successfully.')
        return redirect('table_list')
    return render(request, 'core/confirm_delete.html', {'object': table, 'type': 'table', 'back_url': 'table_list'})


@login_required
@permission_required('tables')
def table_toggle_status(request, pk):
    table = get_object_or_404(Table, pk=pk)
    status_cycle = {'available': 'occupied', 'occupied': 'reserved', 'reserved': 'available'}
    table.status = status_cycle.get(table.status, 'available')
    table.save()
    messages.success(request, f'Table {table.number} is now {table.get_status_display()}.')
    return redirect('table_list')


# ─── Order Views ───

@login_required
@permission_required('orders')
def order_list(request):
    orders = Order.objects.select_related('table', 'staff__user').all()

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Search by order #, customer name, or phone
    search = request.GET.get('search', '').strip()
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_phone__icontains=search)
        )

    # Date filter
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders_page = paginator.get_page(page)
    return render(request, 'core/order_list.html', {
        'orders': orders_page,
        'selected_status': status_filter,
        'status_choices': Order.STATUS_CHOICES,
        'search': search,
        'date_from': date_from or '',
        'date_to': date_to or '',
    })


@login_required
@permission_required('orders')
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            import json
            order = form.save(commit=False)
            if order.order_type == 'dine_in' and order.table:
                order.table.status = 'occupied'
                order.table.save()
            elif order.order_type != 'dine_in':
                order.table = None
            settings = RestaurantSettings.get_settings()
            order.tax_rate = settings.tax_rate
            order.save()
            cart_data = request.POST.get('cart_items', '[]')
            try:
                cart_items = json.loads(cart_data)
            except json.JSONDecodeError:
                cart_items = []
            for item in cart_items:
                menu_item = MenuItem.objects.filter(pk=item.get('id')).first()
                if menu_item:
                    qty = int(item.get('qty', 1))
                    OrderItem.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=qty,
                        price=menu_item.price,
                    )
                    deduct_stock(menu_item, qty, request.user)
            messages.success(request, f'Order #{order.id} created successfully!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm()
    categories = Category.objects.filter(is_active=True)
    menu_items = MenuItem.objects.filter(is_available=True).select_related('category')
    return render(request, 'core/order_create.html', {
        'form': form,
        'categories': categories,
        'menu_items': menu_items,
    })


@login_required
@permission_required('orders')
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items__menu_item'), pk=pk)
    can_edit = order.status in ('pending', 'preparing', 'served')
    if request.method == 'POST' and can_edit:
        menu_item_id = request.POST.get('menu_item_id')
        if menu_item_id:
            menu_item = get_object_or_404(MenuItem, pk=menu_item_id)
            existing = order.items.filter(menu_item=menu_item).first()
            if existing:
                existing.quantity += 1
                existing.save()
                deduct_stock(menu_item, 1, request.user)
            else:
                OrderItem.objects.create(
                    order=order, menu_item=menu_item,
                    quantity=1, price=menu_item.price,
                )
                deduct_stock(menu_item, 1, request.user)
            messages.success(request, f'Added {menu_item.name} to order.')
            return redirect('order_detail', pk=order.pk)
    categories = Category.objects.filter(is_active=True)
    menu_items = MenuItem.objects.filter(is_available=True).select_related('category')
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    return render(request, 'core/order_detail.html', {
        'order': order,
        'can_edit': can_edit,
        'categories': categories,
        'menu_items': menu_items,
        'payment_methods': payment_methods,
    })


@login_required
@permission_required('orders')
def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.status in ('paid', 'cancelled'):
        messages.error(request, 'Cannot edit a paid or cancelled order.')
        return redirect('order_detail', pk=order.pk)
    if request.method == 'POST':
        old_table = order.table
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            if order.order_type == 'dine_in' and order.table:
                if old_table and old_table != order.table:
                    old_table.status = 'available'
                    old_table.save()
                order.table.status = 'occupied'
                order.table.save()
            elif order.order_type != 'dine_in':
                if old_table:
                    old_table.status = 'available'
                    old_table.save()
                order.table = None
            order.save()
            messages.success(request, f'Order #{order.id} updated successfully.')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm(instance=order)
    return render(request, 'core/order_edit.html', {'form': form, 'order': order})


@login_required
@permission_required('orders')
def order_update_status(request, pk, status):
    order = get_object_or_404(Order, pk=pk)
    valid_statuses = dict(Order.STATUS_CHOICES)
    if status == 'paid' and request.method == 'GET':
        payment_methods = PaymentMethod.objects.filter(is_active=True)
        return render(request, 'core/order_pay.html', {'order': order, 'payment_methods': payment_methods})
    if status == 'paid' and request.method == 'POST':
        order.payment_method = request.POST.get('payment_method', 'cash')
        order.status = 'paid'
        order.save()
        if order.table:
            order.table.status = 'available'
            order.table.save()
        messages.success(request, f'Order #{order.id} paid via {order.payment_method_name}.')
        return redirect('order_detail', pk=order.pk)
    if status == 'cancelled' and request.method == 'POST':
        # Restore stock for all items when cancelling
        for item in order.items.select_related('menu_item'):
            if item.menu_item:
                restore_stock(item.menu_item, item.quantity, request.user)
        order.status = 'cancelled'
        order.save()
        if order.table:
            order.table.status = 'available'
            order.table.save()
        messages.success(request, f'Order #{order.id} cancelled. Stock has been restored.')
        return redirect('order_detail', pk=order.pk)
    if status in valid_statuses and status != 'cancelled':
        order.status = status
        order.save()
        messages.success(request, f'Order #{order.id} status updated to {valid_statuses[status]}.')
    return redirect('order_detail', pk=order.pk)


@login_required
@permission_required('orders')
def order_update_discount(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.discount_type = request.POST.get('discount_type', 'none')
        order.discount_value = float(request.POST.get('discount_value', 0) or 0)
        order.save()
        if order.discount_type != 'none':
            messages.success(request, f'Discount applied to Order #{order.id}.')
        else:
            messages.success(request, f'Discount removed from Order #{order.id}.')
    return redirect('order_detail', pk=order.pk)


@login_required
@permission_required('orders')
def order_item_update_qty(request, pk, item_pk, action):
    order = get_object_or_404(Order, pk=pk)
    if order.status not in ('pending', 'preparing', 'served'):
        messages.error(request, 'Cannot edit this order.')
        return redirect('order_detail', pk=order.pk)
    item = get_object_or_404(OrderItem, pk=item_pk, order=order)
    if action == 'increase':
        item.quantity += 1
        item.save()
        if item.menu_item:
            deduct_stock(item.menu_item, 1, request.user)
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
            if item.menu_item:
                restore_stock(item.menu_item, 1, request.user)
        else:
            if item.menu_item:
                restore_stock(item.menu_item, 1, request.user)
            item.delete()
            messages.success(request, 'Item removed from order. Stock restored.')
            return redirect('order_detail', pk=order.pk)
    return redirect('order_detail', pk=order.pk)


@login_required
@permission_required('orders')
def order_remove_item(request, pk, item_pk):
    order = get_object_or_404(Order, pk=pk)
    item = get_object_or_404(OrderItem, pk=item_pk, order=order)
    if item.menu_item:
        restore_stock(item.menu_item, item.quantity, request.user)
    item.delete()
    messages.success(request, 'Item removed from order. Stock restored.')
    return redirect('order_detail', pk=order.pk)


@login_required
@permission_required('orders')
def order_receipt(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items__menu_item'), pk=pk)
    settings = RestaurantSettings.get_settings()
    return render(request, 'core/order_receipt.html', {
        'order': order,
        'settings': settings,
    })


# ─── Staff Views ───

@login_required
@permission_required('staff')
def staff_list(request):
    staff = Staff.objects.select_related('user').all()
    return render(request, 'core/staff_list.html', {'staff': staff})


@login_required
@permission_required('staff')
def staff_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member created successfully.')
            return redirect('staff_list')
    else:
        form = StaffForm()
    return render(request, 'core/staff_form.html', {'form': form, 'title': 'Add Staff Member'})


@login_required
@permission_required('staff')
def staff_edit(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member updated successfully.')
            return redirect('staff_list')
    else:
        form = StaffForm(instance=staff)
    return render(request, 'core/staff_form.html', {'form': form, 'title': 'Edit Staff Member'})


@login_required
@permission_required('staff')
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        user = staff.user
        staff.delete()
        user.delete()
        messages.success(request, 'Staff member deleted successfully.')
        return redirect('staff_list')
    return render(request, 'core/confirm_delete.html', {'object': staff, 'type': 'staff member', 'back_url': 'staff_list'})


# ─── Kitchen Display (KDS) ───

@login_required
@permission_required('kitchen')
def kitchen_display(request):
    active_orders = (
        Order.objects
        .filter(status__in=['pending', 'preparing'])
        .select_related('table', 'staff__user')
        .prefetch_related('items__menu_item')
        .order_by('created_at')
    )
    pending_count = active_orders.filter(status='pending').count()
    preparing_count = active_orders.filter(status='preparing').count()
    return render(request, 'core/kitchen_display.html', {
        'orders': active_orders,
        'pending_count': pending_count,
        'preparing_count': preparing_count,
        'total_count': pending_count + preparing_count,
    })


@login_required
@permission_required('kitchen')
def kitchen_update_status(request, pk, status):
    order = get_object_or_404(Order, pk=pk)
    if status in ('preparing', 'served'):
        order.status = status
        order.save()
    return redirect('kitchen_display')


# ─── Inventory / Stock Views ───

@login_required
@permission_required('inventory')
def ingredient_list(request):
    ingredients = Ingredient.objects.all()
    low_stock = request.GET.get('low_stock')
    if low_stock:
        ingredients = ingredients.filter(quantity__lte=F('min_stock'))
    return render(request, 'core/ingredient_list.html', {
        'ingredients': ingredients,
        'show_low_stock': low_stock,
    })


@login_required
@permission_required('inventory')
def ingredient_create(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ingredient added successfully.')
            return redirect('ingredient_list')
    else:
        form = IngredientForm()
    return render(request, 'core/ingredient_form.html', {'form': form, 'title': 'Add Ingredient'})


@login_required
@permission_required('inventory')
def ingredient_edit(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ingredient updated successfully.')
            return redirect('ingredient_list')
    else:
        form = IngredientForm(instance=ingredient)
    return render(request, 'core/ingredient_form.html', {'form': form, 'title': 'Edit Ingredient'})


@login_required
@permission_required('inventory')
def ingredient_delete(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        ingredient.delete()
        messages.success(request, 'Ingredient deleted successfully.')
        return redirect('ingredient_list')
    return render(request, 'core/confirm_delete.html', {'object': ingredient, 'type': 'ingredient', 'back_url': 'ingredient_list'})


@login_required
@permission_required('inventory')
def stock_movement_create(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            movement.save()
            ingredient = movement.ingredient
            if movement.movement_type == 'in':
                ingredient.quantity += movement.quantity
            elif movement.movement_type == 'out':
                ingredient.quantity -= movement.quantity
            else:
                ingredient.quantity = movement.quantity
            ingredient.last_restocked = timezone.now()
            ingredient.save()
            messages.success(request, f'Stock movement recorded for {ingredient.name}.')
            return redirect('ingredient_list')
    else:
        form = StockMovementForm()
    return render(request, 'core/stock_movement_form.html', {'form': form})


# ─── Reports Views ───

@login_required
@permission_required('reports')
def sales_report(request):
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    period = request.GET.get('period', 'today')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from and date_to:
        period = 'custom'
        start_date = date_from
        end_date = date_to
        orders = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date, status='paid')
    elif date_from:
        period = 'custom'
        start_date = date_from
        orders = Order.objects.filter(created_at__date__gte=start_date, status='paid')
    else:
        if period == 'yesterday':
            orders = Order.objects.filter(created_at__date=yesterday, status='paid')
        elif period == 'today':
            orders = Order.objects.filter(created_at__date=today, status='paid')
        elif period == 'week':
            orders = Order.objects.filter(created_at__date__gte=today - timedelta(days=7), status='paid')
        elif period == 'month':
            orders = Order.objects.filter(created_at__date__gte=today - timedelta(days=30), status='paid')
        else:
            orders = Order.objects.filter(created_at__date=today, status='paid')

    total_revenue = sum(o.total_amount for o in orders)
    total_orders = orders.count()

    # Expenses for the same period
    if date_from and date_to:
        expenses_qs = Expense.objects.filter(date__gte=date_from, date__lte=date_to)
    elif date_from:
        expenses_qs = Expense.objects.filter(date__gte=date_from)
    elif period == 'yesterday':
        expenses_qs = Expense.objects.filter(date=yesterday)
    elif period == 'today':
        expenses_qs = Expense.objects.filter(date=today)
    elif period == 'week':
        expenses_qs = Expense.objects.filter(date__gte=today - timedelta(days=7))
    elif period == 'month':
        expenses_qs = Expense.objects.filter(date__gte=today - timedelta(days=30))
    else:
        expenses_qs = Expense.objects.filter(date=today)
    total_expenses = sum(e.amount for e in expenses_qs)
    profit = total_revenue - total_expenses

    top_items = (
        OrderItem.objects
        .filter(order__in=orders)
        .values('menu_item__name')
        .annotate(total_qty=Sum('quantity'), total_sales=Sum('price'))
        .order_by('-total_qty')[:10]
    )

    daily_revenue = (
        orders
        .values(day=F('created_at__date'))
        .annotate(order_count=Count('id'))
        .order_by('day')
    )

    context = {
        'period': period,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'avg_order': total_revenue / total_orders if total_orders > 0 else 0,
        'total_expenses': total_expenses,
        'profit': profit,
        'top_items': top_items,
        'daily_revenue': daily_revenue,
        'orders': orders[:20],
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'core/sales_report.html', context)


@login_required
@permission_required('reports')
def daily_summary(request):
    today = timezone.now().date()
    date_str = request.GET.get('date', str(today))

    orders = Order.objects.filter(created_at__date=date_str)
    paid_orders = orders.filter(status='paid')
    total_revenue = sum(o.total_amount for o in paid_orders)

    status_breakdown = orders.values('status').annotate(count=Count('id'))

    day_expenses = Expense.objects.filter(date=date_str)
    total_expenses = sum(e.amount for e in day_expenses)
    profit = total_revenue - total_expenses

    context = {
        'selected_date': date_str,
        'total_orders': orders.count(),
        'paid_orders': paid_orders.count(),
        'cancelled_orders': orders.filter(status='cancelled').count(),
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'profit': profit,
        'status_breakdown': status_breakdown,
        'day_expenses': day_expenses.select_related('category', 'payment_method', 'paid_by__user')[:10],
    }
    return render(request, 'core/daily_summary.html', context)


# ─── Settings Views ───

@login_required
@permission_required('settings')
def settings_general(request):
    settings = RestaurantSettings.get_settings()
    if request.method == 'POST':
        form = RestaurantSettingsForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully.')
            return redirect('settings_general')
    else:
        form = RestaurantSettingsForm(instance=settings)
    return render(request, 'core/settings_general.html', {'form': form})


@login_required
@permission_required('settings')
def payment_method_list(request):
    methods = PaymentMethod.objects.all()
    return render(request, 'core/payment_method_list.html', {'methods': methods})


@login_required
@permission_required('settings')
def payment_method_create(request):
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment method created successfully.')
            return redirect('payment_method_list')
    else:
        form = PaymentMethodForm()
    return render(request, 'core/payment_method_form.html', {'form': form, 'title': 'Add Payment Method'})


@login_required
@permission_required('settings')
def payment_method_edit(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=method)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment method updated successfully.')
            return redirect('payment_method_list')
    else:
        form = PaymentMethodForm(instance=method)
    return render(request, 'core/payment_method_form.html', {'form': form, 'title': 'Edit Payment Method'})


@login_required
@permission_required('settings')
def payment_method_delete(request, pk):
    method = get_object_or_404(PaymentMethod, pk=pk)
    if request.method == 'POST':
        method.delete()
        messages.success(request, 'Payment method deleted successfully.')
        return redirect('payment_method_list')
    return render(request, 'core/confirm_delete.html', {'object': method, 'type': 'payment method', 'back_url': 'payment_method_list'})


# ─── Expense Views ───

@login_required
@permission_required('expenses')
def expense_list(request):
    expenses = Expense.objects.select_related('category', 'payment_method', 'paid_by__user').all()

    search = request.GET.get('search', '').strip()
    if search:
        expenses = expenses.filter(
            Q(title__icontains=search) |
            Q(notes__icontains=search)
        )

    category_filter = request.GET.get('category')
    if category_filter:
        expenses = expenses.filter(category_id=category_filter)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)

    total_expenses = sum(e.amount for e in expenses)

    # Current user's expenses
    my_expenses = Expense.objects.filter(created_by=request.user).select_related('category', 'payment_method')
    my_total = sum(e.amount for e in my_expenses)

    payment_methods = PaymentMethod.objects.filter(is_active=True)
    categories = ExpenseCategory.objects.filter(is_active=True)

    paginator = Paginator(expenses, 10)
    page = request.GET.get('page')
    expenses_page = paginator.get_page(page)

    return render(request, 'core/expense_list.html', {
        'expenses': expenses_page,
        'total_expenses': total_expenses,
        'payment_methods': payment_methods,
        'categories': categories,
        'search': search,
        'selected_category': category_filter,
        'date_from': date_from or '',
        'date_to': date_to or '',
        'my_expenses': my_expenses[:5],
        'my_total': my_total,
    })


@login_required
@permission_required('expenses')
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, f'Expense "{expense.title}" of {expense.amount} recorded. Deducted from {expense.payment_method.name}.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(initial={'date': timezone.now().date()})
    return render(request, 'core/expense_form.html', {'form': form, 'title': 'Add Expense'})


@login_required
@permission_required('expenses')
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'core/expense_form.html', {'form': form, 'title': 'Edit Expense'})


@login_required
@permission_required('expenses')
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted. Amount restored to payment method balance.')
        return redirect('expense_list')
    return render(request, 'core/confirm_delete.html', {'object': expense, 'type': 'expense', 'back_url': 'expense_list'})


@login_required
@permission_required('expenses')
def expense_category_list(request):
    categories = ExpenseCategory.objects.all()
    return render(request, 'core/expense_category_list.html', {'categories': categories})


@login_required
@permission_required('expenses')
def expense_category_create(request):
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category created.')
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm()
    return render(request, 'core/expense_category_form.html', {'form': form, 'title': 'Add Expense Category'})


@login_required
@permission_required('expenses')
def expense_category_edit(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense category updated.')
            return redirect('expense_category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    return render(request, 'core/expense_category_form.html', {'form': form, 'title': 'Edit Expense Category'})


@login_required
@permission_required('expenses')
def expense_category_delete(request, pk):
    category = get_object_or_404(ExpenseCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Expense category deleted.')
        return redirect('expense_category_list')
    return render(request, 'core/confirm_delete.html', {'object': category, 'type': 'expense category', 'back_url': 'expense_category_list'})


# ─── Role & Permission Views ───

@login_required
@permission_required('roles')
def role_list(request):
    roles = Role.objects.all()
    return render(request, 'core/role_list.html', {
        'roles': roles,
        'available_permissions': AVAILABLE_PERMISSIONS,
    })


@login_required
@permission_required('roles')
def role_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Role name is required.')
            return redirect('role_create')
        if Role.objects.filter(name=name).exists():
            messages.error(request, 'A role with this name already exists.')
            return redirect('role_create')
        perms = request.POST.getlist('permissions')
        Role.objects.create(name=name, permissions=perms)
        messages.success(request, f'Role "{name}" created with {len(perms)} permissions.')
        return redirect('role_list')
    return render(request, 'core/role_form.html', {
        'title': 'Create Role',
        'available_permissions': AVAILABLE_PERMISSIONS,
        'selected_permissions': [],
    })


@login_required
@permission_required('roles')
def role_edit(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Role name is required.')
            return redirect('role_edit', pk=pk)
        perms = request.POST.getlist('permissions')
        role.name = name
        role.permissions = perms
        role.save()
        messages.success(request, f'Role "{name}" updated.')
        return redirect('role_list')
    return render(request, 'core/role_form.html', {
        'title': f'Edit Role: {role.name}',
        'role': role,
        'available_permissions': AVAILABLE_PERMISSIONS,
        'selected_permissions': role.permissions,
    })


@login_required
@permission_required('roles')
def role_delete(request, pk):
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        role.delete()
        messages.success(request, 'Role deleted.')
        return redirect('role_list')
    return render(request, 'core/confirm_delete.html', {'object': role, 'type': 'role', 'back_url': 'role_list'})


# ─── System Logs ───

@login_required
@permission_required('logs')
def log_list(request):
    tab = request.GET.get('tab', 'audit')
    search = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if tab == 'errors':
        logs = ErrorLog.objects.all()
        if search:
            logs = logs.filter(
                Q(error_type__icontains=search) |
                Q(error_message__icontains=search) |
                Q(url__icontains=search)
            )
        if date_from:
            logs = logs.filter(created_at__date__gte=date_from)
        if date_to:
            logs = logs.filter(created_at__date__lte=date_to)
        total_count = logs.count()
    else:
        logs = AuditLog.objects.select_related('user').all()
        action_filter = request.GET.get('action')
        if action_filter:
            logs = logs.filter(action=action_filter)
        if search:
            logs = logs.filter(
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(object_type__icontains=search) |
                Q(details__icontains=search) |
                Q(url__icontains=search)
            )
        if date_from:
            logs = logs.filter(created_at__date__gte=date_from)
        if date_to:
            logs = logs.filter(created_at__date__lte=date_to)
        total_count = logs.count()

    paginator = Paginator(logs, 25)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)

    audit_count = AuditLog.objects.count()
    error_count = ErrorLog.objects.count()

    return render(request, 'core/log_list.html', {
        'logs': logs_page,
        'tab': tab,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'action_filter': request.GET.get('action', ''),
        'total_count': total_count,
        'audit_count': audit_count,
        'error_count': error_count,
        'action_choices': AuditLog.ACTION_CHOICES,
    })


@login_required
@permission_required('logs')
def log_clear(request, log_type):
    if request.method == 'POST':
        if log_type == 'audit':
            count = AuditLog.objects.count()
            AuditLog.objects.all().delete()
            messages.success(request, f'Cleared {count} audit logs.')
        elif log_type == 'errors':
            count = ErrorLog.objects.count()
            ErrorLog.objects.all().delete()
            messages.success(request, f'Cleared {count} error logs.')
    return redirect('log_list')


def toggle_language(request):
    current = request.session.get('lang', 'en')
    request.session['lang'] = 'so' if current == 'en' else 'en'
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def profile_settings(request):
    user = request.user
    staff, _ = Staff.objects.get_or_create(user=user)
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        new_password = request.POST.get('new_password', '')
        if new_password:
            user.set_password(new_password)
        user.save()
        if 'avatar' in request.FILES:
            staff.avatar = request.FILES['avatar']
            staff.save()
        if request.POST.get('remove_avatar'):
            staff.avatar = None
            staff.save()
        new_pin = request.POST.get('pin_code', '').strip()
        if new_pin:
            if len(new_pin) == 4 and new_pin.isdigit():
                staff.pin_code = new_pin
                staff.save()
            else:
                messages.error(request, 'PIN must be exactly 4 digits.')
                return redirect('profile_settings')
        if new_password:
            login(request, user)
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile_settings')
    return render(request, 'core/profile_settings.html', {'user': user, 'staff': staff})
