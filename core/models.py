from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='menu_items/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - ${self.price}"


class Table(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
    ]
    number = models.IntegerField(unique=True)
    capacity = models.IntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Table {self.number} ({self.capacity} seats)"


AVAILABLE_PERMISSIONS = [
    ('dashboard', 'Dashboard'),
    ('orders', 'Orders'),
    ('menu', 'Menu & Categories'),
    ('tables', 'Tables'),
    ('kitchen', 'Kitchen Display'),
    ('inventory', 'Inventory'),
    ('expenses', 'Expenses'),
    ('staff', 'Staff Management'),
    ('roles', 'Roles & Permissions'),
    ('reports', 'Reports'),
    ('settings', 'Settings'),
    ('logs', 'System Logs'),
]


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def has_permission(self, perm):
        return perm in self.permissions


class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    phone = models.CharField(max_length=20, blank=True)
    pin_code = models.CharField(max_length=4, blank=True, help_text='4-digit quick login PIN')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Staff'
        ordering = ['user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role.name if self.role else 'No Role'}"

    def has_permission(self, perm):
        if not self.role:
            return False
        return self.role.has_permission(perm)


class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Dine-In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('served', 'Served'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    DISCOUNT_TYPE_CHOICES = [
        ('none', 'No Discount'),
        ('percent', 'Percentage %'),
        ('fixed', 'Fixed Amount'),
    ]
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='dine_in')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    delivery_address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, default='', blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='none')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.order_type == 'dine_in':
            return f"Order #{self.id} - Table {self.table.number if self.table else 'N/A'}"
        elif self.order_type == 'delivery':
            return f"Order #{self.id} - Delivery ({self.customer_name or 'N/A'})"
        return f"Order #{self.id} - Takeaway ({self.customer_name or 'Walk-in'})"

    @property
    def payment_method_name(self):
        if not self.payment_method:
            return 'Not Paid'
        pm = PaymentMethod.objects.filter(code=self.payment_method).first()
        return pm.name if pm else self.payment_method.title()

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def discount_amount(self):
        if self.discount_type == 'percent':
            return self.subtotal * self.discount_value / 100
        elif self.discount_type == 'fixed':
            return min(self.discount_value, self.subtotal)
        return 0

    @property
    def tax_amount(self):
        return (self.subtotal - self.discount_amount) * self.tax_rate / 100

    @property
    def total_amount(self):
        return self.subtotal - self.discount_amount + self.tax_amount


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name if self.menu_item else 'Deleted Item'}"

    @property
    def subtotal(self):
        return self.price * self.quantity


# ─── Menu Item ↔ Ingredient Link ───

class MenuItemIngredient(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='ingredient_links')
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE, related_name='menu_item_links')
    quantity_used = models.DecimalField(max_digits=10, decimal_places=2, default=1,
        help_text='How much of this ingredient is used per 1 menu item sold')

    class Meta:
        unique_together = ['menu_item', 'ingredient']

    def __str__(self):
        return f"{self.menu_item.name} uses {self.quantity_used} {self.ingredient.unit} of {self.ingredient.name}"


# ─── Inventory / Stock ───

class Ingredient(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Liter'),
        ('ml', 'Milliliter'),
        ('pcs', 'Pieces'),
        ('box', 'Box'),
        ('bag', 'Bag'),
    ]
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='kg')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier = models.CharField(max_length=200, blank=True)
    last_restocked = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock

    @property
    def total_value(self):
        return self.quantity * self.cost_per_unit


class StockMovement(models.Model):
    TYPE_CHOICES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
    ]
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.ingredient.name} ({self.quantity})"


# ─── Attendance ───

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'On Leave'),
    ]
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['staff', 'date']

    def __str__(self):
        return f"{self.staff.user.get_full_name()} - {self.date} ({self.get_status_display()})"


# ─── Expenses ───

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Expense Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    title = models.CharField(max_length=200)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.ForeignKey('PaymentMethod', on_delete=models.SET_NULL, null=True, related_name='expenses')
    paid_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, related_name='expenses')
    date = models.DateField()
    notes = models.TextField(blank=True)
    receipt_image = models.ImageField(upload_to='expenses/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.amount}"


# ─── Payment Methods ───

class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True)
    icon = models.CharField(max_length=20, default='cash', help_text='Icon identifier: cash, card, mobile, bank, wallet, check, online')
    color = models.CharField(max_length=20, default='green', help_text='Color theme: green, blue, purple, orange, red, teal, pink')
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def total_income(self):
        orders = Order.objects.filter(payment_method=self.code, status='paid')
        return sum(o.total_amount for o in orders)

    @property
    def total_expenses(self):
        from django.db.models import Sum
        result = self.expenses.aggregate(total=Sum('amount'))
        return result['total'] or 0

    @property
    def balance(self):
        return self.total_income - self.total_expenses


# ─── Settings ───

class RestaurantSettings(models.Model):
    restaurant_name = models.CharField(max_length=200, default='My Restaurant')
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency_symbol = models.CharField(max_length=5, default='$')
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    logo = models.ImageField(upload_to='settings/', blank=True, null=True)

    class Meta:
        verbose_name = 'Restaurant Settings'
        verbose_name_plural = 'Restaurant Settings'

    def __str__(self):
        return self.restaurant_name

    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


# ─── System Logs ───

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('status_change', 'Status Change'),
        ('payment', 'Payment'),
        ('stock', 'Stock Movement'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=50, blank=True)
    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os_info = models.CharField(max_length=100, blank=True)
    url = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.object_type} - {self.created_at}"


class ErrorLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='error_logs')
    url = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    error_type = models.CharField(max_length=200)
    error_message = models.TextField()
    traceback = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os_info = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.error_type} - {self.url} - {self.created_at}"
