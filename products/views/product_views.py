import json
from django.http import JsonResponse
from django.views.generic import TemplateView, ListView, DetailView
from django.views import View
from products.models import Product, SKU, SKUImage, Category, Rating, WishlistItem, SKUCombination
from shop_admin.models import PinCode
from cart.models import Coupon, Order
from products.forms import RatingForm
from products.utils import get_products, calculate_product_ratings, calculate_discounted_price, calculate_discount_price
from django.http import JsonResponse
from django.db.models import Q, Max, Avg
from django.views.decorators.http import require_GET
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from cart.models import OrderItem


# To display index page

class IndexView(TemplateView):

    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.filter(sku_status=True, is_active=True).order_by('?')
        if self.request.user.is_authenticated:
            wishlist_items = WishlistItem.objects.filter(user=self.request.user).values_list('product_id', flat=True)
        else:
            wishlist_items = []
            
        men = get_object_or_404(Category, slug='men')
        women = get_object_or_404(Category, slug='women')
        context['men'] = men
        context['women'] = women
             
        get_products(products)
        context['products'] = products
        context['wishlist_items'] = wishlist_items
        
        context['is_logged_in'] = self.request.user.is_authenticated
        
        return context
    
    
# To get products based on category selected

@require_GET
def products_by_category(request, category_name):
    wishlist_items = []
    if request.user.is_authenticated:
        wishlist_items = WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True)
        
    if category_name == 'all':
        products = Product.objects.filter(sku_status=True, is_active=True).order_by('?')[:8]
    else:
        category_name = category_name.replace('.', '')
        products = Product.objects.filter(
            category__name__iexact=category_name, 
            sku_status=True, 
            is_active=True
        ).order_by('?')[:8]

    product_list = []
    for product in products:
        sku = SKU.objects.filter(product=product).first()
        image = SKUImage.objects.filter(sku=sku).first() if sku else None

        discounted_price = sku.get_discount_price()
        original_price = sku.price
        discount_percentage = sku.discount_rate
        stock = sku.stock
        discounted_price = f"{discounted_price:,}"
                
        ratings_data = calculate_product_ratings(product)

        product_list.append({
            'id': product.id,
            'name': product.name,
            'discounted_price': discounted_price,
            'sku_price': original_price,
            'sku_discount_rate': discount_percentage if discount_percentage else 0,
            'stock': stock,
            'brand': product.brand,
            'image': image.image.url if image else None,
            'get_url': product.get_url(),
            'average_rating': ratings_data['average_rating'],
            'total_ratings': ratings_data['total_ratings'],
            'in_wishlist': product.id in wishlist_items
        })

    return JsonResponse(product_list, safe=False)


# To filter products based on url parameters

class BaseProductListView(ListView):
    model = Product
    context_object_name = 'products'
    paginate_by = 12

    def get_template_names(self):
        page_type = self.kwargs.get('page_type', 'shop')
        
        template_map = {
            'shop': 'shop.html',
            'category': 'parentcategory_products.html',
            'subcategory': 'subcategory_products.html',
            'featured': 'featured_products.html',
            'search': 'search_products.html'    
        }
        return [template_map.get(page_type, 'shop.html')]

    def get_queryset(self):
        queryset = Product.objects.filter(sku_status=True, is_active=True)
        queryset = self.apply_filters(queryset)

        if self.kwargs.get('page_type') == 'featured':
            queryset = queryset.filter(is_featured=True)

        queryset = queryset.annotate(max_sku_id=Max('skus__id'))
        
        products = list(queryset)
        for product in products:
            product.original_price, product.discounted_price = calculate_discounted_price(product)
            product.average_rating = product.ratings.aggregate(Avg('rating'))['rating__avg'] or 0

        # Sorting
        sort = self.request.GET.get('sort')
        if sort == 'newness':
            products.sort(key=lambda x: x.created_at, reverse=True)
        elif sort == 'rating':
            products.sort(key=lambda x: x.average_rating or 0, reverse=True)
        elif sort == 'price_low_high':
            products.sort(key=lambda x: int(x.discounted_price.replace(',', '')) if x.discounted_price else float('inf'))
        elif sort == 'price_high_low':
            products.sort(key=lambda x: int(x.discounted_price.replace(',', '')) if x.discounted_price else 0, reverse=True)

        return get_products(products)
    
    def apply_filters(self, queryset):
        search_query = self.request.GET.get('search', '').strip().lower()
        category_slug = self.kwargs.get('category_slug')
        subcategory_slug = self.kwargs.get('subcategory_slug')

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(brand__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(subcategory__name__icontains=search_query)
            )   

        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)

        if subcategory_slug:
            subcategory = get_object_or_404(Category, slug=subcategory_slug)
            queryset = queryset.filter(subcategory=subcategory)

        # Filter based on discount
        discount_filter = self.request.GET.get('discount')
        if discount_filter and discount_filter != 'all':
            queryset = queryset.filter(skus__discount_rate__gte=int(discount_filter))

        # Filter based on rating
        rating_filter = self.request.GET.get('rating')
        if rating_filter and rating_filter != 'all':
            if rating_filter.isdigit():
                rating_threshold = int(rating_filter)
                products = list(queryset)
                for product in products:
                    ratings_info = calculate_product_ratings(product)
                    product.average_rating = ratings_info['average_rating']
                products = [product for product in products if product.average_rating >= rating_threshold]
                queryset = Product.objects.filter(id__in=[product.id for product in products])
                
        
        # Filter based on price
        products = list(queryset)
        products = calculate_discount_price(products)

        price_filter = self.request.GET.get('price')
        if price_filter and price_filter != 'all':
            filtered_products = []
            for product in products:
                if product.discounted_price:
                    discounted_price = int(product.discounted_price.replace(',', ''))
                    if price_filter == '0-500' and 0 <= discounted_price <= 500:
                        filtered_products.append(product)
                    elif price_filter == '500-1000' and 500 < discounted_price <= 1000:
                        filtered_products.append(product)
                    elif price_filter == '1000-5000' and 1000 < discounted_price <= 5000:
                        filtered_products.append(product)
                    elif price_filter == '5000-10000' and 5000 < discounted_price <= 10000:
                        filtered_products.append(product)
                    elif price_filter == '10000+' and discounted_price > 10000:
                        filtered_products.append(product)

            queryset = Product.objects.filter(id__in=[product.id for product in filtered_products])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            wishlist_items = WishlistItem.objects.filter(user=self.request.user).values_list('product_id', flat=True)
        else:
            wishlist_items = []
            
        context['wishlist_items'] = wishlist_items
        
        return context


# To display the searched products

class ProductSearchView(BaseProductListView):
    def get(self, request, *args, **kwargs):
        self.kwargs['page_type'] = 'search'
        return super().get(request, *args, **kwargs)
    
    
# To display the parent category searched products

class ParentCategoryProductsView(BaseProductListView):
    def get(self, request, *args, **kwargs):
        self.kwargs['page_type'] = 'category'
        return super().get(request, *args, **kwargs)
    
    def get_category(self):
        category_slug = self.kwargs.get('category_slug') 
        if category_slug:
            return get_object_or_404(Category, slug=category_slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_category'] = self.get_category()
        return context
    
    
# To display the subcategory searched products

class SubcategoryProductsView(BaseProductListView):
    def get(self, request, *args, **kwargs):
        self.kwargs['page_type'] = 'subcategory'
        return super().get(request, *args, **kwargs)
    
    def get_subcategory(self):
        subcategory_slug = self.kwargs.get('subcategory_slug')
        if subcategory_slug:
            return get_object_or_404(Category, slug=subcategory_slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subcategory = self.get_subcategory()
        if subcategory:
            context['subcategory'] = subcategory
            context['category'] = subcategory.parent
        
        return context


# To show products in shop

class ShopView(BaseProductListView):
    def get(self, request, *args, **kwargs):
        self.kwargs['page_type'] = 'shop'
        return super().get(request, *args, **kwargs)


# To show featured products

class FeaturedView(BaseProductListView):
    def get(self, request, *args, **kwargs):
        self.kwargs['page_type'] = 'featured'
        return super().get(request, *args, **kwargs)

    
# To show product detail

class ProductDetailView(DetailView):
    model = Product
    template_name = 'product_detail.html'
    
    def get_object(self):
        subcategory_slug = self.kwargs['subcategory_slug']
        product_slug = self.kwargs['product_slug']
        return Product.objects.get(subcategory__slug=subcategory_slug, slug=product_slug)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        color_variations, selected_color, filtered_variations, selected_stock, selected_variation_data = self.get_variations_by_color(product)
        context['color_variations'] = color_variations
        context['selected_color'] = selected_color
        context['filtered_variations'] = filtered_variations
        context['selected_stock'] = selected_stock
        context['selected_variation_data'] = selected_variation_data
        
        product_attributes = self.get_product_attributes(product)
        context['product_attributes'] = product_attributes
        
        if self.request.user.is_authenticated:
            try:
                user_rating = Rating.objects.get(product=product, user=self.request.user)
                context['rating_form'] = RatingForm(instance=user_rating)
            except Rating.DoesNotExist:
                context['rating_form'] = RatingForm()
            
        context['limited_reviews'] = product.ratings.exclude(review__isnull=True).exclude(review__exact='')[:4]
        context['more_reviews'] = product.ratings.exclude(review__isnull=True).exclude(review__exact='').count() > 4
        
        ratings_data = calculate_product_ratings(product)
        context['average_rating'] =  ratings_data['average_rating']
        context['total_ratings'] = ratings_data['total_ratings']
        context['total_reviews'] = ratings_data['total_reviews']
        
        if self.request.user.is_authenticated:
            is_purchased_user = OrderItem.objects.filter(order__user=self.request.user, product=product).exists()
        else:
            is_purchased_user = False
            
        context['is_purchased_user'] = is_purchased_user
        
        product = self.product_data(product)
        context['product'] = product
        
        related_products = self.related_products_data(product)
        context['products_in_subcategories'] = related_products[:10]
        
        if self.request.user.is_authenticated:
            wishlist_items = WishlistItem.objects.filter(user=self.request.user).values_list('product_id', flat=True)
            wishlist_count = WishlistItem.objects.filter(user=self.request.user).count()
        else:
            wishlist_items = []
            wishlist_count = 0
        
        context['wishlist_items'] = wishlist_items  
        context['wishlist_count'] = wishlist_count
        
        first_time_user_coupons = Coupon.objects.none()
        
        if self.request.user.is_authenticated:
            has_confirmed_orders = Order.objects.filter(user=self.request.user, delivery_confirmed=True).exists()
            if not has_confirmed_orders:
                first_time_user_coupons = Coupon.objects.filter(is_first_time_user=True, is_active=True, products=None)
                for first_time_coupon in first_time_user_coupons:
                    first_time_coupon.check_and_update_validity()
                    first_time_coupon.save()
                first_time_user_coupons = Coupon.objects.filter(is_first_time_user=True, is_active=True, products=None)
            else:
                first_time_user_coupons = Coupon.objects.none()

        product_coupons = Coupon.objects.filter(products=product, is_active=True, created_by=product.created_by)
        for product_coupon in product_coupons:
            product_coupon.check_and_update_validity()
            product_coupon.save()
        product_coupons = Coupon.objects.filter(products=product, is_active=True, created_by=product.created_by)
            
        coupons = first_time_user_coupons | product_coupons
        coupons = coupons.distinct()
            
        context['coupons'] = coupons
        context['category'] = product.category
        context['subcategory'] = product.subcategory
        
        return context
    
    def product_data(self, product):
        if product:
            product.sku = SKU.objects.filter(product=product).first()
            product.images = product.sku.images.all() if product.sku else []
            product.discounted_price = product.sku.get_discount_price()
            product.discounted_price = f"{product.discounted_price:,}"
        
        return product
    
    def get_variations_by_color(self, product):
        skus = SKU.objects.filter(product=product).prefetch_related('combinations')

        color_variations = []
        variation_data = {}
        has_color_variation = False 
        
        seen_colors = set()
        selected_sku = None
        selected_stock = 0

        for sku in skus:
            for combination in sku.combinations.all():
                variation_name = combination.variation_name.name
                variation_value = combination.variation_value.value

                if variation_name == 'Color':
                    has_color_variation = True
                    if variation_value not in seen_colors:
                        seen_colors.add(variation_value)
                        color_variations.append(variation_value) 
                
                if variation_name not in variation_data:
                    variation_data[variation_name] = {}

                if variation_value not in variation_data[variation_name]:
                    variation_data[variation_name][variation_value] = {
                        'stock': sku.stock
                    }
                    
        if has_color_variation:
            selected_color = self.request.GET.get('color', color_variations[0] if color_variations else None)

            filtered_variations = {}
            for sku in skus:
                for combination in sku.combinations.all():
                    if combination.variation_name.name == 'Color' and combination.variation_value.value == selected_color:
                        if not selected_sku:
                            selected_sku = sku
                            selected_stock = sku.stock
                            
                        for comb in sku.combinations.all():
                            if comb.variation_name.name != 'Color':
                                if comb.variation_name.name not in filtered_variations:
                                    filtered_variations[comb.variation_name.name] = {}
                                if comb.variation_value.value not in filtered_variations[comb.variation_name.name]:
                                    filtered_variations[comb.variation_name.name][comb.variation_value.value] = {
                                        'stock': sku.stock
                                    }
        else:
            selected_color = None
            filtered_variations = variation_data
            
            if skus.exists():
                selected_sku = skus.first()
                selected_stock = selected_sku.stock
                
        selected_variation_data = {}
        if selected_sku:
            for comb in selected_sku.combinations.all():
                selected_variation_data[comb.variation_name.name] = comb.variation_value.value
        
        return color_variations, selected_color, filtered_variations, selected_stock, selected_variation_data
    
    def related_products_data(self, product):
        if product.category:
            subcategories = product.category.subcategories.all()
            products_in_subcategories = Product.objects.filter(subcategory__in=subcategories, sku_status=True).exclude(id=product.id)
            
            for sub_product in products_in_subcategories:
                sub_product.sku = SKU.objects.filter(product=sub_product).first()
                sub_product.image = SKUImage.objects.filter(sku=sub_product.sku).first() if sub_product.sku else None
                sub_product.discounted_price = sub_product.sku.get_discount_price()
                        
                ratings_data = calculate_product_ratings(sub_product)
                sub_product.average_rating = ratings_data['average_rating']
                sub_product.total_ratings = ratings_data['total_ratings']
                sub_product.total_reviews = ratings_data['total_reviews']
            
        return products_in_subcategories
    
    def get_product_attributes(self, product):
        attributes_with_values = {}
        
        product_attributes = product.product_attribute.all()
        
        for attribute_value in product_attributes:
            product_attribute = attribute_value.product_attribute
            attributes_with_values[product_attribute.name] = attribute_value.value
        
        return attributes_with_values
        

# To check available Pin code

class CheckPinCode(View):
    def post(self, request, *args, **kwargs):
        pin_code = request.POST.get('pin_code')
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        available_pincode = PinCode.objects.filter(created_by=product.created_by, pin_code=pin_code)

        if available_pincode.exists():
            days_to_delivery = available_pincode.first().delivery_days
            estimated_delivery_date = datetime.now() + timedelta(days=days_to_delivery)
            formatted_date = estimated_delivery_date.strftime('%a, %b %d')

            return JsonResponse({
                'success': True,
                'message': f'Estimated delivery by {formatted_date}'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Delivery not available for this pincode'
            })
    

# To get product details based on the selected variations

class ProductVariationView(View):
    def get(self, request, subcategory_slug, product_slug):
        product = get_object_or_404(Product, slug=product_slug)
        selected_variations = request.GET.dict()
        skus = SKU.objects.filter(product=product).prefetch_related('combinations')

        filtered_variations = {}
        selected_sku = None

        color_selected = 'Color' in selected_variations

        for sku in skus:
            matches_all_variations = True
            sku_color_match = False

            for comb in sku.combinations.all():
                variation_name = comb.variation_name.name
                variation_value = comb.variation_value.value

                if color_selected and variation_name == 'Color':
                    if variation_value == selected_variations.get('Color'):
                        sku_color_match = True

                elif not color_selected and variation_name in selected_variations:
                    if variation_value != selected_variations.get(variation_name):
                        matches_all_variations = False
                        break 

            if color_selected and not sku_color_match:
                continue

            if matches_all_variations:
                if not selected_sku:
                    selected_sku = sku 

                for comb in sku.combinations.all():
                    if comb.variation_name.name != 'Color': 
                        if comb.variation_name.name not in filtered_variations:
                            filtered_variations[comb.variation_name.name] = {}

                        if comb.variation_value.value not in filtered_variations[comb.variation_name.name]:
                            filtered_variations[comb.variation_name.name][comb.variation_value.value] = {
                                'stock': sku.stock
                            }

        images = SKUImage.objects.filter(sku=selected_sku).values_list('image', flat=True)
        original_price = selected_sku.price
        discount_rate = selected_sku.discount_rate
        discounted_price = selected_sku.get_discount_price()

        response_data = {
            'id': product.id,
            'filtered_variations': filtered_variations,
            'images': list(images),
            'original_price': original_price,
            'discount_rate': discount_rate,
            'discounted_price': discounted_price,
        }

        return JsonResponse(response_data, status=200)
    
    
# To check available stock

class CheckStockView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        product_id = data.get('product_id')
        color = data.get('color')
        variations = data.get('variations')

        skus = SKU.objects.filter(product_id=product_id)
        
        variation_ids = []
        for variation in variations:
            variation_name = variation.get('name')
            variation_value = variation.get('value')
            
            sku_combinations = SKUCombination.objects.filter(
                sku__in=skus,
                variation_name__name=variation_name,
                variation_value__value=variation_value
            )
            
            if not sku_combinations.exists():
                return JsonResponse({'error': f'Variation combination not found for {variation_name}: {variation_value}'}, status=404)

            variation_ids.extend(sku_combination.id for sku_combination in sku_combinations)
            
        if color:
            color_combinations = SKUCombination.objects.filter(
                sku__in=skus,
                variation_name__name='Color',
                variation_value__value=color
            )
            if not color_combinations.exists():
                return JsonResponse({'error': f'No SKU found for color: {color}'}, status=404)

            stock_quantity = 0
            stock_available = False

            for color_combination in color_combinations:
                sku = color_combination.sku

                matching_variations = all(
                    SKUCombination.objects.filter(
                        sku=sku,
                        variation_name__name=variation['name'],
                        variation_value__value=variation['value']
                    ).exists()
                    for variation in variations
                )

                if matching_variations:
                    stock_quantity += sku.stock
                    stock_available = stock_quantity > 0

            if not stock_available:
                stock_quantity = 0
                
        stock_info = {
            "in_stock": stock_available,
            'stock_quantity': stock_quantity,
        }                 
    
        return JsonResponse(stock_info)

