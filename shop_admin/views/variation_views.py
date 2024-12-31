from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView, DeleteView
from django.views import View
from shop_admin.mixins import ShopRequiredMixin
from products.models import VariationValue, VariationName
from shop_admin.forms import VariationForm, VariationValueForm


# To list variations     

class VariationListView(ShopRequiredMixin, ListView):
    model = VariationName
    template_name = 'list_variation.html'
    context_object_name = 'variations'


# To add variation names and variation values

class AddVariationView(ShopRequiredMixin, View):
    template_name = 'add_variation.html'
    success_url = reverse_lazy('add_variation')

    def get(self, request, *args, **kwargs):
        variation_form = VariationForm()
        variation_value_form = VariationValueForm()
        return self.render_forms(variation_form, variation_value_form)

    def post(self, request, *args, **kwargs):
        variation_form = VariationForm()
        variation_value_form = VariationValueForm()
        
        if 'submit_variation' in request.POST:
            variation_form = VariationForm(request.POST)
            if variation_form.is_valid():
                variation_form.save()
                return HttpResponseRedirect(self.success_url)
        elif 'submit_variation_value' in request.POST:
            variation_value_form = VariationValueForm(request.POST)
            if variation_value_form.is_valid():
                variation_value_form.save()
                return HttpResponseRedirect(self.success_url)

        return self.render_forms(variation_form, variation_value_form)

    def render_forms(self, variation_form, variation_value_form):
        return render(self.request, self.template_name, {
            'variation_form': variation_form,
            'variation_value_form': variation_value_form
        })
        
        
# To update variation names and values

class UpdateVariationView(ShopRequiredMixin, UpdateView):
    model = VariationName
    form_class = VariationForm
    template_name = 'update_variation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        variation = self.object
        context['variation'] = variation
        context['variation_form'] = VariationForm(instance=variation)
        context['variation_values'] = variation.values.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        variation_value_id = request.POST.get('variation_value_id')

        if 'submit_variation' in request.POST:
            return self.update_variation_name(request)
        elif 'submit_variation_value' in request.POST:
            return self.update_variation_value(request, variation_value_id)
        elif 'delete_variation_value' in request.POST:
            return self.delete_variation_value(request, variation_value_id)

        return super().post(request, *args, **kwargs)
    
    def update_variation_name(self, request):
        form = self.get_form()
        if form.is_valid():
            form.save() 
            return redirect(self.get_success_url()) 
        else:
            self.handle_form_errors(request, form)

        return self.render_to_response(self.get_context_data(form=form))
    
    def update_variation_value(self, request, variation_value_id):
        variation_value = get_object_or_404(VariationValue, id=variation_value_id)  
        new_value = request.POST.get('new_value')
        if VariationValue.objects.filter(value__iexact=new_value).exclude(id=variation_value_id).exists():
            messages.error(request, "This variation value already exists")
            return redirect(self.get_success_url())  
        variation_value.value = new_value 
        variation_value.save()
        return redirect(self.get_success_url())

    def delete_variation_value(self, request, variation_value_id):  
        variation_value = get_object_or_404(VariationValue, id=variation_value_id) 
        variation_value.delete()
        return redirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse_lazy('update_variation', kwargs={'pk': self.object.pk})
    
    def handle_form_errors(self, request, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
   

# To delete an variation

class DeleteVariationView(ShopRequiredMixin, DeleteView):
    model = VariationName
    template_name = 'list_variation.html'
    success_url = reverse_lazy('list_variation')

    def get_object(self, queryset=None):
        variation_id = self.request.POST.get('variation_id')
        variation = get_object_or_404(VariationName, id=variation_id)

        return variation
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "variation deleted successfully")
        return response

     