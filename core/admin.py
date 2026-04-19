from django.contrib import admin
from .models import (
    Category, MenuItem, Table, Staff, Order, OrderItem,
    Ingredient, StockMovement, Attendance, RestaurantSettings,
    MenuItemIngredient, PaymentMethod, ExpenseCategory, Expense, Role,
    AuditLog, ErrorLog,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']


class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available']
    list_filter = ['category', 'is_available']
    search_fields = ['name']
    inlines = [MenuItemIngredientInline]


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'capacity', 'status']
    list_filter = ['status']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'is_active']
    list_filter = ['role', 'is_active']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'staff', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    inlines = [OrderItemInline]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'quantity', 'unit', 'min_stock', 'cost_per_unit']
    list_filter = ['unit']
    search_fields = ['name']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['ingredient', 'movement_type', 'quantity', 'created_by', 'created_at']
    list_filter = ['movement_type', 'created_at']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'date', 'status', 'check_in', 'check_out']
    list_filter = ['status', 'date']


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'payment_method', 'paid_by', 'date', 'category']
    list_filter = ['category', 'payment_method', 'date']
    search_fields = ['title', 'notes']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon', 'color', 'is_active', 'sort_order']
    list_filter = ['is_active']
    prepopulated_fields = {'code': ('name',)}


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'user', 'action', 'module', 'object_type', 'ip_address', 'device_type']
    list_filter = ['action', 'module', 'device_type', 'created_at']
    search_fields = ['user__username', 'details', 'url']
    readonly_fields = ['user', 'action', 'module', 'object_type', 'object_id', 'object_repr', 'details', 'ip_address', 'user_agent', 'device_type', 'browser', 'os_info', 'url', 'method', 'created_at']


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'error_type', 'url', 'user', 'device_type']
    list_filter = ['error_type', 'created_at']
    search_fields = ['error_message', 'url']


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(admin.ModelAdmin):
    list_display = ['restaurant_name', 'phone', 'email']
