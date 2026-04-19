import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import Order, Expense, Ingredient
from .decorators import permission_required


@login_required
@permission_required('orders')
def export_orders(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d")}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order #', 'Type', 'Table', 'Customer', 'Phone', 'Items', 'Subtotal', 'Discount', 'Tax', 'Total', 'Status', 'Payment Method', 'Staff', 'Date'])

    orders = Order.objects.select_related('table', 'staff__user').prefetch_related('items').all()

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status = request.GET.get('status')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    if status:
        orders = orders.filter(status=status)

    for order in orders:
        writer.writerow([
            order.id,
            order.get_order_type_display(),
            order.table.number if order.table else '',
            order.customer_name,
            order.customer_phone,
            order.items.count(),
            order.subtotal,
            order.discount_amount,
            order.tax_amount,
            order.total_amount,
            order.get_status_display(),
            order.payment_method_name if order.payment_method else '',
            order.staff.user.get_full_name() if order.staff else '',
            order.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


@login_required
@permission_required('expenses')
def export_expenses(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="expenses_{timezone.now().strftime("%Y%m%d")}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Title', 'Category', 'Amount', 'Payment Method', 'Paid By', 'Notes'])

    expenses = Expense.objects.select_related('category', 'payment_method', 'paid_by__user').all()

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)

    for exp in expenses:
        writer.writerow([
            exp.date.strftime('%Y-%m-%d'),
            exp.title,
            exp.category.name if exp.category else '',
            exp.amount,
            exp.payment_method.name if exp.payment_method else '',
            exp.paid_by.user.get_full_name() if exp.paid_by else '',
            exp.notes,
        ])
    return response


@login_required
@permission_required('inventory')
def export_inventory(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="inventory_{timezone.now().strftime("%Y%m%d")}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Unit', 'Quantity', 'Min Stock', 'Cost/Unit', 'Total Value', 'Supplier', 'Low Stock'])

    for ing in Ingredient.objects.all():
        writer.writerow([
            ing.name,
            ing.get_unit_display(),
            ing.quantity,
            ing.min_stock,
            ing.cost_per_unit,
            ing.total_value,
            ing.supplier,
            'Yes' if ing.is_low_stock else 'No',
        ])
    return response


@login_required
@permission_required('reports')
def export_sales(request):
    response = HttpResponse(content_type='text/csv')
    period = request.GET.get('period', 'today')
    today = timezone.now().date()

    if period == 'yesterday':
        orders = Order.objects.filter(created_at__date=today - timedelta(days=1), status='paid')
    elif period == 'week':
        orders = Order.objects.filter(created_at__date__gte=today - timedelta(days=7), status='paid')
    elif period == 'month':
        orders = Order.objects.filter(created_at__date__gte=today - timedelta(days=30), status='paid')
    else:
        orders = Order.objects.filter(created_at__date=today, status='paid')

    response['Content-Disposition'] = f'attachment; filename="sales_{period}_{timezone.now().strftime("%Y%m%d")}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order #', 'Type', 'Table', 'Customer', 'Items', 'Total', 'Payment Method', 'Date'])

    for order in orders.select_related('table', 'staff__user').prefetch_related('items'):
        writer.writerow([
            order.id,
            order.get_order_type_display(),
            order.table.number if order.table else '',
            order.customer_name,
            order.items.count(),
            order.total_amount,
            order.payment_method_name if order.payment_method else '',
            order.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response
