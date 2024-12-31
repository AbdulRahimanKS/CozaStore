from django.db import models
from django.urls import reverse
from django.utils.text import slugify


PRODUCTS_PRODUCT_MODEL = 'products.Product'
PRODUCTS_CATEGORY_MODEL = 'products.Category'
PRODUCTS_VARIATIONS_NAME_MODEL = 'products.VariationName'
PRODUCTS_VARIATIONS_VALUE_MODEL = 'products.VariationValue'
PRODUCTS_ATTRIBUTE_MODEL = 'products.ProductAttribute'
PRODUCTS_ATTRIBUTE_VALUE_MODEL = 'products.ProductAttributeValue'
PRODUCTS_SKU_MODEL = 'products.SKU'
ACCOUNTS_CUSTOMUSER_MODEL = 'accounts.CustomUser'


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(PRODUCTS_CATEGORY_MODEL, on_delete=models.CASCADE, related_name='subcategories', blank=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def save(self, *args, **kwargs):
        base_slug = slugify(self.name)

        if not self.slug:
            if self.parent:
                parent_slug = self.parent.slug
                self.slug = f"{parent_slug}-{base_slug}"
            else:
                self.slug = base_slug

        super(Category, self).save(*args, **kwargs)
        
        
class SubcategoryVariation(models.Model):
    subcategory = models.ForeignKey(PRODUCTS_CATEGORY_MODEL, on_delete=models.CASCADE, related_name='subcategory_variations')
    variation = models.ManyToManyField(PRODUCTS_VARIATIONS_NAME_MODEL, related_name='subcategory_variation_names')

    def __str__(self):
        variation_names = ', '.join([v.name for v in self.variation.all()])
        return f"{self.subcategory.name} - {variation_names}"
    
    
class SubcategoryAttribute(models.Model):
    subcategory = models.ForeignKey(PRODUCTS_CATEGORY_MODEL, on_delete=models.CASCADE, related_name='subcategory_attributes')
    attribute = models.ManyToManyField(PRODUCTS_ATTRIBUTE_MODEL, related_name='subcategory_attribute_names')

    def __str__(self):
        attribute_names = ', '.join([v.name for v in self.attribute.all()])
        return f"{self.subcategory.name} - {attribute_names}"        


class VariationName(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=False)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.name = ' '.join([word.capitalize() for word in self.name.split()])
        super(VariationName, self).save(*args, **kwargs)
        
        
class VariationValue(models.Model):
    variation = models.ForeignKey(PRODUCTS_VARIATIONS_NAME_MODEL, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ('variation', 'value')

    def __str__(self):
        return self.value
    
 
class ProductAttribute(models.Model):
    name = models.CharField(max_length=255, unique=True, blank=False)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.name = ' '.join([word.capitalize() for word in self.name.split()])
        super(ProductAttribute, self).save(*args, **kwargs)


class ProductAttributeValue(models.Model):
    product_attribute = models.ForeignKey(PRODUCTS_ATTRIBUTE_MODEL, related_name='product_type', on_delete=models.CASCADE)
    value = models.CharField(max_length=255)
    
    class Meta:
        unique_together = ('product_attribute', 'value')

    def __str__(self):
        return self.value


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    brand = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sku_status = models.BooleanField(default=False)
    category = models.ForeignKey(PRODUCTS_CATEGORY_MODEL, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(PRODUCTS_CATEGORY_MODEL, on_delete=models.CASCADE, related_name='sub_products')
    product_attribute = models.ManyToManyField(PRODUCTS_ATTRIBUTE_VALUE_MODEL, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(ACCOUNTS_CUSTOMUSER_MODEL, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ('name',)
        verbose_name = 'product'
        verbose_name_plural = 'products'
        
    def get_available_variations(self):
        return SKU.objects.filter(product=self, stock__gt=0).values('variations__name', 'variations__value').distinct()

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug

            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        super(Product, self).save(*args, **kwargs)

    def get_url(self):
        return reverse('product_detail', args=[self.subcategory.slug, self.slug])

 
class SKU(models.Model):
    product = models.ForeignKey(PRODUCTS_PRODUCT_MODEL, on_delete=models.CASCADE, related_name='skus')
    price = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(default=0)
    discount_rate = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.get_variation_display()}"

    def get_variation_display(self):
        return ', '.join([str(combination) for combination in self.combinations.all()])

    def get_discount_price(self):
        if self.discount_rate:  
            return round(self.price - (self.price * self.discount_rate / 100))
        return self.price
        

class SKUCombination(models.Model):
    sku = models.ForeignKey(PRODUCTS_SKU_MODEL, on_delete=models.CASCADE, related_name='combinations')
    variation_name = models.ForeignKey(VariationName, on_delete=models.CASCADE)
    variation_value = models.ForeignKey(VariationValue, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.sku.product.name}: {self.variation_name.name}: {self.variation_value.value}"
    
    
class SKUImage(models.Model):
    sku = models.ForeignKey(PRODUCTS_SKU_MODEL, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='sku_images/')

    def __str__(self):
        return f'{self.sku.product.name} - {self.image.name}'
    
    
class Rating(models.Model):
    product = models.ForeignKey(PRODUCTS_PRODUCT_MODEL, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(ACCOUNTS_CUSTOMUSER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')

    def __str__(self):
        return f'{self.product.name} - {self.rating} by {self.user.email}'

    
class CheckOutAddresses(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('Home', 'Home'),
        ('Work', 'Work'),
    )
    
    user = models.ForeignKey(ACCOUNTS_CUSTOMUSER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=250, blank=False)
    mobile = models.CharField(max_length=10, blank=False)
    pin_code = models.CharField(max_length=6, blank=False)
    locality = models.CharField(max_length=250, blank=False)
    address = models.TextField()
    city = models.CharField(max_length=250, blank=False)
    state = models.CharField(max_length=100, blank=False)
    landmark = models.CharField(max_length=250, blank=True, null=True)
    alternate_phone = models.CharField(max_length=10, blank=True)
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, blank=False)
    default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} - {self.address}'
    
    def save(self, *args, **kwargs):
        if self.default:
            CheckOutAddresses.objects.filter(user=self.user, default=True).update(default=False)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'CheckOutAddresses'
        
        
class WishlistItem(models.Model):
    user = models.ForeignKey(ACCOUNTS_CUSTOMUSER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.first_name}'s Wishlist Item: {self.product.name}"