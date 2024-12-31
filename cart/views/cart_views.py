import json
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView
from cart.models import CartItem, Cart, Order, OrderItem, OrderItemTracking, Coupon
from accounts.models import CustomUser
from shop_admin.models import PinCode
from products.models import Product, SKU, SKUImage, CheckOutAddresses, SKUCombination
from products.forms import CheckoutAddressesForm
from shop_admin.mixins import UserRequiredMixin


# To add products in the cart

class CartItemCreateView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            product_id = data.get('productId')
            color = data.get('color')
            variations = data.get('variations')
            
            product = Product.objects.get(id=product_id)
            skus = SKU.objects.filter(product_id=product_id)

            filters = {
                'sku__in': skus
            }

            for variation in variations:
                variation_name = variation.get('name')
                variation_value = variation.get('value')
                filters[f'variation_name__name'] = variation_name
                filters[f'variation_value__value'] = variation_value

            sku_combinations = SKUCombination.objects.filter(**filters).distinct()

            if color:
                color_combinations = SKUCombination.objects.filter(
                    sku__in=skus,
                    variation_name__name='Color',
                    variation_value__value=color
                )
                color_sku_ids = set(color_combinations.values_list('sku', flat=True))
            
                sku_combinations = sku_combinations.filter(sku__in=color_sku_ids)

            sku = sku_combinations.first().sku if sku_combinations.exists() else None

            if request.user.is_authenticated:
                cart, created = Cart.objects.get_or_create(user=request.user)
            else:
                session_cart_id = request.session.get('cart_id')
                if not session_cart_id:
                    if not request.session.session_key:
                        request.session.create()
                    session_cart_id = request.session.session_key
                    cart = Cart.objects.create(is_session_cart=True, session_id=session_cart_id)
                    request.session['cart_id'] = cart.id
                    request.session.set_expiry(60 * 60 * 24 * 2)
                else:
                    cart = Cart.objects.get(id=session_cart_id)    

            existing_cart_item = CartItem.objects.filter(cart=cart, product=product, sku=sku).first()
            if existing_cart_item:
                existing_cart_item.quantity += 1
                if existing_cart_item.quantity > sku.stock:
                    return JsonResponse({'success': False, 'error': 'Not enough stock available'})
                
                existing_cart_item.save()
                return JsonResponse({'success': True, 'message': 'Quantity updated successfully'})
            else:
                cart_item = CartItem.objects.create(cart=cart, product=product, sku=sku, quantity=1)
                cart_item.save()
                return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
        
# To view cartItems
        
class ShoppingCartView(ListView):
    model = CartItem
    template_name = 'shopping_cart.html'
    context_object_name = 'cart_items'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cart_items = []
        cart = None
        if self.request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=self.request.user)
            cart_items = cart.items.prefetch_related('product', 'sku').distinct()
        else:
            session_cart_id = self.request.session.get('cart_id')
            if session_cart_id:
                try:
                    cart = Cart.objects.get(id=session_cart_id)
                    cart_items = cart.items.prefetch_related('product', 'sku').distinct()
                except Cart.DoesNotExist:
                    cart = Cart.objects.create()  
                    self.request.session['cart_id'] = cart.id  
            else:
                cart = Cart.objects.create()
                self.request.session['cart_id'] = cart.id
                   
        products_data, total_original_price, total_discount, total_discounted_price, total_cart_items_count, available_cart_items_count, delivery_charge_display, delivery_charge_amount, show_strikethrough, total_discount_available = self.product_data(cart_items)
        cart.discounted_price = total_discounted_price if total_discounted_price is not None else 0
        cart.coupon_discount = 0
        cart.save()
        
        if self.request.user.is_authenticated:
            has_confirmed_orders = Order.objects.filter(user=self.request.user, delivery_confirmed=True).exists()
            if not has_confirmed_orders:
                first_time_coupon = Coupon.objects.filter(is_first_time_user=True, is_active=True, minimum_cart_value__lte=total_discounted_price, products=None).first()
                if first_time_coupon:
                    first_time_coupon.check_and_update_validity()
                    first_time_coupon.save()
                first_time_coupon = Coupon.objects.filter(is_first_time_user=True, is_active=True, minimum_cart_value__lte=total_discounted_price, products=None).first()
                cart.coupons.add(first_time_coupon)
                cart.save()
        
        coupon_details_list = []  
        for coupon in cart.coupons.all():
            total_discounted_price, coupon_discount, coupon_details = self.apply_coupon(coupon, total_discounted_price)
            cart.discounted_price -= coupon_discount
            cart.coupon_discount += coupon_discount
            if coupon_details:
                coupon_details_list.append(coupon_details)
        cart.save()
        
        discounted_price_without_coupon = total_original_price - total_discount
          
        context['cart_items'] = products_data
        context['total_original_price'] = f"{total_original_price:,}"
        context['total_discount'] = f"{total_discount:,}"
        context['total_discounted_price'] = f"{total_discounted_price:,}"
        context['total_cart_items_count'] = total_cart_items_count 
        context['available_cart_items_count'] = available_cart_items_count
        context['delivery_charge_display'] = delivery_charge_display
        context['delivery_charge_amount'] = delivery_charge_amount
        context['show_strikethrough'] = show_strikethrough
        context['total_discount_available'] = total_discount_available
        context['coupon_details'] = coupon_details_list
        context['coupon_discount'] = cart.coupon_discount
        context['discounted_price_without_coupon'] = discounted_price_without_coupon
        
        if self.request.user.is_authenticated:
            addresses = CheckOutAddresses.objects.filter(user=self.request.user)
            default_address = addresses.filter(default=True).first()
            context['addresses'] = addresses
            context['default_address'] = default_address
            
        context['CheckoutAddressesForm'] = CheckoutAddressesForm()

        return context
    
    def product_data(self, cart_items):
        products_data = []
        total_original_price = 0    
        total_discount = 0
        total_discounted_price = 0
        total_cart_items_count = len(cart_items)
        available_cart_items_count = 0
        delivery_charge_display = 0
        delivery_charge_amount = 0
        total_discount_available = False
        show_strikethrough = False
        
        user = self.request.user
        default_address = None
        pin_code = None
        if user.is_authenticated:
            default_address = CheckOutAddresses.objects.filter(user=user, default=True).first()
            if default_address:
                pin_code = default_address.pin_code
                
        pin_code_object = None
        delivery_available = False
        
        if pin_code:
            pin_code_object = PinCode.objects.filter(pin_code=pin_code).first()
            if pin_code_object:
                delivery_available = True
        
        for item in cart_items:
            can_submit = True
            issues = []
        
            product = item.product
            product_url = item.product.get_url()
            sku = item.sku
            product_image = SKUImage.objects.filter(sku=sku).first() if sku else None
            discounted_price = item.sku.get_discount_price()
            original_price = item.sku.price
            discount_percentage = item.sku.discount_rate
            
            discount_amount = original_price - discounted_price if discounted_price < original_price else 0
            
            quantity = item.quantity
            initial_total_price = discounted_price * quantity if discounted_price else original_price * quantity
            initial_total_price = f"{initial_total_price:,}"
            
            stock_available = item.sku.stock
            
            variations = []
            if sku and sku.combinations.exists():
                for combination in sku.combinations.all():
                    if combination.variation_name.name.lower() != 'color':
                        variations.append({
                            'name': combination.variation_name.name,
                            'value': combination.variation_value.value,
                        })
            
            product_admin_delivery_available = False
            if delivery_available:
                product_admin_delivery_available = PinCode.objects.filter(created_by=product.created_by, pin_code=pin_code).exists()
            else:
                delivery_available = False
                
            stock_limit_reached = quantity > item.sku.stock
            delivery_available_final = delivery_available and product_admin_delivery_available

            if quantity > item.sku.stock:
                can_submit = False
                issues.append('Stock quantity exceeded than the stock')
                
            if not delivery_available_final:
                can_submit = False
                issues.append('Delivery not available for this address')
                
            if delivery_available_final:
                total_original_price += original_price * item.quantity
                total_discount += discount_amount * item.quantity
                total_discounted_price += discounted_price * item.quantity
                available_cart_items_count += 1
                
            original_price = f"{original_price:,}"
            discounted_price = f"{discounted_price:,}"
            
            products_data.append({
                'cart_item': item,
                'product_id': product.id,
                'product_url': product_url,
                'product_name': product.name,
                'product_price': original_price,
                'product_discounted_price': discounted_price,
                'product_image': product_image,
                'product_discount_percentage': discount_percentage,
                'product_sku': sku,
                'initial_total_price': initial_total_price,
                'variations': variations,
                'delivery_available': delivery_available_final,
                'stock_limit_reached': stock_limit_reached,
                'stock_available': stock_available,
                'can_submit': can_submit,
                'issues': ','.join(issues)
            })
            
        if pin_code_object and total_discounted_price > 499:
            delivery_charge_display = pin_code_object.delivery_charge
            show_strikethrough = True
        elif pin_code_object: 
            delivery_charge_display = pin_code_object.delivery_charge
            total_discounted_price += delivery_charge_display
            show_strikethrough = False
            delivery_charge_amount = delivery_charge_display
        
        if total_discount > 0:
            total_discount_available = True
        
        return products_data, total_original_price, total_discount, total_discounted_price, total_cart_items_count, available_cart_items_count, delivery_charge_display, delivery_charge_amount, show_strikethrough, total_discount_available
    
    def apply_coupon(self, coupon, total_discounted_price):
        coupon_discount = 0
        coupon_details = None
        
        if total_discounted_price > coupon.minimum_cart_value:
            if coupon.discount_type == 'fixed':
                discount_amount = int(coupon.discount_value)
            elif coupon.discount_type == 'percentage':
                discount_amount = int((coupon.discount_value / 100) * total_discounted_price)
            else:
                discount_amount = 0
            
            total_discounted_price = max(total_discounted_price - discount_amount, 0)
            coupon_discount = discount_amount
            
            coupon_details = {
                'code': coupon.code,
                'description': coupon.description if coupon.description else (
                                f"{coupon.discount_value}% off" if coupon.discount_type == 'percentage' else f"₹{coupon.discount_value} off"),
                'discount_amount': f"{discount_amount:,}"
            }
        
        return total_discounted_price, coupon_discount, coupon_details
    
    def post(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id=request.user.id)
        form = CheckoutAddressesForm(request.POST)

        if 'add_address' in request.POST:
            if form.is_valid():
                address = form.save(commit=False)
                address.user = user
                if not CheckOutAddresses.objects.filter(user=user).exists():
                    address.default = True
                address.save()
                messages.success(request, 'Address added successfully')
                return redirect('cart_view')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, error)
            return redirect('cart_view')
    
    
# To apply coupons

class ApplyCouponView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').strip().upper()
        response_data = {
            "success": False,
            "message": ""
        }
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            coupon.check_and_update_validity()
            coupon.save()
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            cart_products = []
            cart = None
            if self.request.user.is_authenticated:
                cart, created = Cart.objects.get_or_create(user=self.request.user)
                cart_products = cart.items.prefetch_related('product', 'sku').distinct()
            else:
                session_cart_id = self.request.session.get('cart_id')
                if session_cart_id:
                    try:
                        cart = Cart.objects.get(id=session_cart_id)
                        cart_products = cart.items.prefetch_related('product', 'sku').distinct()
                    except Cart.DoesNotExist:
                        cart = Cart.objects.create()  
                        self.request.session['cart_id'] = cart.id  
                else:
                    cart = Cart.objects.create()
                    self.request.session['cart_id'] = cart.id
                                
            cart_product_ids = [item.product.id for item in cart_products]
            
            if coupon in cart.coupons.all():
                response_data["message"] = 'This coupon has already been applied to your cart'
            else:
                if coupon.products.exists():
                    if coupon.products.filter(id__in=cart_product_ids).exists():
                        cart.coupons.add(coupon)
                        response_data["success"] = True
                    else:
                        response_data["message"] = 'This coupon does not apply to the products in your cart'
                else:
                    if self.is_first_time_user(request.user):
                        cart.coupons.add(coupon)
                        response_data["success"] = True
                    else:
                        response_data["message"] = 'This coupon is only valid for first-time users'
                cart.save()
        except Coupon.DoesNotExist:
            response_data["message"] = 'Invalid coupon code. Please try again'
        
        return JsonResponse(response_data)

    def is_first_time_user(self, user):
        return not Order.objects.filter(user=user, delivery_confirmed=True).exists()

    def calculate_discount(self, coupon, discounted_price):
        if coupon.discount_type == 'percentage':
            discount_amount = (coupon.discount_value / 100) * discounted_price
        else:
            discount_amount = coupon.discount_value

        discount_amount = min(discount_amount, discounted_price)

        return discount_amount
    
    
# To remove coupons

class RemoveCouponView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)   
        coupon_code = data.get('coupon_code', '').strip().upper()
        print(coupon_code)
        response_data = {
            "success": True,
            "message": ""
        }
        
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        
        if self.request.user.is_authenticated:
            cart = Cart.objects.get(user=self.request.user, coupons__code=coupon_code)
        else:
            session_cart_id = self.request.session.get('cart_id')
            if session_cart_id:
                    cart = Cart.objects.get(id=session_cart_id, coupons__code=coupon_code)
        
        cart.coupons.remove(coupon)
        
        response_data["success"] = True
        response_data["message"] = 'Coupon removed successfully!'
        
        return JsonResponse(response_data)


# To check for available product stock

class CheckStockView(View):
    def get(self, request, product_id, sku_id):
        quantity = int(request.GET.get('quantity', 1))
        try:
            sku = SKU.objects.get(id=sku_id, product_id=product_id)
            stock_available = sku.stock
            is_available = quantity <= stock_available
            
            if is_available:
                if request.user.is_authenticated:
                    cart, created = Cart.objects.get_or_create(user=request.user)
                    
                    cart_item, created = CartItem.objects.get_or_create(cart=cart, sku=sku)
                    cart_item.quantity = quantity
                    cart_item.save()
                    
                else:
                    session_cart_id = request.session.get('cart_id')
                    if not session_cart_id:
                        cart = Cart.objects.create()
                        request.session['cart_id'] = cart.id
                    else:
                        cart = Cart.objects.get(id=session_cart_id)

                    cart_item, created = CartItem.objects.get_or_create(cart=cart, sku=sku)
                    cart_item.quantity = quantity
                    cart_item.save()

            return JsonResponse({
                'stock_available': is_available,
                'available_quantity': stock_available,
            })
        except SKU.DoesNotExist:
            return JsonResponse({'error': 'SKU not found'}, status=404)

        
# To remove cart items

class RemoveCartItemView(View):
    def delete(self, request, product_id, sku_id):
        if request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=request.user)
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id, sku_id=sku_id)
                self.remove_related_coupons(cart, product_id)
                cart_item.delete()
                
                return JsonResponse({'message': 'Item removed successfully'}, status=200)
            except CartItem.DoesNotExist:
                return JsonResponse({'message': 'Item not found'}, status=404)
        else:
            session_cart_id = request.session.get('cart_id')
            if session_cart_id:
                try:
                    session_cart = Cart.objects.get(id=session_cart_id, is_session_cart=True)
                    cart_item = CartItem.objects.get(cart=session_cart, product_id=product_id, sku_id=sku_id)
                    self.remove_related_coupons(session_cart, product_id)
                    cart_item.delete()
                    return JsonResponse({'message': 'Item removed successfully'}, status=200)
                except CartItem.DoesNotExist:
                    return JsonResponse({'message': 'Item not found in session cart'}, status=404)
            else:
                return JsonResponse({'message': 'No items in session cart'}, status=404)
            
    def remove_related_coupons(self, cart, product_id):
        try:
            related_coupons = cart.coupons.filter(products__id=product_id)  
            for coupon in related_coupons:
                cart.coupons.remove(coupon)
        except Exception as e:
            print(f"Error while deleting related coupons: {e}")
        
        
# To set default address form cartView

class SetDefaultAddressView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        address_id = data.get('address_id')
        user = request.user
        
        address = get_object_or_404(CheckOutAddresses, id=address_id, user=user)
        address.default = True
        address.save()
        return JsonResponse({'success': True})
    

# To set order details

class SetOrderDetailsView(UserRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        address_id = request.POST.get('selected_address_id')
        
        product_ids = request.POST.getlist('cart_items')
        coupon_codes = request.POST.getlist('coupon_codes')
        total_amount = request.POST.get('total_amount').replace(',', '')
        coupon_discount = request.POST.get('coupon_discount').replace(',', '')
        total_discount = request.POST.get('total_discount').replace(',', '')
        discounted_amount = request.POST.get('discounted_amount').replace(',', '')
        delivery_charge_amount = request.POST.get('delivery_charge_amount').replace(',', '')
        discounted_price_without_coupon = request.POST.get('discounted_price_without_coupon').replace(',', '')
        
        if address_id and product_ids and total_amount and total_discount and discounted_amount and coupon_discount:
            address = get_object_or_404(CheckOutAddresses,id=address_id, user=user)
            
            order = Order(user=user, address=address, total_amount=total_amount, 
                          total_discount=total_discount, discounted_amount=discounted_amount, coupon_amount=coupon_discount,
                          delivery_charge=delivery_charge_amount, discounted_amount_without_coupon=discounted_price_without_coupon)
            
            order.address_name = address.name
            order.address_address = address.address
            order.address_locality = address.locality
            order.address_city = address.city
            order.address_state = address.state
            order.address_pin_code = address.pin_code
            order.address_mobile = address.mobile
            order.save() 
            
            if coupon_codes:
                for coupon_code in coupon_codes:
                    coupon = get_object_or_404(Coupon, code=coupon_code, is_active=True)
                    order.coupons.add(coupon)
                order.save()     
           
            cart_items = []
            cart = get_object_or_404(Cart, user=user)
            for index, product_id in enumerate(product_ids):
                sku_id = request.POST.get(f'sku_{index + 1}')
                
                if sku_id:
                    cart_item = get_object_or_404(CartItem, product_id=product_id, sku_id=sku_id, cart=cart)
                    cart_items.append(cart_item)
            
            for cart_item in cart_items:
                order_item = OrderItem(order=order, product=cart_item.product, sku=cart_item.sku, quantity=cart_item.quantity)  
                order_item.product_name = cart_item.product.name
                order_item.product_price = cart_item.sku.price
                order_item.product_discount_percentage = cart_item.sku.discount_rate
                order_item.product_discounted_price = cart_item.sku.get_discount_price()
                order_item.save()
                
                OrderItemTracking.objects.create(order_item=order_item, status='processing')
        
        return redirect('payment_method_selection', order_id=order.order_id)
    
    
# To list ordered items
    
class OrdersListView(UserRequiredMixin, TemplateView):
    template_name = "orders.html"
    
    def get(self, request, *args, **kwargs):
        user = self.request.user
        orders = Order.objects.filter(user=user, delivery_confirmed='True').order_by('-created_at').prefetch_related('items')
        return render(request, self.template_name, {'orders': orders})
            
    
# To track each products ordered
    
class TrackOrderView(UserRequiredMixin, TemplateView):
    template_name = "order_item.html"
    
    def get(self, request, tracking_id, *args, **kwargs):
        order_item = get_object_or_404(OrderItemTracking, tracking_id=tracking_id)
        status = order_item.status
        
        is_cancelled = status == 'cancelled'
        is_returned = status == 'returned'
        
        context = {
            'order_item': order_item,
            'is_confirmed': status in ['processing', 'shipped', 'out_for_delivery', 'delivered'],
            'is_shipped': status in ['shipped', 'out_for_delivery', 'delivered'],
            'is_out_for_delivery': status in ['out_for_delivery', 'delivered'],
            'is_delivered': status == 'delivered',
            'is_cancelled': is_cancelled,
            'is_returned': is_returned
        }
        
        return render(request, self.template_name, context)
    
    
