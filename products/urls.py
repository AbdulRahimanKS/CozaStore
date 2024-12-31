from django.urls import path
from products.views.product_views import IndexView, products_by_category, ProductSearchView, ShopView, FeaturedView, ProductDetailView, ParentCategoryProductsView, SubcategoryProductsView, CheckPinCode, ProductVariationView, CheckStockView
from products.views.customer_views import CustomerProfileView, AddressDeleteView, AddressFormView, ProductReviewListView, RatingManageView, AddWishlistView, WishlistView, CheckDefaultAddressView, DeleteWishlistItemView, FCMTokenCreateView, SubscribeToTopicView


urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('save_fcm_token/', FCMTokenCreateView.as_view(), name='save_fcm_token'),
    path('subscribe_to_topic/', SubscribeToTopicView.as_view(), name='subscribe_to_topic'),
    path('products_by_category/<str:category_name>/', products_by_category, name='products_by_category'),
    path('search_products/', ProductSearchView.as_view(), name='search_products'),
    path('shop_view/', ShopView.as_view(), name='shop_view'),
    path('featured_view/', FeaturedView.as_view(), name='featured_view'),   
    path('check_pin_code/', CheckPinCode.as_view(), name='check_pin_code'),
    path('check_stock/', CheckStockView.as_view(), name='check_stock'),
    
    path('profile/', CustomerProfileView.as_view(), name='profile'),
    path('check_default_address/', CheckDefaultAddressView.as_view(), name='check_default_address'),
    path('delete_address/', AddressDeleteView.as_view(), name='delete_address'),
    path('get_address_form/<int:pk>/', AddressFormView.as_view(), name='get_address_form'),
    path('update_address/<int:pk>/', AddressFormView.as_view(), name='update_address'),
    path('add_to_wishlist/', AddWishlistView.as_view(), name='add_to_wishlist'),
    path('wishlist_view/', WishlistView.as_view(), name='wishlist_view'),
    path('delete_wishlist_item/<int:pk>/', DeleteWishlistItemView.as_view(), name='delete_wishlist_item'),
    
    path('shop/<slug:category_slug>/', ParentCategoryProductsView.as_view(), name='search_products_categoryid'),
    path('<slug:subcategory_slug>/', SubcategoryProductsView.as_view(), name='search_products_subcategoryid'),
    path('<slug:subcategory_slug>/<slug:product_slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('<slug:subcategory_slug>/<slug:product_slug>/get_product_variation/', ProductVariationView.as_view(), name='get_product_variation'),
    path('<slug:subcategory_slug>/<slug:product_slug>/rate_product/', RatingManageView.as_view(), name='rate_product'),
    path('<slug:subcategory_slug>/<slug:product_slug>/reviews/', ProductReviewListView.as_view(), name='product_reviews'),
]

