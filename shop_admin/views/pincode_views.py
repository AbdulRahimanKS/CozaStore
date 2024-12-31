from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from shop_admin.mixins import ShopRequiredMixin
from shop_admin.models import PinCode
from shop_admin.forms import PinCodeForm


# TO list pin codes

class PinCodeListView(ShopRequiredMixin, ListView):
    model = 'PinCode'
    template_name  = 'list_pincode.html'
    context_object_name = 'pincodes'

    def get_queryset(self):
        return PinCode.objects.filter(created_by=self.request.user)
    

# To create a pin code

class PinCodeAddView(ShopRequiredMixin, CreateView):
    template_name = 'add_pincode.html'
    form_class = PinCodeForm
    success_url = reverse_lazy('add_pincode')

    def form_valid(self, form):
        user = form.save(commit=False)
        
        user.created_by = self.request.user
        user.save()
        messages.success(self.request, 'Pincode has been added successfully')

        return super().form_valid(form)
    

# To update a pin code

class PinCodeUpdateView(ShopRequiredMixin, UpdateView):
    template_name = 'update_pincode.html'
    form_class = PinCodeForm
    success_url = reverse_lazy('list_pincode')

    def get_queryset(self):
        return PinCode.objects.filter(created_by=self.request.user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Pincode has been updated successfully')
        return response


# To delete a pin code

class PinCodeDeleteView(ShopRequiredMixin, DeleteView):
    model = PinCode
    template_name = 'list_pincode.html'
    success_url = reverse_lazy('list_pincode')

    def get_object(self, queryset=None):
        pincode_id = self.request.POST.get('pincode_id')
        return get_object_or_404(PinCode, id=pincode_id)
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, 'Pincode has been deleted successfully')
        return response

