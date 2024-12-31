from django import forms
from products.models import Category, Product, SKU, VariationName, VariationValue, SubcategoryVariation, ProductAttribute, ProductAttributeValue, SubcategoryAttribute
from accounts.models import CustomUser
from cart.models import Coupon, Order
from .models import PinCode
from accounts.country_choices import COUNTRY_CHOICES


# Category Form

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'id': 'categoryName', 
                'placeholder': 'Enter category name',
                'required': True,
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select', 
                'id': 'parentCategory',
                'required': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        queryset = Category.objects.filter(parent__isnull=True)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(id=self.instance.pk)
        self.fields['parent'].queryset = queryset
        self.fields['parent'].empty_label = '---Select Parent---'

    def clean_name(self):
        name = self.cleaned_data.get('name').capitalize()
        if Category.objects.filter(name__iexact=name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Category name already exists")
        return name


# To select variations related to subcategories

class SubcategoryVariationForm(forms.ModelForm):
    class Meta:
        model = SubcategoryVariation
        fields = ['variation']
        widgets = {
            'variation': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'style': 'height: 100px;',
            })
        }
        
        
# To select attributes related to subcategories

class SubcategoryAttributeForm(forms.ModelForm):
    class Meta:
        model = SubcategoryAttribute
        fields = ['attribute']
        widgets = {
            'attribute': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'style': 'height: 100px;',
            })
        }
        

# Product Form

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'brand', 'description', 'is_active', 'is_featured', 'category']
        widgets = {
            'name': forms.TextInput(attrs={
                'maxlength': 100, 
                'class': 'form-control', 
                'placeholder': 'Enter product name',
                'required': True,
            }),
            'brand': forms.TextInput(attrs={
                'maxlength': 100,
                'class': 'form-control', 
                'placeholder': 'Enter product name',
                'required': True,
            }),
            'category': forms.Select(attrs={ 
                'class': 'form-select',
                'id': 'categoryName',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter product description',
                'required': True,
            }),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['category'].empty_label = '---Select Category---'
        self.fields['category'].queryset = Category.objects.filter(parent__isnull=True)


# Profile Form

class ProfileForm(forms.ModelForm):
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        widget=forms.Select(attrs={'id': 'inputCountry'}),
        required=True
    )

    mobile = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'id':"mobile", 'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'surname', 'email', 'country', 'mobile']
        widgets = {
            'first_name': forms.TextInput(attrs={'id':"first_name", 'class': 'form-control', 'required': True}),
            'surname': forms.TextInput(attrs={'id':"surname", 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'id':"email", 'class': 'form-control', 'autocomplete': 'off', 'required': True})
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("Email is already registered")
        return email
    
    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if not mobile.isdigit():
            raise forms.ValidationError("Mobile number must contain only digits")
        return mobile

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user


# To update the current password

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'id':"current_password", 'class': 'form-control', 'required': True}),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'id':"new_password", 'class': 'form-control', 'required': True}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'id':"confirm_password", 'class': 'form-control', 'required': True}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError("Incorrect current password")
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data
    

# PinCode Form

class PinCodeForm(forms.ModelForm):
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        widget=forms.Select(attrs={'id': 'inputCountry', 'class': 'form-select'}),
        required=True
    )

    class Meta:
        model = PinCode
        fields = [
            'pin_code', 'country', 'city', 'state', 'delivery_days', 'delivery_charge'
        ]
        widgets = {
            'pin_code': forms.TextInput(attrs={'id':"pin_code", 'class': 'form-control', 'placeholder': 'Enter pin code', 'required': True}),
            'city': forms.TextInput(attrs={'id':"city", 'class': 'form-control', 'placeholder': 'Enter city', 'required': True}),
            'state': forms.TextInput(attrs={'id':"state", 'class': 'form-control', 'placeholder': 'Enter state', 'required': True}),
            'delivery_days': forms.TextInput(attrs={'id':"delivery_days", 'class': 'form-control', 'placeholder': 'Enter delivery days', 'required': True}),
            'delivery_charge': forms.TextInput(attrs={'id':"delivery_charge", 'class': 'form-control', 'placeholder': 'Enter delivery charge', 'required': True})
        }

    def clean_pin_code(self):
        pin_code = self.cleaned_data.get('pin_code')

        if not pin_code.isdigit() or len(pin_code)!= 6:
                raise forms.ValidationError("Pin code must be a 6-digit number")
        
        if PinCode.objects.filter(pin_code__iexact=pin_code).exclude(id=self.instance.id).exists():
                raise forms.ValidationError("Pincode already exists")
        
        return pin_code
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user


# Variation name form

class VariationForm(forms.ModelForm):
    class Meta:
        model = VariationName
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter variation name'}),
        }
        
    def clean_name(self):
        name = self.cleaned_data.get('name')

        if VariationName.objects.filter(name__iexact=name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Variation name already exists")
        
        return name
     
        
# Variation value form

class VariationValueForm(forms.ModelForm):
    class Meta:
        model = VariationValue
        fields = ['variation', 'value']
        widgets = {
            'variation': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter variation value'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['variation'].queryset = VariationName.objects.exclude(name__in=['Size', 'Color'])
        self.fields['variation'].empty_label = "---Select Variation---"


# Attribute name form

class AttributeForm(forms.ModelForm):
    class Meta:
        model = ProductAttribute
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter attribute name'}),
        }
        
    def clean_name(self):
        name = self.cleaned_data.get('name')

        if ProductAttribute.objects.filter(name__iexact=name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("Attribute name already exists")

        return name
     
        
# Attribute value form

class AttributeValueForm(forms.ModelForm):
    class Meta:
        model = ProductAttributeValue
        fields = ['product_attribute', 'value']
        widgets = {
            'product_attribute': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter attribute value'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product_attribute'].empty_label = "---Select Attribute---"
        
    def clean_value(self):
        value = self.cleaned_data.get('value').strip()
        product_attribute = self.cleaned_data.get('product_attribute')

        if ProductAttributeValue.objects.filter(product_attribute=product_attribute, value__iexact=value).exists():
            raise forms.ValidationError(f'The value "{value}" already exists for this attribute.')

        return value


# SKU form

class SKUForm(forms.ModelForm):
    class Meta:
        model = SKU
        fields = ['price', 'stock', 'discount_rate']
        widgets = {
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock'}),
            'discount_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter discount rate'}),
        }
        
    def __init__(self, *args, **kwargs):
        super(SKUForm, self).__init__(*args, **kwargs)
        self.fields['price'].required = True
        self.fields['stock'].required = True
        self.fields['discount_rate'].required = True
        

# Coupon form

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active', 'is_first_time_user', 'description', 'products', 'minimum_cart_value']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter coupon code'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter discount value'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_first_time_user': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter a description', 'rows': 3}),
            'products': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'minimum_cart_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter minimum cart value'}),
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(CouponForm, self).__init__(*args, **kwargs)
        discount_type_choices = [('', '---Select Discount type---')] + list(self.fields['discount_type'].choices)
        self.fields['discount_type'].choices = discount_type_choices
        
        if user:
            self.fields['products'].queryset = Product.objects.filter(created_by=user)
        else:
            self.fields.pop('products')
        
        
    def clean_code(self):   
        code = self.cleaned_data.get('code')

        if Coupon.objects.filter(code__iexact=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Coupon with the same coupon code already exists")

        return code
    
    def clean_discount_value(self):
        discount_value = self.cleaned_data.get('discount_value')
        discount_type = self.cleaned_data.get('discount_type')
        
        if discount_value <= 0:
            raise forms.ValidationError("Discount value must be greater than zero")
        
        if discount_type == 'percentage' and discount_value > 100:
            raise forms.ValidationError("Percentage discount cannot exceed 100%")

        return discount_value

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            self.save_m2m()
        return user
    
    