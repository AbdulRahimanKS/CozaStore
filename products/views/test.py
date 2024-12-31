
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
        
        product = self.product_data(product)
        context['variations'] = product.variations
        context['product'] = product
        
        related_products = self.related_products_data(product)
        context['products_in_subcategories'] = related_products[:10]

        categories = get_category()
        context['categories'] = categories
        
        if self.request.user.is_authenticated:
            wishlist_items = WishlistItem.objects.filter(user=self.request.user).values_list('product_id', flat=True)
            wishlist_count = WishlistItem.objects.filter(user=self.request.user).count()
        else:
            wishlist_items = []
            wishlist_count = 0
            
        context['wishlist_items'] = wishlist_items
        context['wishlist_count'] = wishlist_count

        self.set_variations_in_context(context, product)
        
        return context
    
    def product_data(self, product):
        if product:
            product.sku = SKU.objects.filter(product=product).first()
            product.images = product.sku.images.all() if product.sku else []
            product.discounted_price = None
            
            if product.sku:
                original_price = product.sku.price
                discount_percentage = product.sku.discount_rate
                
                if discount_percentage is not None:
                    discount_amount = (original_price * discount_percentage) / Decimal('100')
                    discounted_price = original_price - discount_amount
                    
                    product.discounted_price = int(round(discounted_price))
                    product.discounted_price = f"{product.discounted_price:,}"
            
                product.variations = product.sku.variations
                product.sku.price = int(round(product.sku.price))
                product.sku.price = f"{product.sku.price:,}"
        
        return product
    
    def related_products_data(self, product):
        if product.category:
            subcategories = product.category.subcategories.all()
            products_in_subcategories = Product.objects.filter(subcategory__in=subcategories).exclude(id=product.id)
            
            for sub_product in products_in_subcategories:
                sub_product.sku = SKU.objects.filter(product=sub_product).first()
                sub_product.image = SKUImage.objects.filter(sku=sub_product.sku).first() if sub_product.sku else None
                
                sub_product.discounted_price = None
                if sub_product.sku:
                    original_price = sub_product.sku.price
                    discount_percentage = sub_product.sku.discount_rate
                    if discount_percentage is not None:
                        discount_amount = (original_price * discount_percentage) / Decimal('100')
                        discounted_price = original_price - discount_amount
                        sub_product.discounted_price = int(round(discounted_price))
                        sub_product.discounted_price = f"{sub_product.discounted_price:,}"
                        
                ratings_data = calculate_product_ratings(sub_product)
                sub_product.average_rating = ratings_data['average_rating']
                sub_product.total_ratings = ratings_data['total_ratings']
                sub_product.total_reviews = ratings_data['total_reviews']
            
        return products_in_subcategories
                            

    def set_variations_in_context(self, context, product):
        skus = SKU.objects.filter(product=product)
        variations = Variations.objects.filter(skus__in=skus)
        
        size_values = variations.exclude(size__in=['Onesize', 'Pack']).exclude(size='').filter(skus__stock_quantity__gt=0).values_list('size', flat=True).distinct()
        context['size_values'] = size_values

        one_size = variations.filter(size='Onesize', skus__stock_quantity__gt=0).values_list('size', flat=True).first()
        context['one_size'] = one_size

        pack = variations.filter(size='Pack', skus__stock_quantity__gt=0).values_list('size', flat=True).first()
        context['pack'] = pack

        shoe_size = variations.filter(shoe_size__gt=0, skus__stock_quantity__gt=0).values_list('shoe_size', flat=True).distinct()
        context['shoe_size'] = shoe_size

        quantity = variations.values_list('quantity', flat=True).exclude(quantity=0).filter(skus__stock_quantity__gt=0).distinct()
        context['quantity'] = quantity
        
        context['color_values'] = variations.values_list('color__color_value', flat=True).exclude(color__color_value__isnull=True).distinct()
        context['category'] = product.category
        context['subcategory'] = product.subcategory
       