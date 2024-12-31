from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DeleteView, TemplateView
from products.models import Category, SubcategoryVariation, SubcategoryAttribute
from shop_admin.forms import CategoryForm, SubcategoryVariationForm, SubcategoryAttributeForm
from shop_admin.mixins import ShopRequiredMixin


# To List categories

class CategoryListView(ShopRequiredMixin, ListView):
    model = Category
    template_name = "list_category.html"
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(parent__isnull=True)


# To create a category

class CategoryAddView(ShopRequiredMixin, TemplateView):
    template_name = 'add_category.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        action = self.request.GET.get('action', 'add_category')
        context['is_subcategory'] = action == 'add_subcategory'
        context['category_form'] = CategoryForm()
        context['subcategory_variation_form'] = SubcategoryVariationForm()
        context['subcategory_attribute_form'] = SubcategoryAttributeForm()
        return context

    def post(self, request, *args, **kwargs):
        category_form = CategoryForm(request.POST)
        subcategory_variation_form = SubcategoryVariationForm(request.POST)
        subcategory_attribute_form = SubcategoryAttributeForm(request.POST)
        
        is_subcategory = bool(category_form.data.get('parent'))
        print(is_subcategory)
        
        if category_form.is_valid():
            category = category_form.save(commit=False)
            
            if is_subcategory:
                category.save()
                
                if subcategory_variation_form.is_valid():
                    subcategory_variation = subcategory_variation_form.save(commit=False)
                    subcategory_variation.subcategory = category
                    subcategory_variation.save()
                    subcategory_variation_form.save_m2m()
                    
                if subcategory_attribute_form.is_valid():
                    subcategory_attribute = subcategory_attribute_form.save(commit=False)
                    subcategory_attribute.subcategory = category
                    subcategory_attribute.save()
                    subcategory_attribute_form.save_m2m()
                    
                messages.success(request, 'Subcategory has been added successfully')
                return redirect(f'{reverse("add_category")}?action=add_subcategory')
            else:
                category.save()
                messages.success(request, 'Category has been added successfully')
                return redirect('add_category')    
        else:
            print(f"Category form errors: {category_form.errors}")

        context = {
            'category_form': category_form,
            'subcategory_variation_form': subcategory_variation_form,
            'subcategory_attribute_form': subcategory_attribute_form
        }
        return self.render_to_response(context)
    

# To update a category

class CategoryUpdateView(ShopRequiredMixin, TemplateView):
    template_name = 'update_category.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = Category.objects.get(pk=self.kwargs['pk'])
        
        is_subcategory = category.parent is not None
        context['is_subcategory'] = is_subcategory
        
        context['category_form'] = CategoryForm(instance=category)
        context['subcategory_variation_form'] = SubcategoryVariationForm(instance=self.get_subcategory_variation(category))
        context['subcategory_attribute_form'] = SubcategoryAttributeForm(instance=self.get_subcategory_attribute(category))
        
        return context

    def get_subcategory_variation(self, category):
        try:
            return SubcategoryVariation.objects.get(subcategory=category)
        except SubcategoryVariation.DoesNotExist:
            return None
        
    def get_subcategory_attribute(self, category):
        try:
            return SubcategoryAttribute.objects.get(subcategory=category)
        except SubcategoryAttribute.DoesNotExist:
            return None

    def post(self, request, *args, **kwargs):
        category = Category.objects.get(pk=self.kwargs['pk'])

        category_form = CategoryForm(request.POST, instance=category)
        subcategory_variation_form = SubcategoryVariationForm(request.POST, instance=self.get_subcategory_variation(category))
        subcategory_attribute_form = SubcategoryAttributeForm(request.POST, instance=self.get_subcategory_attribute(category))
        
        is_subcategory = category.parent is not None

        if category_form.is_valid():
            category = category_form.save()
            
            if is_subcategory:
                if subcategory_variation_form.is_valid():
                    subcategory_variation = subcategory_variation_form.save(commit=False)
                    subcategory_variation.subcategory = category
                    subcategory_variation.save()
                    subcategory_variation_form.save_m2m()
                
                if subcategory_attribute_form.is_valid():
                    subcategory_attribute = subcategory_attribute_form.save(commit=False)
                    subcategory_attribute.subcategory = category
                    subcategory_attribute.save()
                    subcategory_attribute_form.save_m2m()
                
                messages.success(request, 'Subcategory has been updated successfully')
            else:
                messages.success(request, 'Category has been updated successfully')

            return redirect('list_category')
        else:
            print(f"Category form errors: {category_form.errors}")  

        context = {
            'category_form': category_form,
            'subcategory_variation_form': subcategory_variation_form,
            'subcategory_attribute_form': subcategory_attribute_form
        }
        return self.render_to_response(context)
    

# To delete a category

class CategoryDeleteView(ShopRequiredMixin, DeleteView):
    model = Category
    template_name = 'list_category.html'
    success_url = reverse_lazy('list_category')

    def get_object(self, queryset=None):
        category_id = self.request.POST.get('category_id')
        return get_object_or_404(Category, id=category_id)
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "Category deleted successfully")
        return response


    