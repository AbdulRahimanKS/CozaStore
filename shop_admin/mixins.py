import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
import requests
from cart.models import OrderItemAction, OrderItemRefund
from Ecommerce.settings import YOUR_API_KEY


class ShopRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='Shop').exists():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

class UserRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='Customer').exists():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

class ReturnRefundAPIMixin:
    def get_refund_api_call(self, order_item, order_item_tracking):
        action_item = get_object_or_404(OrderItemAction, order_item_tracking=order_item_tracking)
        action_item.status = 'completed'
        action_item.save()
        
        invoice_id = order_item.order.invoice_id
        amount = order_item.get_cost()
        
        if invoice_id and amount:
            request_data = {
                "KeyType": "invoiceid",
                "Key": invoice_id,
                "RefundChargeOnCustomer": False,
                "ServiceChargeOnCustomer": False,
                "Amount": amount,
                "Comment": "Refund to Customer",
                "AmountDeductedFromSupplier": 0
            }
            
            api_url = "https://apitest.myfatoorah.com/v2/MakeRefund"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {YOUR_API_KEY}"}
            
            try:
                request_data = json.dumps(request_data)
                refund_response = requests.post(api_url, data=request_data, headers=headers).json()
                
                refund_key = refund_response["Data"]["Key"]
                refund_id = refund_response["Data"]["RefundId"]
                refundInvoiceId = refund_response["Data"]["RefundInvoiceId"]
                amount = refund_response["Data"]["Amount"]
                
                order_item_tracking.status = 'returned'
                order_item_tracking.save()
                                    
                refund = OrderItemRefund(
                    order_item_tracking = order_item_tracking,
                    refund_id = refund_id,
                    refund_key = refund_key,
                    refundInvoiceId = refundInvoiceId,
                    amount = amount,
                    status = 'completed'
                )
                refund.save()
                
            except Exception as e:
                return requests.Response({'status': 'error', 'message': str(e)}, status=500)