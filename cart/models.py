from datetime import datetime
from django.utils import timezone
import uuid
from django.db import models
from products.models import SKU, CheckOutAddresses


ACCOUNTS_CUSTOMUSER_MODEL = 'accounts.CustomUser'
PRODUCTS_PRODUCT_MODEL = 'products.Product'

       
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, blank=False)
    discount_type = models.CharField(max_length=20, choices=(('fixed', 'Fixed'), ('percentage', 'Percentage')), blank=False)
    discount_value = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(blank=True, null=True)
    valid_to = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_first_time_user = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    products = models.ManyToManyField(PRODUCTS_PRODUCT_MODEL, blank=True, related_name='cart_items')
    minimum_cart_value = models.PositiveIntegerField(default=0) 
    created_by = models.ForeignKey(ACCOUNTS_CUSTOMUSER_MODEL, on_delete=models.CASCADE)

    def check_and_update_validity(self):
        current_time = timezone.now()

        if self.valid_to is not None:
            if current_time > self.valid_to:
                self.is_active = False
                self.save(update_fields=['is_active'])
        
        return self.is_active
            
    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)   

    def __str__(self):
        return f'{self.code} - {self.discount_type}: {self.discount_value}'
        
        
class Cart(models.Model):
    user = models.ForeignKey(ACCOUNTS_CUSTOMUSER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_session_cart = models.BooleanField(default=False)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    discounted_price = models.PositiveIntegerField(default=0)
    coupon_discount = models.PositiveIntegerField(default=0)
    coupons = models.ManyToManyField(Coupon, blank=True, related_name='carts') 
    
    def __str__(self):
        if self.session_id:
            return str(self.session_id)
        else:
            return str(self.user)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(PRODUCTS_PRODUCT_MODEL, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    sku = models.ForeignKey(SKU, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        if self.cart.user:
            return f'{self.product.name} - {self.cart.user}'
        else:
            return f'{self.product.name} - {self.cart.session_id}'
        
        
class Order(models.Model):

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed')
    )
    
    user = models.ForeignKey(ACCOUNTS_CUSTOMUSER_MODEL, on_delete=models.SET_NULL, null=True) 
    order_id = models.CharField(max_length=50, unique=True, editable=False)
    address = models.ForeignKey(CheckOutAddresses, on_delete=models.SET_NULL, null=True)
    address_name = models.CharField(max_length=200)
    address_address = models.CharField(max_length=200)
    address_locality = models.CharField(max_length=100)
    address_city = models.CharField(max_length=100)
    address_state = models.CharField(max_length=100)
    address_pin_code = models.CharField(max_length=6)
    address_mobile = models.CharField(max_length=10)
    coupons = models.ManyToManyField(Coupon, blank=True)
    coupon_amount = models.PositiveIntegerField(default=0)
    total_amount =  models.PositiveIntegerField(default=0)
    total_discount = models.PositiveIntegerField(default=0)
    discounted_amount = models.PositiveIntegerField(default=0)
    delivery_charge = models.CharField(max_length=20, blank=True, null=True)
    discounted_amount_without_coupon = models.CharField(max_length=20, blank=True, null=True)
    payment_type = models.CharField(max_length=20, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_datetime = models.DateTimeField(null=True, blank=True)
    invoice_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    delivery_confirmed = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    order_time = models.DateTimeField(null=True, blank=True)    
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f'ORD-{uuid.uuid4().hex[:8].upper()}'  
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Order {self.order_id} for {self.user.email}'
    
    def generate_invoice_id(self):
        self.invoice_id = uuid.uuid4().hex[:8].upper()
        self.save(update_fields=['invoice_id'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE) 
    product = models.ForeignKey(PRODUCTS_PRODUCT_MODEL, on_delete=models.SET_NULL, null=True)  
    sku = models.ForeignKey(SKU, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    product_name = models.CharField(max_length=200)
    product_price = models.PositiveIntegerField(default=0)
    product_discount_percentage = models.PositiveIntegerField(default=0)
    product_discounted_price = models.PositiveIntegerField(default=0)
    delivery_days = models.PositiveIntegerField(default=0)
    delivery_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    
    def get_cost(self):
        return self.product_discounted_price * self.quantity
    
    def get_discount(self):        
        return (self.product_price * self.quantity) - self.get_cost()

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'
    
    
class OrderItemTracking(models.Model):
    STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    )
    
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='tracking_info')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    tracking_id = models.CharField(max_length=50, unique=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_date = models.DateTimeField(null=True, blank=True)
    is_delivered = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = f'TRK-{self.order_item.order.order_id}-{uuid.uuid4().hex[:6].upper()}'
            
        if self.status == 'delivered' and self.delivered_date is None:
            self.delivered_date = timezone.now()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Tracking {self.tracking_id} - Status: {self.status}'
    
    
class OrderItemAction(models.Model):
    ACTION_TYPE_CHOICES = (
        ('cancellation', 'Cancellation'),
        ('return', 'Return'),
    )

    order_item_tracking = models.OneToOneField(OrderItemTracking, on_delete=models.CASCADE, related_name='action_info')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES)
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('rejected', 'Rejected')])

    def __str__(self):
        return f'{self.order_item_tracking.order_item.order.user.email} - {self.order_item_tracking.order_item.order.order_id} - Action: {self.action_type}'


class OrderItemRefund(models.Model):
    order_item_tracking = models.ForeignKey(OrderItemTracking, on_delete=models.CASCADE, related_name='refunds')
    refund_id = models.CharField(max_length=50, unique=True) 
    refund_key = models.CharField(max_length=50, unique=True) 
    refundInvoiceId = models.CharField(max_length=50, unique=True) 
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    refunded_at = models.DateTimeField(auto_now_add=True) 
    status = models.CharField(max_length=20, choices=[('completed', 'Completed')])

    def __str__(self):
        return f'Refund {self.refund_id} for {self.order_item_tracking.order_item.order.order_id} - Amount: {self.amount}'

