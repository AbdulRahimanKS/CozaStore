from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, render, redirect
from shop_admin.models import Notification, UserProfile
from accounts.models import CustomUser
from shop_admin.forms import ProfileForm,ChangePasswordForm
from cart.models import OrderItem, Order, OrderItemTracking, OrderItemAction
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from shop_admin.mixins import ShopRequiredMixin, ReturnRefundAPIMixin
from shop_admin.utils import send_refund_success_notifcation
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from django.utils import timezone
from cart.models import OrderItem
from django.db.models import Sum, F, Subquery, OuterRef, Value as V, CharField, Count
from django.db.models.functions import Coalesce, Concat, TruncDay, TruncMonth
from products.models import SKUImage, Product


PROFILE_TEMPLATE  = 'profile_view.html'

# To update profile and change password

class ProfileView(ShopRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id=request.user.id)
        form1 = ProfileForm(instance=user)
        form2 = ChangePasswordForm()
        user_profile = getattr(user, 'userprofile', None)

        return self.render_profile(request, form1, form2, user, user_profile)
    
    def post(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id=request.user.id)
        form1 = ProfileForm(request.POST, request.FILES, instance=user)
        form2 = ChangePasswordForm(request.POST, user=user)
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        if 'profile_update' in request.POST:
            if form1.is_valid():
                self.update_user_and_profile(request, form1, user_profile)
                messages.success(request, 'Profile details updated successfully')
                return redirect('profile_view')
            else:
                self.handle_form_errors(request, form1)

        elif 'change_password' in request.POST:
            if form2.is_valid():
                self.change_password(request, form2)
                messages.success(request, 'Password updated successfully')
                return redirect('profile_view')
            else:
                self.handle_form_errors(request, form2)
                return redirect('profile_view')

        return self.render_profile(request, form1, form2, user, user_profile)

    def render_profile(self, request, form1, form2, user, user_profile):
        return render(request, PROFILE_TEMPLATE, {
            'form': form1,
            'ChangePasswordForm': form2,
            'user': user,
            'user_profile': user_profile
        })

    def update_user_and_profile(self, request, form1, user_profile):
        user = form1.save(commit=False)
        user.countryCode = request.POST.get('countryCode', user.countryCode)
        user.save()

        if request.POST.get('remove_image') == 'true' and user_profile.profile_image:
            user_profile.profile_image.delete(save=False)
            user_profile.profile_image = None

        profile_fields = [
            'about', 'company', 'job_title', 'address', 'city', 
            'LinkedIn', 'Facebook', 'Instagram'
        ]
        for field in profile_fields:
            setattr(user_profile, field, request.POST.get(field, getattr(user_profile, field)))

        profile_image = request.FILES.get('profile_image')
        if profile_image:
            user_profile.profile_image = profile_image

        user_profile.save()

    def change_password(self, request, form2):
        user = request.user
        user.set_password(form2.cleaned_data['new_password'])
        user.save()
        update_session_auth_hash(request, user)
        
    def handle_form_errors(self, request, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)


# To show notifications

class NotificationsListView(ShopRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications.html'
    context_object_name = 'notifications'
    paginate_by = 8
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Notification.objects.filter(admin=self.request.user).order_by('is_read', '-created_at')
        

# To read notifications

class NotificationsReadView(ShopRequiredMixin, View):
    def post(self, request, notification_id, *args, **kwargs):
        if self.request.user.is_authenticated:
            notification = Notification.objects.get(id=notification_id, admin=self.request.user)
            notification.is_read = True
            notification.save()
            
            return JsonResponse({'status': 'success'})
        
        return JsonResponse({'status': 'error', 'message': 'User not authenticated'})
    
    
# To show orders list

class OrderListView(ShopRequiredMixin, ReturnRefundAPIMixin, ListView):
    model = OrderItem
    template_name = 'list_orders.html'
    context_object_name = 'order_items'
    
    def get_queryset(self):
        queryset = OrderItem.objects.filter(product__created_by=self.request.user, order__delivery_confirmed=True).select_related('tracking_info', 'order').order_by('-tracking_info__action_info__status', '-order__created_at')
        return queryset
    
    def post(self, request, *args, **kwargs):
        order_item_id = request.POST.get('order_item_id')
        action = request.POST.get('action')
        
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order_item_tracking = get_object_or_404(OrderItemTracking, order_item=order_item)
        
        if action == 'reject':
            action_item = get_object_or_404(OrderItemAction, order_item_tracking=order_item_tracking)
            action_item.status = 'rejected'
            action_item.save()
            
            order_item_tracking.status = 'delivered'
            order_item.save()
            
            return redirect('list_orders')
        
        elif action == 'approve':
            self.get_refund_api_call(order_item, order_item_tracking)
            send_refund_success_notifcation(order_item.product_name, self.request.user)
            return redirect('list_orders')


# To update orders

class OrderUpdateView(ShopRequiredMixin, ReturnRefundAPIMixin, View):
    def get(self, request, *args, **kwargs):
        order_item_id = kwargs.get('id')
        orderItem  = get_object_or_404(OrderItem, id=order_item_id, product__created_by=self.request.user)
        if orderItem:
            return render(request, 'update_order.html', {'order_item': orderItem})
        else:
            return redirect('list_orders')
    
    def post(self, request, *args, **kwargs):
        order_item_id = request.POST.get('order_item_id')
        order_id = request.POST.get('order_id')
        is_paid = request.POST.get('is_paid')
        order_status = request.POST.get('order_status')
        action = request.POST.get('action', '')
                
        order_item = get_object_or_404(OrderItem, id=order_item_id, product__created_by=self.request.user)
        order_item.is_paid = is_paid  
        order_item.save()
                
        orderItemTracking = get_object_or_404(OrderItemTracking, order_item=order_item)  
        if order_status == 'delivered':
            orderItemTracking.status = 'delivered'
            orderItemTracking.is_delivered = True
        else:
            orderItemTracking.status = order_status
            orderItemTracking.is_delivered = False
            
        orderItemTracking.save()
        
        order = get_object_or_404(Order, order_id=order_id)
        payment_status = all(item.is_paid or item.order.is_cancelled for item in order.items.all())
        order.payment_status = 'completed' if payment_status else 'pending'
        order.save()
        
        messages.success(request, 'Order details updated successfully')
        
        order_item_tracking = get_object_or_404(OrderItemTracking, order_item=order_item)
        if action == 'reject':
            action_item = get_object_or_404(OrderItemAction, order_item_tracking=order_item_tracking)
            action_item.status = 'rejected'
            action_item.save()
            
            order_item_tracking.status = 'delivered'
            order_item.save()
            
            return redirect('list_orders')
        
        elif action == 'approve':
            self.get_refund_api_call(order_item, order_item_tracking)
            send_refund_success_notifcation(order_item.product_name, self.request.user)
            return redirect('list_orders')
        
        return redirect('list_orders')
            
            
# To view invoice
            
class InvoiceView(ShopRequiredMixin, TemplateView):
    template_name = 'invoice.html'
    
    def get(self, request, *args, **kwargs):
        order_id = kwargs.get('id')
        order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id)
        
        context = {
            'order': order,
            'order_items': order.items.all()
        }
        
        html_content = render_to_string(self.template_name, context)
        pdf = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="invoice_{order.id}.pdf"'
        
        return response
    

# To download invoice

class InvoiceDownloadView(ShopRequiredMixin, View):
    template_name = 'invoice.html'
    
    def get(self, request, *args, **kwargs):
        order_id = kwargs.get('id')
        order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id)
        
        context = {
            'order': order,
            'order_items': order.items.all()
        }
        
        html_content = render_to_string(self.template_name, context)
        pdf = HTML(string=html_content).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
        
        return response
    

# To view admin dashboard

class DashboardView(ShopRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    
    today = timezone.now()
    month = today.month
    year = today.year
    previous_day = today - timezone.timedelta(days=1)
    
    if today.month == 1:
        previous_month = 12
        previous_year = today.year - 1
    else:
        previous_month = today.month - 1
        previous_year = today.year
    
    def get(self, request, *args, **kwargs):
        sales_filter = request.GET.get('sales_filter', 'today') 
        revenue_filter = request.GET.get('revenue_filter', 'this_month')
        customer_filter = request.GET.get('customer_filter', 'this_year')
        
        report_filter = request.GET.get('report_filter', 'this_month')
        
        recent_filter = request.GET.get('recent_filter', 'today')
        
        topSelling_filter = request.GET.get('topSelling_filter', 'today')
        
        sales_data = self.get_sales_data(sales_filter)
        revenue_data = self.get_revenue_data(revenue_filter)
        customers_data = self.get_customers_data(customer_filter)
        
        report_data = self.get_chart_data(report_filter)
        
        recent_data = self.get_recent_data(recent_filter)
        
        topSelling_data = self.get_topSelling_data(topSelling_filter)
        
        context = {
            'sales_today_count': sales_data['count'],
            'percentage_sales_today': sales_data['percentage_change'],
            'sales_timeframe': sales_filter,
            'revenue_monthly': revenue_data['amount'],
            'percentage_revenue_monthly': revenue_data['percentage_change'],
            'revenue_timeframe': revenue_filter,
            'customers_yearly': customers_data['count'],
            'percentage_customers_yearly': customers_data['percentage_change'],
            'customer_timeframe': customer_filter,
            'report_data': report_data,
            'report_data_timeframe': report_filter,
            'recent_data': recent_data,
            'recent_timeframe': recent_filter,
            'topSelling_data': topSelling_data,
            'topSelling_timeframe': topSelling_filter
        }
        
        return render(request, self.template_name, context)
    
    def get_filtered_sales(self, filter_type):
        if filter_type == 'today':
            return OrderItem.objects.filter(order__order_time__date=self.today.date(), 
                                            product__created_by=self.request.user,
                                            order__delivery_confirmed=True,
                                            order__is_cancelled=False)
        elif filter_type == 'this_month':
            return OrderItem.objects.filter(order__order_time__year=self.year,
                                            order__order_time__month=self.month,
                                            product__created_by=self.request.user,
                                            order__delivery_confirmed=True,
                                            order__is_cancelled=False)
        elif filter_type == 'this_year':
            return OrderItem.objects.filter(order__order_time__year=self.year,
                                            product__created_by=self.request.user,
                                            order__delivery_confirmed=True,
                                            order__is_cancelled=False)
            
    def get_previous_filtered_sales(self, filter_type):
        if filter_type == 'today':
            return OrderItem.objects.filter(order__order_time__date=self.previous_day, 
                                            product__created_by=self.request.user,
                                            order__delivery_confirmed=True,
                                            order__is_cancelled=False)
        elif filter_type == 'this_month':
            return OrderItem.objects.filter(order__order_time__year=self.previous_year,
                                            order__order_time__month=self.previous_month,
                                            product__created_by=self.request.user,
                                            order__delivery_confirmed=True,
                                            order__is_cancelled=False)
        elif filter_type == 'this_year':
            return OrderItem.objects.filter(order__order_time__year=self.previous_year,
                                            product__created_by=self.request.user,
                                            order__delivery_confirmed=True,
                                            order__is_cancelled=False)
    
    def get_sales_data(self, filter_type):
        sales = self.get_filtered_sales(filter_type)
        
        sales_count = sales.count()
        previous_sales_count = self.get_previous_sales_count(filter_type)
        percentage_change = self.calculate_percentage_change(previous_sales_count, sales_count)
    
        return {'count': sales_count, 'percentage_change': percentage_change}
    
    def get_revenue_data(self, filter_type):
        sales = self.get_filtered_sales(filter_type)
        
        revenue_amount = sum(item.get_cost() for item in sales)
        previous_revenue_amount = self.get_revenue_amount(filter_type)
        percentage_change = self.calculate_percentage_change(previous_revenue_amount, revenue_amount)
        
        return {'amount': revenue_amount, 'percentage_change': percentage_change}
    
    def get_customers_data(self, filter_type):
        sales = self.get_filtered_sales(filter_type)
        
        customer_count = sales.values('order__user').distinct().count()
        previous_customer_count = self.get_customer_count(filter_type)
        percentage_change = self.calculate_percentage_change(previous_customer_count, customer_count)
        
        return {'count': customer_count, 'percentage_change': percentage_change}
    
    def get_previous_sales_count(self, filter_type):
        sales = self.get_previous_filtered_sales(filter_type)
        
        sales_count = sales.count()
        
        return sales_count
    
    def get_revenue_amount(self, filter_type):
        sales = self.get_previous_filtered_sales(filter_type)
        
        revenue_amount = sum(item.get_cost() for item in sales)
        
        return revenue_amount
       
    def get_customer_count(self, filter_type):
        sales = self.get_previous_filtered_sales(filter_type)
        
        customer_count = sales.values('order__user').distinct().count()
        
        return customer_count
    
    def calculate_percentage_change(self, previous_value, current_value):
        if previous_value == 0:
            return 100 if current_value > 0 else 0
        elif current_value == previous_value:
            return 100
        return round(((current_value - previous_value) / previous_value) * 100)
   
    def get_recent_data(self, filter_type):
        order_items = self.get_filtered_sales(filter_type)
        order_items = order_items.select_related('order').order_by('-order__created_at')
        
        return order_items
    
    def get_topSelling_data(self, filter_type):
        order_items = self.get_filtered_sales(filter_type)
        
        first_image_subquery = SKUImage.objects.filter(sku__product=OuterRef('product')).values('image')[:1]
        top_selling_products = (
            order_items.values('product', 'product_name', 'product_discounted_price')
            .annotate(total_quantity=Sum('quantity'), total_cost=Sum(F('quantity') * F('product_discounted_price')), 
                      first_image=Coalesce(Concat(V(settings.MEDIA_URL), Subquery(first_image_subquery), output_field=CharField()), None))
            .order_by('-total_quantity')[:5]
            )
        
        for product in top_selling_products:
            product_instance = Product.objects.get(id=product['product'])
            product['url'] = product_instance.get_url()
            
        return top_selling_products
    
    def get_chart_data(self, filter_type):
        if filter_type == 'this_month':
            report_data = self.get_monthly_chart_data()
            
            return report_data
            
        elif filter_type == 'this_year':
            report_data = self.get_yearly_chart_data()

            return report_data
    
    def get_monthly_chart_data(self):
        queryset = (
            OrderItem.objects.filter(
                order__order_time__year=self.year,
                order__order_time__month=self.month,
                product__created_by=self.request.user,
                order__delivery_confirmed=True,
                order__is_cancelled=False
            ).annotate(day=TruncDay('order__order_time')).values('day').annotate(sales_count=Count('id'),total_revenue=Sum('product_discounted_price')).order_by('day')
        )
        
        all_orders = (
            OrderItem.objects.filter(
                order__order_time__year=self.year,
                order__order_time__month=self.month,
                product__created_by=self.request.user,
                order__delivery_confirmed=True,
                order__is_cancelled=False
            ).annotate(day=TruncDay('order__order_time'))
            .values('order__user', 'day')
            .order_by('day')
        )
        
        unique_customers = set()
        customer_counts_by_day = {}
        
        for order in all_orders:
            customer = order['order__user']
            order_day = order['day']
            
            if customer not in unique_customers:
                unique_customers.add(customer)
                customer_counts_by_day[order_day] = customer_counts_by_day.get(order_day, 0) + 1

        revenue_scaling_factor = 1000
        
        chart_data = {
            'dates': [],
            'sales_counts': [],
            'scaled_revenues': [],
            'first_time_customers': []
        }

        for data in queryset:
            date = data['day'].strftime('%Y-%m-%d')
            chart_data['dates'].append(date)
            chart_data['sales_counts'].append(data['sales_count'])
            scaled_revenue = round((data['total_revenue'] or 0) / revenue_scaling_factor, 1)
            chart_data['scaled_revenues'].append(scaled_revenue)
            chart_data['first_time_customers'].append(customer_counts_by_day.get(data['day'], 0))
        
        return chart_data
    
    def get_yearly_chart_data(self):
        queryset = (
            OrderItem.objects.filter(
                order__order_time__year=self.year,
                product__created_by=self.request.user,
                order__delivery_confirmed=True,
                order__is_cancelled=False
            )
            .annotate(month=TruncMonth('order__order_time'))
            .values('month')
            .annotate(
                sales_count=Count('id'),
                total_revenue=Sum('product_discounted_price')
            )
            .order_by('month')
        )
        
        all_orders = (
            OrderItem.objects.filter(
                order__order_time__year=self.year,
                product__created_by=self.request.user,
                order__delivery_confirmed=True,
                order__is_cancelled=False
            )
            .annotate(month=TruncMonth('order__order_time'))
            .values('order__user', 'month')
            .order_by('month')
        )

        unique_customers = set()
        customer_counts_by_month = {}

        for order in all_orders:
            customer = order['order__user']
            order_month = order['month']
            
            if customer not in unique_customers:
                unique_customers.add(customer)
                customer_counts_by_month[order_month] = customer_counts_by_month.get(order_month, 0) + 1

        revenue_scaling_factor = 1000

        chart_data = {
            'dates': [],
            'sales_counts': [],
            'scaled_revenues': [],
            'first_time_customers': []
        }

        for data in queryset:
            month = data['month'].strftime('%Y-%m')
            chart_data['dates'].append(month)
            chart_data['sales_counts'].append(data['sales_count'])
            scaled_revenue = round((data['total_revenue'] or 0) / revenue_scaling_factor, 1)
            chart_data['scaled_revenues'].append(scaled_revenue)
            chart_data['first_time_customers'].append(customer_counts_by_month.get(data['month'], 0))
        
        return chart_data

    
    
    