from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, TemplateView
from products.models import Product, SKU, SKUImage, SubcategoryVariation, VariationValue, VariationName, SKUCombination
from django.urls import reverse
from django.views import View
from shop_admin.mixins import ShopRequiredMixin
from shop_admin.forms import SKUForm


# To List SKUs of a product

class SKUListView(ShopRequiredMixin, ListView):
    template_name = "list_sku.html"

    def get_product(self):
        product_id = self.kwargs.get('product_id')
        return get_object_or_404(Product, id=product_id, created_by=self.request.user)

    def get_queryset(self):
        product = self.get_product()
        return SKU.objects.filter(product=product).prefetch_related('combinations__variation_name', 'combinations__variation_value')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_product()

        skus = self.get_queryset()

        context['skus'] = skus
        context['product_id'] = product.id
        return context
    

# Add SKU of a product

class AddSKUView(ShopRequiredMixin, TemplateView):
    template_name = 'add_sku.html'

    def get_product(self):
        product_id = self.kwargs.get('product_id')
        return get_object_or_404(Product, id=product_id, created_by=self.request.user)
    
    def get_variations_for_subcategory(self, subcategory):
        subcategory_variations = SubcategoryVariation.objects.filter(subcategory=subcategory).prefetch_related('variation__values')
        variations = {}
        for subcategory_variation in subcategory_variations:
            for variation in subcategory_variation.variation.all():
                variations[variation.name] = variation.values.all()

        return variations
    
    def get(self, request, *args, **kwargs):
        product = self.get_product()
        variations = self.get_variations_for_subcategory(product.subcategory)
        form = SKUForm()
        return self.render_form(form, product, variations)
    
    def render_form(self, form, product, variations):
        return render(self.request, self.template_name, {
            'form': form,
            'product': product,
            'variations': variations
        })

    def post(self, request, *args, **kwargs):
        product = self.get_product()
        variations = self.get_variations_for_subcategory(product.subcategory)
        form = SKUForm(request.POST)
        
        if form.is_valid():
            sku = form.save(commit=False)
            sku.product = product
            
            variation_combinations = []
            
            color_value = request.POST.get('color_value')
            if color_value:
                color_variation, _  = VariationName.objects.get_or_create(name='Color')
                color_variation_value, _  = VariationValue.objects.get_or_create(value=color_value, variation=color_variation)
                variation_combinations.append((color_variation, color_variation_value))

            for variation_name, variation_values in variations.items():
                variation_value_id = request.POST.get(f'variation_{variation_name}')
                if variation_value_id:
                    variation_name_obj = VariationName.objects.get(name=variation_name)
                    variation_value_obj = VariationValue.objects.get(id=variation_value_id)
                    variation_combinations.append((variation_name_obj, variation_value_obj))
    
            existing_sku = SKU.objects.filter(product=product).prefetch_related('combinations')
            matching_skus = []
            for sku_obj in existing_sku:
                sku_combination = sku_obj.combinations.all()
                if len(sku_combination) == len(variation_combinations):
                    match = all(
                        any(comb.variation_name == var_name and comb.variation_value == var_value for comb in sku_combination)
                        for var_name, var_value in variation_combinations
                    )
                    if match:
                        matching_skus.append(sku_obj)

            if matching_skus:
                messages.error(request, "An SKU with the same attributes already exists")
                return self.render_form(form, product, variations)

            sku.save()
            for var_name, var_value in variation_combinations:
                SKUCombination.objects.create(sku=sku, variation_name=var_name, variation_value=var_value)

            image_files = [
                self.request.FILES.get('image1'),
                self.request.FILES.get('image2'),
                self.request.FILES.get('image3')
            ]
            
            for image in image_files:
                print(image)
                SKUImage.objects.create(sku=sku, image=image)
                
            product.sku_status = True
            product.save()
                        
            messages.success(request, "SKU added successfully")
            return redirect(reverse('list_sku', kwargs={'product_id': product.id}))

        return self.render_form(form, product, variations)


# To update SKU of a product 

class UpdateSKUView(ShopRequiredMixin, TemplateView):
    template_name = 'update_sku.html'

    def get_product(self):
        product_id = self.kwargs.get('product_id')
        return get_object_or_404(Product, id=product_id, created_by=self.request.user)

    def get_sku(self):
        sku_id = self.kwargs.get('sku_id')
        return get_object_or_404(SKU, id=sku_id, product__created_by=self.request.user)

    def get_subcategory_variations(self, product):
        subcategory = product.subcategory
        subcategory_variations = SubcategoryVariation.objects.filter(subcategory=subcategory).prefetch_related('variation__values')
        variations = {}
        for subcategory_variation in subcategory_variations:
            for variation in subcategory_variation.variation.all():
                variations[variation.name] = variation.values.all()
        return variations
    
    def get_selected_variations(self, sku):
        combinations = SKUCombination.objects.filter(sku=sku)
        selected_variations = {}
        
        for combination in combinations:
            selected_variations[combination.variation_name.name] = combination.variation_value.value

        return selected_variations
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = self.get_product()
        sku = self.get_sku()
        form = SKUForm(instance=sku)
        existing_images = sku.images.all()
        variations = self.get_subcategory_variations(product)
        selected_variations = self.get_selected_variations(sku)
        context['form'] = form
        context['existing_images'] = existing_images
        context['variations'] = variations
        context['selected_variations'] = selected_variations
        context['product'] = product

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context) 

    def post(self, request, *args, **kwargs):
        product = self.get_product()
        sku = self.get_sku()
        variations = self.get_subcategory_variations(product)
        form = SKUForm(request.POST, instance=sku)
        
        if form.is_valid():
            sku = form.save(commit=False)
            sku.product = product
            
            variation_combinations = []
            
            color_value = request.POST.get('color_value')
            if color_value:
                color_variation, _  = VariationName.objects.get_or_create(name='Color')
                color_variation_value, _  = VariationValue.objects.get_or_create(value=color_value, variation=color_variation)
                variation_combinations.append((color_variation, color_variation_value))

            for variation_name, variation_values in variations.items():
                variation_value_id = request.POST.get(f'variation_{variation_name}')
                if variation_value_id:
                    variation_name_obj = VariationName.objects.get(name=variation_name)
                    variation_value_obj = VariationValue.objects.get(id=variation_value_id)
                    variation_combinations.append((variation_name_obj, variation_value_obj))

            existing_sku = SKU.objects.filter(product=product).prefetch_related('combinations')
            matching_skus = []
            
            for sku_obj in existing_sku:
                sku_combination = sku_obj.combinations.all()
                if len(sku_combination) == len(variation_combinations):
                    match = all(
                        any(comb.variation_name == var_name and comb.variation_value == var_value for comb in sku_combination)
                        for var_name, var_value in variation_combinations
                    )
                    if match:
                        matching_skus.append(sku_obj)
            
            if matching_skus and sku not in matching_skus:
                messages.error(request, "An SKU with the same attributes already exists")
                return render(request, self.template_name, self.get_context_data(form=form))
            
            sku.save()
            
            sku.combinations.all().delete()
            for var_name, var_value in variation_combinations:
                SKUCombination.objects.get_or_create(sku=sku, variation_name=var_name, variation_value=var_value)

            image_files = [
                self.request.FILES.get('image1'),
                self.request.FILES.get('image2'),
                self.request.FILES.get('image3')
            ]

            existing_images = list(sku.images.all())
            
            for i, image_file in enumerate(image_files):
                if image_file:
                    if i < len(existing_images):
                        image = existing_images[i]
                        image.image = image_file
                        image.save()
                    else:
                        SKUImage.objects.create(sku=sku, image=image_file)

            for image in existing_images[len(image_files):]:
                image.delete()

            messages.success(request, "SKU updated successfully")
            return redirect(reverse('list_sku', kwargs={'product_id': product.id}))
        
        return render(request, self.template_name, self.get_context_data(form=form))


# To delete an SKU

class DeleteSKUView(ShopRequiredMixin, View):
    def get_product(self):
        product_id = self.kwargs.get('product_id')
        return get_object_or_404(Product, id=product_id, created_by=self.request.user)

    def get_sku(self):
        sku_id = self.kwargs.get('sku_id')
        return get_object_or_404(SKU, id=sku_id, product__created_by=self.request.user)

    def post(self, request, *args, **kwargs):
        product = self.get_product()
        sku = self.get_sku()

        if sku.product.created_by == request.user:
            sku.delete()
            messages.success(request, "SKU deleted successfully")

        if not SKU.objects.filter(product=product).exists():
                product.sku_status = False
                product.save()
                messages.success(request, "No remaining SKUs. Product SKU status updated to inactive")

        return redirect(reverse('list_sku', kwargs={'product_id': product.id}))
    

