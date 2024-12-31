from django.shortcuts import get_object_or_404
from products.models import Category, WishlistItem
from cart.models import CartItem, Cart
from products.models import SKUImage
from django.db.models import Count


def get_categories(request):
    priority_categories = ['Men', 'Women', 'Shoes', 'Watches', 'Bags']
    categories_with_priority = Category.objects.filter(name__in=priority_categories, parent__isnull=True
                                                       ).filter(product__sku_status=True).annotate(product_count=Count('product')).filter(product_count__gt=0)
    remaining_categories = Category.objects.filter(parent__isnull=True
                                                   ).exclude(name__in=priority_categories).filter(product__sku_status=True).annotate(product_count=Count('product')).filter(product_count__gt=0)

    ordered_categories = sorted(
        categories_with_priority,
        key=lambda cat: priority_categories.index(cat.name)
    )
    
    categories = list(ordered_categories) + list(remaining_categories)
    return {'categories': categories}


def wishlist_count(request):
    wishlist_count = 0
    
    if request.user.is_authenticated:
        wishlist_count = WishlistItem.objects.filter(user=request.user).count()
    else:
        wishlist_count = 0
        
    return {'wishlist_count': wishlist_count}


def cart_items_count(request):
    cart_items_count = 0
    
    if request.user.is_authenticated:
        cart_items_count = CartItem.objects.filter(cart__user=request.user).count()
    else:
        session_cart_id = request.session.get('cart_id')
        if session_cart_id:
            cart_items_count = CartItem.objects.filter(cart_id=session_cart_id).count()
    
    return {'cart_items_count': cart_items_count}


def cart_items_base(request):             
    cart_items_base = []
    products_data = []
    total_cart_price = 0
    
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_cart_id = request.session.get('cart_id')
        if session_cart_id:
            try:
                cart = Cart.objects.filter(id=session_cart_id).first()
            except Cart.DoesNotExist:
                cart = Cart.objects.create()  
                request.session['cart_id'] = cart.id  
        else:
            cart = Cart.objects.create()
            request.session['cart_id'] = cart.id
            
    if cart:  
        cart_items_base = cart.items.prefetch_related('product', 'sku').distinct() if cart.items.exists() else []

        sku_ids = [item.sku_id for item in cart_items_base if item.sku]
        sku_images = {image.sku_id: image for image in SKUImage.objects.filter(sku_id__in=sku_ids)}

        for cart_item in cart_items_base:
            sku = cart_item.sku
            product_image = sku_images.get(sku.id) if sku else None
            item_discounted_price = cart_item.sku.get_discount_price()
            item_quantity = cart_item.quantity
            
            total_cart_price += item_discounted_price * item_quantity
            
            products_data.append({
                'item_name': cart_item.product.name,
                'item_discounted_price': item_discounted_price,
                'item_quantity': item_quantity,
                'item_product_image': product_image
            })
        
    return {'cart_items_base': products_data, 'total_cart_price': total_cart_price}
    