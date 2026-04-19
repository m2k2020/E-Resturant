from django import forms
from django.contrib.auth.models import User
from .models import (
    Category, MenuItem, Table, Staff, Order, OrderItem,
    Ingredient, StockMovement, Attendance, RestaurantSettings,
    PaymentMethod, ExpenseCategory, Expense, Role,
)


tw = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm'
tw_select = tw
tw_check = 'h-4 w-4 text-indigo-600 rounded focus:ring-indigo-500'
tw_file = 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
tw_textarea = tw + ' min-h-[80px]'


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': tw, 'placeholder': 'Category name'}),
            'description': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Description (optional)', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': tw_check}),
        }


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['name', 'category', 'description', 'price', 'is_available', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': tw, 'placeholder': 'Item name'}),
            'category': forms.Select(attrs={'class': tw_select}),
            'description': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Description (optional)', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': tw, 'placeholder': '0.00', 'step': '0.01'}),
            'is_available': forms.CheckboxInput(attrs={'class': tw_check}),
            'image': forms.ClearableFileInput(attrs={'class': tw_file}),
        }


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['number', 'capacity', 'status']
        widgets = {
            'number': forms.NumberInput(attrs={'class': tw, 'placeholder': 'Table number'}),
            'capacity': forms.NumberInput(attrs={'class': tw, 'placeholder': 'Seating capacity'}),
            'status': forms.Select(attrs={'class': tw_select}),
        }


class StaffForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': tw, 'placeholder': 'First name'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': tw, 'placeholder': 'Last name'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': tw, 'placeholder': 'Email (optional)'}))
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': tw, 'placeholder': 'Username'}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': tw, 'placeholder': 'Password (leave blank to keep current)'}))

    class Meta:
        model = Staff
        fields = ['role', 'phone', 'pin_code', 'avatar', 'is_active']
        widgets = {
            'role': forms.Select(attrs={'class': tw_select}),
            'phone': forms.TextInput(attrs={'class': tw, 'placeholder': 'Phone number'}),
            'pin_code': forms.TextInput(attrs={'class': tw, 'placeholder': '4-digit PIN for quick login', 'maxlength': '4', 'pattern': '[0-9]{4}'}),
            'avatar': forms.ClearableFileInput(attrs={'class': tw_file}),
            'is_active': forms.CheckboxInput(attrs={'class': tw_check}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['username'].initial = self.instance.user.username
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True

    def save(self, commit=True):
        staff = super().save(commit=False)
        if staff.pk:
            user = staff.user
        else:
            user = User()
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['username']
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            staff.user = user
            staff.save()
        return staff


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_type', 'table', 'staff', 'customer_name', 'customer_phone', 'delivery_address', 'notes']
        widgets = {
            'order_type': forms.Select(attrs={'class': tw_select, 'id': 'orderType'}),
            'table': forms.Select(attrs={'class': tw_select, 'id': 'tableSelect'}),
            'staff': forms.Select(attrs={'class': tw_select}),
            'customer_name': forms.TextInput(attrs={'class': tw, 'placeholder': 'Customer name'}),
            'customer_phone': forms.TextInput(attrs={'class': tw, 'placeholder': 'Phone number'}),
            'delivery_address': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Delivery address', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Order notes (optional)', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['table'].required = False
        self.fields['customer_name'].required = False
        self.fields['customer_phone'].required = False
        self.fields['delivery_address'].required = False


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity']
        widgets = {
            'menu_item': forms.Select(attrs={'class': tw_select}),
            'quantity': forms.NumberInput(attrs={'class': tw, 'min': '1', 'value': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['menu_item'].queryset = MenuItem.objects.filter(is_available=True)


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'unit', 'quantity', 'min_stock', 'cost_per_unit', 'supplier']
        widgets = {
            'name': forms.TextInput(attrs={'class': tw, 'placeholder': 'Ingredient name'}),
            'unit': forms.Select(attrs={'class': tw_select}),
            'quantity': forms.NumberInput(attrs={'class': tw, 'placeholder': '0', 'step': '0.01'}),
            'min_stock': forms.NumberInput(attrs={'class': tw, 'placeholder': '5', 'step': '0.01'}),
            'cost_per_unit': forms.NumberInput(attrs={'class': tw, 'placeholder': '0.00', 'step': '0.01'}),
            'supplier': forms.TextInput(attrs={'class': tw, 'placeholder': 'Supplier name'}),
        }


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['ingredient', 'movement_type', 'quantity', 'notes']
        widgets = {
            'ingredient': forms.Select(attrs={'class': tw_select}),
            'movement_type': forms.Select(attrs={'class': tw_select}),
            'quantity': forms.NumberInput(attrs={'class': tw, 'placeholder': '0', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Notes (optional)', 'rows': 2}),
        }


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['staff', 'date', 'status', 'check_in', 'check_out', 'notes']
        widgets = {
            'staff': forms.Select(attrs={'class': tw_select}),
            'date': forms.DateInput(attrs={'class': tw, 'type': 'date'}),
            'status': forms.Select(attrs={'class': tw_select}),
            'check_in': forms.TimeInput(attrs={'class': tw, 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': tw, 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Notes (optional)', 'rows': 2}),
        }


class PaymentMethodForm(forms.ModelForm):
    ICON_CHOICES = [
        ('cash', 'Cash / Bills'),
        ('card', 'Credit / Debit Card'),
        ('mobile', 'Mobile Money'),
        ('bank', 'Bank Transfer'),
        ('wallet', 'Digital Wallet'),
        ('check', 'Check / Cheque'),
        ('online', 'Online Payment'),
    ]
    COLOR_CHOICES = [
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('red', 'Red'),
        ('teal', 'Teal'),
        ('pink', 'Pink'),
    ]
    icon = forms.ChoiceField(choices=ICON_CHOICES, widget=forms.Select(attrs={'class': tw_select}))
    color = forms.ChoiceField(choices=COLOR_CHOICES, widget=forms.Select(attrs={'class': tw_select}))

    class Meta:
        model = PaymentMethod
        fields = ['name', 'code', 'icon', 'color', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': tw, 'placeholder': 'e.g. Cash, Visa Card, EVC Plus'}),
            'code': forms.TextInput(attrs={'class': tw, 'placeholder': 'e.g. cash, visa, evc-plus'}),
            'is_active': forms.CheckboxInput(attrs={'class': tw_check}),
            'sort_order': forms.NumberInput(attrs={'class': tw, 'placeholder': '0'}),
        }


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': tw, 'placeholder': 'e.g. Rent, Supplies, Salary, Utilities'}),
            'is_active': forms.CheckboxInput(attrs={'class': tw_check}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'payment_method', 'paid_by', 'date', 'notes', 'receipt_image']
        widgets = {
            'title': forms.TextInput(attrs={'class': tw, 'placeholder': 'What was this expense for?'}),
            'category': forms.Select(attrs={'class': tw_select}),
            'amount': forms.NumberInput(attrs={'class': tw, 'placeholder': '0.00', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': tw_select}),
            'paid_by': forms.Select(attrs={'class': tw_select}),
            'date': forms.DateInput(attrs={'class': tw, 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Details (optional)', 'rows': 2}),
            'receipt_image': forms.ClearableFileInput(attrs={'class': tw_file}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].queryset = PaymentMethod.objects.filter(is_active=True)
        self.fields['paid_by'].queryset = Staff.objects.filter(is_active=True)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)


class RestaurantSettingsForm(forms.ModelForm):
    class Meta:
        model = RestaurantSettings
        fields = [
            'restaurant_name', 'address', 'phone', 'email',
            'tax_rate', 'currency_symbol', 'opening_time', 'closing_time', 'logo',
        ]
        widgets = {
            'restaurant_name': forms.TextInput(attrs={'class': tw, 'placeholder': 'Restaurant name'}),
            'address': forms.Textarea(attrs={'class': tw_textarea, 'placeholder': 'Address', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': tw, 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': tw, 'placeholder': 'Email'}),
            'tax_rate': forms.NumberInput(attrs={'class': tw, 'placeholder': '0.00', 'step': '0.01'}),
            'currency_symbol': forms.TextInput(attrs={'class': tw, 'placeholder': '$'}),
            'opening_time': forms.TimeInput(attrs={'class': tw, 'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'class': tw, 'type': 'time'}),
            'logo': forms.ClearableFileInput(attrs={'class': tw_file}),
        }
