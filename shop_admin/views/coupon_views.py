from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from cart.models import Coupon
from shop_admin.forms import CouponForm
from shop_admin.mixins import ShopRequiredMixin


# To list coupons

class CouponListView(ShopRequiredMixin, ListView):
    model = Coupon
    template_name = 'list_coupon.html'
    context_object_name = 'coupons'

    def get_queryset(self):
        return Coupon.objects.filter(created_by=self.request.user)
    
    
# To add coupons

class CouponAddView(ShopRequiredMixin, CreateView):
    template_name = 'add_coupon.html'
    form_class = CouponForm
    success_url = reverse_lazy('add_coupon')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user 
        return kwargs
    
    def form_valid(self, form):
        coupon = form.save(commit=False)
        coupon.created_by = self.request.user 
        coupon.save()
        messages.success(self.request, 'Coupon has been added successfully')
        
        return super().form_valid(form)


# To update a coupon

class UpdateCouponView(ShopRequiredMixin, UpdateView):
    template_name = 'update_coupon.html'
    form_class = CouponForm
    success_url = reverse_lazy('list_coupon')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user 
        return kwargs

    def get_queryset(self):
        return Coupon.objects.filter(created_by=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Coupon has been updated successfully')
        return response


# To delete a coupon

class DeleteCouponView(ShopRequiredMixin, DeleteView):
    model = Coupon
    template_name = 'list_coupon.html'
    success_url = reverse_lazy('list_coupon')

    def get_object(self, queryset=None):
        coupon_id = self.request.POST.get('coupon_id')
        return get_object_or_404(Coupon, id=coupon_id)
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, 'Coupon has been deleted successfully')
        return response


    