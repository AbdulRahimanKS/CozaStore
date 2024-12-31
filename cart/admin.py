from django.contrib import admin
from .models import Cart, CartItem, Coupon, Order, OrderItem, OrderItemTracking, OrderItemAction, OrderItemRefund
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

class CartAdmin(admin.ModelAdmin):
    list_display = ('get_cart_identifier', 'created_at')
    inlines = [CartItemInline]
    
    def get_cart_identifier(self, obj):
        if obj.user:
            return obj.user
        return obj.session_id
    
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active', 'is_first_time_user')
    search_fields = ('code',)

admin.site.register(Cart, CartAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register([CartItem, Order, OrderItem, OrderItemTracking, OrderItemAction, OrderItemRefund])

