import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
import requests
from Ecommerce.settings import YOUR_API_KEY
from datetime import datetime, timedelta
from django.utils import timezone
from zoneinfo import ZoneInfo
from cart.models import Order, OrderItem, OrderItemTracking, OrderItemAction, OrderItemRefund
from shop_admin.models import PinCode
from shop_admin.mixins import UserRequiredMixin


# To select payment options

class Initiate_PaymentAPI(UserRequiredMixin, APIView):
    def get(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, order_id=order_id)
        invoice_amount = order.discounted_amount
        currency_iso = "AED"
        order_id = order.order_id

        if invoice_amount and currency_iso:
            initiatepay_request = {
                "InvoiceAmount": invoice_amount,
                "CurrencyIso": currency_iso,
            }

            if initiatepay_request:
                api_url = "https://apitest.myfatoorah.com/v2/InitiatePayment"
                headers = {
                    "Authorization": f"Bearer {YOUR_API_KEY}",
                    "Content-Type": "application/json"
                }

                request_data = json.dumps(initiatepay_request)
                initiatedpay_response = requests.post(api_url, data=request_data, headers=headers).json()

                payment_methods = initiatedpay_response["Data"]["PaymentMethods"]
                payment_method_list = [
                    {
                        "payment_method": method["PaymentMethodEn"],
                        "payment_method_id": method["PaymentMethodId"]
                    } for method in payment_methods if not method["IsDirectPayment"]
                ]
                return render(request, 'payment_method_selection.html', {"payment_methods": payment_method_list, "order_id": order_id})
            
            else:
                return JsonResponse({"status": False, "error": "No initiatepay_request provided"})
        else:
            return JsonResponse({"status": False, "error": "Required Fields are not provided"})


# To execute payment

class ExecutePaymentView(UserRequiredMixin, APIView):
    def post(self, request):
        order_id = request.POST.get('order_id')
        payment_method_id = request.POST.get('payment_method_id')
        
        order = get_object_or_404(Order, order_id=order_id)
        invoice_amount = order.discounted_amount
        currency_iso = "KWD"
        customer_email = order.user.email
        
        if payment_method_id == 'cod':
            order.generate_invoice_id()
            order.save()
            return redirect('order_success')
        
        else:
            if customer_email:
                payment_url = "https://apitest.myfatoorah.com/v2/ExecutePayment"
                headers = {
                    "Authorization": f"Bearer {YOUR_API_KEY}",
                    "Content-Type": "application/json"
                }
                payment_data = {
                    "InvoiceValue": invoice_amount,
                    "PaymentMethodId": payment_method_id,
                    "DisplayCurrencyIso": currency_iso,
                    "CustomerEmail": customer_email,
                    "Language": "en",
                    "CallBackUrl": "http://127.0.0.1:8000/cart/order_success/",
                    "ErrorUrl": "http://127.0.0.1:8000/cart/order_failed/"
                }
                
                response = requests.post(payment_url, json=payment_data, headers=headers).json()
                invoiceID = response['Data']['InvoiceId']
                order.invoice_id = invoiceID
                order.save()
                
                return JsonResponse({
                    'status': 'success',
                    'paymenturl': response['Data']['PaymentURL'],
                })

        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while processing the payment'
        })


# Order success page

class OrderSuccessView(UserRequiredMixin, APIView):    
    def get(self, request, *args, **kwargs):
        paymentId = request.GET.get('paymentId')
        
        if paymentId:
            headers = {
                "Authorization": f"Bearer {YOUR_API_KEY}",
                "Content-Type": "application/json"
            }
            verify_url = "https://apitest.myfatoorah.com/v2/GetPaymentStatus"
            verify_data = {"Key": paymentId, "KeyType": "PaymentId"}
            
            response = requests.post(verify_url, json=verify_data, headers=headers).json()
            transactions = response["Data"]["InvoiceTransactions"]
            CustomerEmail = response["Data"]["CustomerEmail"]
            invoiceID = response["Data"]["InvoiceId"]
            
            if transactions and invoiceID and CustomerEmail:
                order = get_object_or_404(Order, invoice_id=invoiceID, user__email=CustomerEmail)
                order_items = OrderItem.objects.filter(order=order)
                
                if response["Data"]['InvoiceTransactions']:
                    for transaction in response["Data"]['InvoiceTransactions']:
                        order.payment_type = transaction["PaymentGateway"]
                        order.payment_transaction_id = transaction["TransactionId"]
                        order.payment_status = 'completed'
                        order.order_time = timezone.now()
                        order.delivery_confirmed = 'True'
                        
                        transaction_datetime = transaction["TransactionDate"]
                        
                        if '.' in transaction_datetime:
                            transaction_datetime = transaction_datetime[:transaction_datetime.index('.') + 7]

                        transaction_datetime_naive = datetime.strptime(transaction_datetime, "%Y-%m-%dT%H:%M:%S.%f")
                        transaction_datetime_aware = timezone.make_aware(transaction_datetime_naive, timezone=ZoneInfo("UTC"))
                        
                        order.transaction_datetime = transaction_datetime_aware
                        order.save()
                        
                        for order_item in order_items:
                            order_item.is_paid = True
                            order_item.save()
                        
                min_delivery_days, max_delivery_days = self.calculate_delivery_dates(order)             
                order_details = self.order_details(order, min_delivery_days, max_delivery_days)
                        
        else:
            user = self.request.user
            order = Order.objects.filter(user=user).order_by('-created_at').first()
            if order:
                order.payment_type = 'cod'
                order.payment_transaction_id = ''
                order.transaction_datetime = None
                order.payment_status = 'pending'
                order.delivery_confirmed = 'True'
                order.order_time = timezone.now()
                order.save()   
                
            min_delivery_days, max_delivery_days = self.calculate_delivery_dates(order)             
            order_details = self.order_details(order, min_delivery_days, max_delivery_days)
                    
        return render(request, 'order_success.html', {'order_details': order_details})
    
    def order_details(self, order, min_delivery_days, max_delivery_days):
        order_details = {
            'order_id': order.order_id,
            'address': order.address_address,
            'locality': order.address_locality,
            'city': order.address_city,
            'state': order.address_state,
            'pin_code': order.address_pin_code,
            'mobile': order.address_mobile,
            'payment_method': f"Cash on delivery" if order.payment_type=="cod" else order.payment_type,
            'delivery_days': f"{min_delivery_days} days" if max_delivery_days is None else f"{min_delivery_days}-{max_delivery_days} days"
        }
        
        return order_details

    def calculate_delivery_dates(self, order):
        delivery_days_list = []
        
        for item in order.items.all(): 
            user = item.product.created_by
            pin_code = order.address_pin_code
            pincode_obj = PinCode.objects.get(created_by=user, pin_code=pin_code) 
            delivery_days = pincode_obj.delivery_days
            delivery_date = order.order_time + timedelta(days=delivery_days)
            item.delivery_date = delivery_date
            item.save()
            
            delivery_days_list.append(delivery_days)
            
        if delivery_days_list:
            min_delivery_days = min(delivery_days_list)
            max_delivery_days = max(delivery_days_list)
            
            if min_delivery_days == max_delivery_days:
                return min_delivery_days, None

        return min_delivery_days, max_delivery_days
    

# Order failed page

class OrderFailedView(UserRequiredMixin, APIView):
    def get(self, request, *args, **kwargs):
        paymentId = request.GET.get('paymentId')
        
        if paymentId:
            headers = {
                "Authorization": f"Bearer {YOUR_API_KEY}",
                "Content-Type": "application/json"
            }
            verify_url = "https://apitest.myfatoorah.com/v2/GetPaymentStatus"
            verify_data = {"Key": paymentId, "KeyType": "PaymentId"}
            
            response = requests.post(verify_url, json=verify_data, headers=headers).json()
            transactions = response["Data"]["InvoiceTransactions"]  
            CustomerEmail = response["Data"]["CustomerEmail"]
            invoiceID = response["Data"]["InvoiceId"]
            
            if transactions and invoiceID and CustomerEmail:
                order = get_object_or_404(Order, invoice_id=invoiceID, user__email=CustomerEmail)
                
                if response["Data"]['InvoiceTransactions']:
                    for transaction in response["Data"]['InvoiceTransactions']:
                        order.payment_type = transaction["PaymentGateway"]
                        order.payment_transaction_id = transaction["TransactionId"]
                        order.payment_status = 'failed'
                        
                        transaction_datetime = transaction["TransactionDate"]
                        if '.' in transaction_datetime:
                            transaction_datetime = transaction_datetime[:transaction_datetime.index('.') + 7]
                        transaction_datetime_naive = datetime.strptime(transaction_datetime, "%Y-%m-%dT%H:%M:%S.%f")
                        transaction_datetime_aware = timezone.make_aware(transaction_datetime_naive, timezone=ZoneInfo("UTC"))
                        order.transaction_datetime = transaction_datetime_aware
                        order.save()
                    
                order_id = order.order_id
                
        return render(request, 'order_failed.html', {'order_id': order_id})


# To cancel an order

class OrderCancelView(UserRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        order_item_id = request.POST.get('order_item_id')
        cancel_reason = request.POST.get('cancel_reason')
        other_reason = request.POST.get('other_reason').strip()
        
        if cancel_reason == "Other":
            cancel_reason = other_reason
        
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order_item_tracking = get_object_or_404(OrderItemTracking, order_item=order_item)
        tracking_id = order_item_tracking.tracking_id 
        
        if order_item_tracking.status == 'processing':
            action_item = OrderItemAction(
                order_item_tracking=order_item_tracking,
                action_type='cancellation',
                reason=cancel_reason,
                status='completed'
            )
            action_item.save()
            
            if order_item.order.payment_type == 'cod':
                self.update_order_tracking_status(order_item_tracking, order_item)            
                return redirect(reverse('track_item', kwargs={'tracking_id': tracking_id}))
            
            else:
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
                        
                        self.update_order_tracking_status(order_item_tracking, order_item)
                                            
                        refund = OrderItemRefund(
                            order_item_tracking = order_item_tracking,
                            refund_id = refund_id,
                            refund_key = refund_key,
                            refundInvoiceId = refundInvoiceId,
                            amount = amount,
                            status = 'completed'
                        )
                        refund.save()
                        
                        return redirect(reverse('track_item', kwargs={'tracking_id': tracking_id}))
                        
                    except Exception as e:
                        return Response({'status': 'error', 'message': str(e)}, status=500)
                
        return redirect(reverse('track_item', kwargs={'tracking_id': tracking_id}))
    
    def update_order_tracking_status(self, order_item_tracking, order_item):
        order_item_tracking.status = 'cancelled'
        order_item_tracking.save()
        
        order = order_item.order
        order.is_cancelled = True
        order.save()
                    
                    
# To return an order
    
class OrderReturnView(UserRequiredMixin, APIView):
    def post(self, request, *args, **kwargs):
        order_item_id = request.POST.get('order_item_id')
        return_reason = request.POST.get('return_reason')
        other_reason = request.POST.get('other_reason').strip()
        
        if return_reason == "Other":
            return_reason = other_reason
        
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order_item_tracking = get_object_or_404(OrderItemTracking, order_item=order_item)
        tracking_id = order_item_tracking.tracking_id
        
        if order_item_tracking.status == 'delivered':
            action_item = OrderItemAction(
                order_item_tracking=order_item_tracking,
                action_type='return',
                reason=return_reason,
                status='pending'
            )
            action_item.save() 
            
            return redirect(reverse('track_item', kwargs={'tracking_id': tracking_id}))
            
        return redirect(reverse('track_item', kwargs={'tracking_id': tracking_id}))


    