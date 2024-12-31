from django.urls import path
from shop_admin.views.category_views import CategoryAddView, CategoryListView, CategoryUpdateView, CategoryDeleteView
from shop_admin.views.product_views import ProductListView, ProductAddView, get_subcategories, ProductUpdateView, ProductDeleteView, get_attributes
from shop_admin.views.SKU_views import SKUListView, AddSKUView, UpdateSKUView, DeleteSKUView
from shop_admin.views.admin_views import ProfileView, NotificationsListView, NotificationsReadView, OrderListView, OrderUpdateView, InvoiceView, InvoiceDownloadView, DashboardView
from shop_admin.views.pincode_views import PinCodeListView, PinCodeAddView, PinCodeUpdateView, PinCodeDeleteView
from shop_admin.views.variation_views import AddVariationView, VariationListView, UpdateVariationView, DeleteVariationView
from shop_admin.views.attribute_views import AttributeListView, AddAttributeView, DeleteAttributeView, UpdateAttributeView
from shop_admin.views.coupon_views import CouponListView, CouponAddView, UpdateCouponView, DeleteCouponView


urlpatterns = [
    path('profile_view/', ProfileView.as_view(), name='profile_view'),   
    path('dashboard/', DashboardView.as_view(), name='dashboard'),    
    path('notifications/', NotificationsListView.as_view(), name='notifications'),  
    path('read_notifications/<int:notification_id>/', NotificationsReadView.as_view(), name='read_notifications'),
    path('invoice_view/<int:id>/', InvoiceView.as_view(), name='invoice_view'),
    path('invoice_download/<int:id>/', InvoiceDownloadView.as_view(), name='invoice_download'),
    path('list_orders/', OrderListView.as_view(), name='list_orders'),
    path('update_order/<int:id>/', OrderUpdateView.as_view(), name='update_order'),

    path('list_category/', CategoryListView.as_view(), name='list_category'),
    path('add_category/', CategoryAddView.as_view(), name='add_category'),
    path('add_subcategory/', CategoryAddView.as_view(), name='add_subcategory'),
    path('update_category/<int:pk>/', CategoryUpdateView.as_view(), name='update_category'),
    path('delete_category/', CategoryDeleteView.as_view(), name='delete_category'),

    path('list_product/', ProductListView.as_view(), name='list_product'),
    path('add_product/', ProductAddView.as_view(), name='add_product'),
    path('get-subcategories/<int:category_id>/', get_subcategories, name='get_subcategories'),
    path('get-attributes/<int:subcategory_id>/', get_attributes, name='get_attributes'),
    path('update_product/<int:pk>/', ProductUpdateView.as_view(), name='update_product'),
    path('delete_product/', ProductDeleteView.as_view(), name='delete_product'),

    path('list_sku/<int:product_id>', SKUListView.as_view(), name='list_sku'),
    path('add_sku/<int:product_id>/', AddSKUView.as_view(), name='add_sku'),
    path('update_sku/<int:product_id>/<int:sku_id>/', UpdateSKUView.as_view(), name='update_sku'),
    path('delete_sku/<int:product_id>/<int:sku_id>/', DeleteSKUView.as_view(), name='delete_sku'),

    path('list_pincode/', PinCodeListView.as_view(), name='list_pincode'),
    path('add_pincode/', PinCodeAddView.as_view(), name='add_pincode'),
    path('update_pincode/<int:pk>/', PinCodeUpdateView.as_view(), name='update_pincode'),
    path('delete_pincode/', PinCodeDeleteView.as_view(), name='delete_pincode'),

    path('list_variation/', VariationListView.as_view(), name='list_variation'),
    path('add_variation/', AddVariationView.as_view(), name='add_variation'),
    path('update_variation/<int:pk>/', UpdateVariationView.as_view(), name='update_variation'),
    path('delete_variation/', DeleteVariationView.as_view(), name='delete_variation'),
     
    path('list_attribute/', AttributeListView.as_view(), name='list_attribute'),
    path('add_attribute/', AddAttributeView.as_view(), name='add_attribute'),
    path('update_attribute/<int:pk>/', UpdateAttributeView.as_view(), name='update_attribute'),
    path('delete_attribute/', DeleteAttributeView.as_view(), name='delete_attribute'),
    
    path('list_coupon/', CouponListView.as_view(), name='list_coupon'),    
    path('add_coupon/', CouponAddView.as_view(), name='add_coupon'),
    path('update_coupon/<int:pk>/', UpdateCouponView.as_view(), name='update_coupon'),
    path('delete_coupon/', DeleteCouponView.as_view(), name='delete_coupon'),
]

