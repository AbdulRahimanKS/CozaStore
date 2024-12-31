from django.contrib import admin
from . models import Category, SubcategoryVariation, SubcategoryAttribute, VariationName, VariationValue, ProductAttribute, ProductAttributeValue, Product, SKU, SKUImage, CheckOutAddresses, Rating, WishlistItem, SKUCombination

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
admin.site.register(Category, CategoryAdmin)

class ProductAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
admin.site.register(Product, ProductAdmin)

class CheckOutAddressesAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'mobile', 'city', 'state', 'pin_code', 'address_type', 'default']
    list_filter = ['user', 'state', 'city', 'pin_code', 'address_type']
    search_fields = ['user__email', 'name', 'mobile', 'city', 'state', 'pin_code']
    list_editable = ['default']
admin.site.register(CheckOutAddresses, CheckOutAddressesAdmin)

class RatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    search_fields = ('product__name', 'user__email')
    list_filter = ('rating', 'created_at')
admin.site.register(Rating, RatingAdmin)

admin.site.register([SKUCombination, SubcategoryVariation, SubcategoryAttribute, VariationName, VariationValue, ProductAttribute, ProductAttributeValue, SKU, SKUImage, WishlistItem])

