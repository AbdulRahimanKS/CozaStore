from products.models import SKU, SKUImage, Category, Rating
from django.db.models import Count, Avg


# To get product details

def get_products(products):
    for product in products:
        product.sku = SKU.objects.filter(product=product).first()
        product.image = SKUImage.objects.filter(sku=product.sku).first() if product.sku else None
        product.price = product.sku.price
        product.discounted_price = product.sku.get_discount_price()

        ratings = Rating.objects.filter(product=product)
        total_ratings = ratings.count()
        total_reviews = ratings.filter(review__isnull=False).exclude(review__exact='').count()

        if total_ratings > 0:
            average_rating = ratings.aggregate(Avg('rating'))['rating__avg']
            product.average_rating = round(average_rating, 1)
        else:
            product.average_rating = None
        
        product.total_ratings = total_ratings
        product.total_reviews = total_reviews
    
    return products


# To calculate rating

def calculate_product_ratings(product):
    ratings = Rating.objects.filter(product=product)

    total_ratings = ratings.count()
    total_reviews = ratings.exclude(review__isnull=True).exclude(review__exact='').count() or 0
    
    ratings_data = {
        5: {'count': 0, 'percentage': 0},
        4: {'count': 0, 'percentage': 0},
        3: {'count': 0, 'percentage': 0},
        2: {'count': 0, 'percentage': 0},
        1: {'count': 0, 'percentage': 0},
    }

    if total_ratings > 0:
        average_rating = ratings.aggregate(Avg('rating'))['rating__avg']
        average_rating = round(average_rating, 1)
        
        for rating in ratings.values('rating').annotate(count=Count('rating')):
            star = rating['rating']
            count = rating['count']
            percentage = (count / total_ratings) * 100
            ratings_data[star]['count'] = f'{count:,}'
            ratings_data[star]['percentage'] = percentage
            
    else:
        average_rating = 0

    return {
        'average_rating': average_rating,
        'total_ratings': f'{total_ratings:,}',
        'total_reviews': f'{total_reviews:,}',
        'ratings_data': ratings_data
    }


# To calculated discounted_price for filtering

def calculate_discounted_price(product):
    sku = SKU.objects.filter(product=product).first()
    if sku:
        original_price = sku.price
        discounted_price = sku.get_discount_price()
        
        return original_price, discounted_price
    return None, None


# To calculate discounted_price based on SKU

def calculate_discount_price(products):
    for product in products:
        product.sku = SKU.objects.filter(product=product).first()

        product.original_price = product.sku.price
        product.discounted_price = product.sku.get_discount_price()
                
    return products

