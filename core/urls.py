from django.urls import path
from . import views
from . import export_views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Home (Module Launcher)
    path('', views.home, name='home'),
    path('toggle-language/', views.toggle_language, name='toggle_language'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Menu Items
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/add/', views.menu_create, name='menu_create'),
    path('menu/<int:pk>/edit/', views.menu_edit, name='menu_edit'),
    path('menu/<int:pk>/delete/', views.menu_delete, name='menu_delete'),
    path('menu/<int:pk>/toggle/', views.menu_toggle, name='menu_toggle'),

    # Tables
    path('tables/', views.table_list, name='table_list'),
    path('tables/add/', views.table_create, name='table_create'),
    path('tables/<int:pk>/edit/', views.table_edit, name='table_edit'),
    path('tables/<int:pk>/delete/', views.table_delete, name='table_delete'),
    path('tables/<int:pk>/toggle/', views.table_toggle_status, name='table_toggle_status'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/new/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/', views.order_edit, name='order_edit'),
    path('orders/<int:pk>/receipt/', views.order_receipt, name='order_receipt'),
    path('orders/<int:pk>/status/<str:status>/', views.order_update_status, name='order_update_status'),
    path('orders/<int:pk>/discount/', views.order_update_discount, name='order_update_discount'),
    path('orders/<int:pk>/item/<int:item_pk>/<str:action>/', views.order_item_update_qty, name='order_item_update_qty'),
    path('orders/<int:pk>/remove-item/<int:item_pk>/', views.order_remove_item, name='order_remove_item'),

    # Kitchen Display
    path('kitchen/', views.kitchen_display, name='kitchen_display'),
    path('kitchen/<int:pk>/status/<str:status>/', views.kitchen_update_status, name='kitchen_update_status'),

    # Staff
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),

# Inventory / Stock
    path('inventory/', views.ingredient_list, name='ingredient_list'),
    path('inventory/add/', views.ingredient_create, name='ingredient_create'),
    path('inventory/<int:pk>/edit/', views.ingredient_edit, name='ingredient_edit'),
    path('inventory/<int:pk>/delete/', views.ingredient_delete, name='ingredient_delete'),
    path('inventory/stock-movement/', views.stock_movement_create, name='stock_movement_create'),

    # Reports
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/daily/', views.daily_summary, name='daily_summary'),

    # Logs
    path('logs/', views.log_list, name='log_list'),
    path('logs/clear/<str:log_type>/', views.log_clear, name='log_clear'),

    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/categories/', views.expense_category_list, name='expense_category_list'),
    path('expenses/categories/add/', views.expense_category_create, name='expense_category_create'),
    path('expenses/categories/<int:pk>/edit/', views.expense_category_edit, name='expense_category_edit'),
    path('expenses/categories/<int:pk>/delete/', views.expense_category_delete, name='expense_category_delete'),

    # Export CSV
    path('export/orders/', export_views.export_orders, name='export_orders'),
    path('export/expenses/', export_views.export_expenses, name='export_expenses'),
    path('export/inventory/', export_views.export_inventory, name='export_inventory'),
    path('export/sales/', export_views.export_sales, name='export_sales'),

    # Settings
    path('settings/', views.settings_general, name='settings_general'),
    path('settings/profile/', views.profile_settings, name='profile_settings'),

    # Roles & Permissions
    path('settings/roles/', views.role_list, name='role_list'),
    path('settings/roles/add/', views.role_create, name='role_create'),
    path('settings/roles/<int:pk>/edit/', views.role_edit, name='role_edit'),
    path('settings/roles/<int:pk>/delete/', views.role_delete, name='role_delete'),

    # Payment Methods (Settings)
    path('settings/payment-methods/', views.payment_method_list, name='payment_method_list'),
    path('settings/payment-methods/add/', views.payment_method_create, name='payment_method_create'),
    path('settings/payment-methods/<int:pk>/edit/', views.payment_method_edit, name='payment_method_edit'),
    path('settings/payment-methods/<int:pk>/delete/', views.payment_method_delete, name='payment_method_delete'),
]
