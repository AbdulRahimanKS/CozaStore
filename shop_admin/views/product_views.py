from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from products.models import Product, Category, ProductAttribute, ProductAttributeValue, SubcategoryAttribute
from django.urls import reverse_lazy
from shop_admin.forms import ProductForm
from django.urls import reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from shop_admin.mixins import ShopRequiredMixin
from django.views.decorators.http import require_GET
from shop_admin.utils import send_new_product_notification


# To List products

class ProductListView(ShopRequiredMixin, ListView):
    model = Product
    template_name = "list_product.html"
    context_object_name = 'products'
    
    def get_queryset(self):
        return Product.objects.filter(created_by=self.request.user)
        
        
# To create a product

class ProductAddView(ShopRequiredMixin, CreateView):
    form_class = ProductForm
    template_name = 'add_product.html'

    def form_valid(self, form):
        subcategory_id = self.request.POST.get('subcategory')

        product_attributes = {}
        for key, value in self.request.POST.items():
            if key.startswith('product_attributes['):
                attribute_id = key.split('[')[1].split(']')[0]
                if value:
                    product_attributes[attribute_id] = value
        
        product  = form.save(commit=False) 
        product.created_by = self.request.user
        
        if subcategory_id:
            subcategory = Category.objects.get(id=subcategory_id)
            product.subcategory = subcategory
        
        product.save()
        
        attribute_value_ids = list(product_attributes.values())
        attribute_values = ProductAttributeValue.objects.filter(id__in=attribute_value_ids)
        product.product_attribute.set(attribute_values)
        
        send_new_product_notification(product.name)

        messages.success(self.request, 'Product has been added successfully')
        
        return redirect(reverse('add_sku', kwargs={'product_id': product.id}))


# To manage ajax request for returning subcategories

@require_GET
def get_subcategories(request, category_id):
    subcategories = Category.objects.filter(parent_id=category_id).order_by('name')
    data = {
        'subcategories': list(subcategories.values('id', 'name'))
    }
    return JsonResponse(data)


# To manage ajax request for returning product attributes

@require_GET
def get_attributes(request, subcategory_id):
    try:
        subcategory_attributes = SubcategoryAttribute.objects.get(subcategory_id=subcategory_id)
        attributes = subcategory_attributes.attribute.all() 
        data = {
            'attributes': [
                {
                    'id': attribute.id,
                    'name': attribute.name,
                    'values': [
                        {
                            'id': value.id,
                            'name': value.value
                        } for value in ProductAttributeValue.objects.filter(product_attribute=attribute)
                    ]
                } for attribute in attributes
            ]
        }
        return JsonResponse(data)
    except SubcategoryAttribute.DoesNotExist:
        return JsonResponse({'attributes': []})


# To update a product

class ProductUpdateView(ShopRequiredMixin, UpdateView):
    form_class = ProductForm
    template_name = 'update_product.html'
    success_url = reverse_lazy('list_product')

    def get_queryset(self):
        return Product.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        subcategory = product.subcategory
        
        if subcategory:
            subcategory_attributes = SubcategoryAttribute.objects.filter(subcategory=subcategory).prefetch_related('attribute')
            attributes = set()
            for sub_attr in subcategory_attributes:
                attributes.update(sub_attr.attribute.all())
        else:
            attributes = ProductAttribute.objects.none()

        product_attributes = product.product_attribute.all()

        context['product_attributes'] = product_attributes
        context['all_attributes'] = attributes
        
        context['categories'] = Category.objects.filter(parent__isnull=True)
        context['subcategories'] = Category.objects.filter(parent=product.category) if product.category else []
        context['selected_subcategory'] = product.subcategory.id if product.subcategory else None

        return context

    def form_valid(self, form):
        subcategory_id = self.request.POST.get('subcategory')
        self.object = form.save(commit=False)

        if subcategory_id:
            subcategory = Category.objects.get(id=subcategory_id)
            self.object.subcategory = subcategory

        self.object.save()
        
        product_attributes = {}
        for key, value in self.request.POST.items():
            if key.startswith('product_attributes['):
                attribute_id = key.split('[')[1].split(']')[0]
                if value:
                    product_attributes[attribute_id] = value
                    
        attribute_value_ids = list(product_attributes.values())
        attribute_values = ProductAttributeValue.objects.filter(id__in=attribute_value_ids)
        self.object.product_attribute.set(attribute_values)

        messages.success(self.request, 'Product has been updated successfully')

        return redirect(self.get_success_url())
    

# To delete a product

class ProductDeleteView(ShopRequiredMixin, DeleteView):
    model = Product
    template_name = 'list_product.html'
    success_url = reverse_lazy('list_product')

    def get_object(self, queryset=None):
        product_id = self.request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
    
        if product.created_by != self.request.user:
            raise PermissionDenied("You do not have permission to delete this product")

        return product
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "Product deleted successfully")
        return response

