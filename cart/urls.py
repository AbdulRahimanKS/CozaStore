from django.urls import path
from cart.views.cart_views import CartItemCreateView, ShoppingCartView, CheckStockView, RemoveCartItemView, SetDefaultAddressView, SetOrderDetailsView, OrdersListView, ApplyCouponView, TrackOrderView, RemoveCouponView
from cart.views.paymentapi_views import Initiate_PaymentAPI, ExecutePaymentView, OrderSuccessView, OrderFailedView, OrderCancelView, OrderReturnView


urlpatterns = [
    path('add_to_cart/', CartItemCreateView.as_view(), name='add_to_cart'),
    path('cart_view/', ShoppingCartView.as_view(), name='cart_view'),
    path('check_stock/<int:product_id>/<int:sku_id>/', CheckStockView.as_view(), name='check_stock'),
    path('remove_cartitem/<int:product_id>/<int:sku_id>/', RemoveCartItemView.as_view(), name='remove_cartitem'),
    path('set_default_address/', SetDefaultAddressView.as_view(), name='set_default_address'),
    path('apply_coupon/', ApplyCouponView.as_view(), name='apply_coupon'),
    path('remove_coupon/', RemoveCouponView.as_view(), name='remove_coupon'),
    path('set_order_details/', SetOrderDetailsView.as_view(), name='set_order_details'),
    path('payment_method_selection/<str:order_id>/', Initiate_PaymentAPI.as_view(), name='payment_method_selection'),
    path('process_payment/', ExecutePaymentView.as_view(), name='process_payment'),
    path('order_success/', OrderSuccessView.as_view(), name='order_success'),
    path('order_failed/', OrderFailedView.as_view(), name='order_failed'),
    path('orders_list/', OrdersListView.as_view(), name='orders_list'),
    path('track_item/<str:tracking_id>/', TrackOrderView.as_view(), name='track_item'),
    path('cancel_order/', OrderCancelView.as_view(), name='cancel_order'),
    path('return_order/', OrderReturnView.as_view(), name='return_order')
]

