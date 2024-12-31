from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView, DeleteView
from django.views import View
from shop_admin.mixins import ShopRequiredMixin
from products.models import ProductAttribute, ProductAttributeValue
from shop_admin.forms import AttributeForm, AttributeValueForm


# To list attributes     

class AttributeListView(ShopRequiredMixin, ListView):
    model = ProductAttribute
    template_name = 'list_attribute.html'
    context_object_name = 'attributes'


# To add variation names and variation values

class AddAttributeView(ShopRequiredMixin, View):
    template_name = 'add_attribute.html'
    success_url = reverse_lazy('add_attribute')

    def get(self, request, *args, **kwargs):
        attribute_form = AttributeForm()
        attribute_value_form = AttributeValueForm()
        return self.render_forms(attribute_form, attribute_value_form)

    def post(self, request, *args, **kwargs):
        if 'submit_attribute' in request.POST:
            attribute_form = AttributeForm(request.POST)
            attribute_value_form = AttributeValueForm()
            if attribute_form.is_valid():
                attribute_form.save()
                return HttpResponseRedirect(self.success_url)
        elif 'submit_attribute_value' in request.POST:
            attribute_value_form = AttributeValueForm(request.POST)
            attribute_form = AttributeForm()
            if attribute_value_form.is_valid():
                attribute_value_form.save()
                return HttpResponseRedirect(self.success_url)

        return self.render_forms(attribute_form, attribute_value_form)

    def render_forms(self, attribute_form, attribute_value_form):
        return render(self.request, self.template_name, {
            'attribute_form': attribute_form,
            'attribute_value_form': attribute_value_form
        })
        
         
# To update attribute names and values

class UpdateAttributeView(ShopRequiredMixin, UpdateView):
    model = ProductAttribute
    form_class = AttributeForm
    template_name = 'update_attribute.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attribute = self.object
        context['attribute'] = attribute
        context['attribute_form'] = AttributeForm(instance=attribute)
        context['attribute_values'] = attribute.product_type.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        attribute_value_id = request.POST.get('attribute_value_id')

        if 'submit_attribute' in request.POST:
            return self.update_variation_name(request)
        elif 'submit_attribute_value' in request.POST:
            return self.update_variation_value(request, attribute_value_id)
        elif 'delete_attribute_value' in request.POST:
            return self.delete_variation_value(request, attribute_value_id)

        return super().post(request, *args, **kwargs)
    
    def update_variation_name(self, request):
        form = self.get_form()
        if form.is_valid():
            form.save() 
            return redirect(self.get_success_url()) 
        else:
            self.handle_form_errors(request, form)

        return self.render_to_response(self.get_context_data(form=form))
    
    def update_variation_value(self, request, attribute_value_id):
        attribute_value = get_object_or_404(ProductAttributeValue, id=attribute_value_id)  
        new_value = request.POST.get('new_value')
        if ProductAttributeValue.objects.filter(value__iexact=new_value).exclude(id=attribute_value_id).exists():
            messages.error(request, "This Attribute already exists")
            return redirect(self.get_success_url())  
        attribute_value.value = new_value 
        attribute_value.save()
        return redirect(self.get_success_url())

    def delete_variation_value(self, request, attribute_value_id):  
        variation_value = get_object_or_404(ProductAttributeValue, id=attribute_value_id) 
        variation_value.delete()
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy('update_attribute', kwargs={'pk': self.object.pk})
    
    def handle_form_errors(self, request, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
        
        
# To delete an attribute

class DeleteAttributeView(ShopRequiredMixin, DeleteView):
    model = ProductAttribute
    template_name = 'list_attribute.html'
    success_url = reverse_lazy('list_attribute')

    def get_object(self, queryset=None):
        attribute_id = self.request.POST.get('attribute_id')
        variation = get_object_or_404(ProductAttribute, id=attribute_id)

        return variation
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "Attribute deleted successfully")
        return response

     

