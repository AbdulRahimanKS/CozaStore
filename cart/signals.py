from django.db.models.signals import post_save
from django.dispatch import receiver
from products.models import SKU
from .models import Cart, CartItem, Order
from shop_admin.models import Notification


@receiver(post_save, sender=Order)
def reduce_stock_count(sender, instance, **kwargs):
    if instance.delivery_confirmed:
        cart_items = CartItem.objects.filter(cart__user=instance.user)
        for item in cart_items:
            product = item.product
            sku = item.sku
            quantity = item.quantity
            
            SKU.objects.filter(product=product, id=sku.id).update(stock=sku.stock - quantity)
            
            if product.created_by: 
                Notification.objects.create(
                    admin=product.created_by,
                    message=f'New order placed for {product.name}, Quantity: {quantity}',
                )
        try:   
            cart = Cart.objects.get(user=instance.user)
            cart.delete()
        except Cart.DoesNotExist:
            pass
        
        
