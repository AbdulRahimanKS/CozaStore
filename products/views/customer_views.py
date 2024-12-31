import json
from django.db.models.base import Model as Model
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, ListView
from shop_admin.models import CustomUser, UserProfile
from products.models import CheckOutAddresses, Product, Rating, WishlistItem
from shop_admin.forms import ProfileForm, ChangePasswordForm
from products.forms import CheckoutAddressesForm, RatingForm
from products.utils import calculate_product_ratings, get_products
from django.template.loader import render_to_string
from django.http import JsonResponse
from firebase_admin import messaging
from shop_admin.mixins import UserRequiredMixin


PROFILE_TEMPLATE  = 'customer_profile.html'

# To update profile and change password

class CustomerProfileView(UserRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id=request.user.id)
        form1 = ProfileForm(instance=user)
        form2 = ChangePasswordForm()
        form3 = CheckoutAddressesForm()
        addresses = CheckOutAddresses.objects.filter(user=user).order_by('-default', '-id')
        user_profile = getattr(user, 'userprofile', None)

        return self.render_profile(request, form1, form2, form3, user, user_profile, addresses)
    
    def post(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id=request.user.id)
        form1 = ProfileForm(request.POST, request.FILES, instance=user)
        form2 = ChangePasswordForm(request.POST, user=user)
        form3 = CheckoutAddressesForm(request.POST)
        addresses = CheckOutAddresses.objects.filter(user=user).order_by('-default', 'id')
        user_profile, created = UserProfile.objects.get_or_create(user=user)

        if 'profile_update' in request.POST:
            if form1.is_valid():
                self.update_user_and_profile(request, form1, user_profile)
                messages.success(request, 'Profile details updated successfully')
                return redirect('profile')
            else:
                self.handle_form_errors(request, form1)

        elif 'change_password' in request.POST:
            if form2.is_valid():
                self.change_password(request, form2)
                messages.success(request, 'Password updated successfully')
                return redirect('profile')
            else:
                self.handle_form_errors(request, form2)
                return redirect('profile')
            
        elif 'add_address' in request.POST:
            if form3.is_valid():
                address = form3.save(commit=False)
                address.user = user
                if not CheckOutAddresses.objects.filter(user=user).exists():
                    address.default = True
                address.save()
                messages.success(request, 'Address added successfully')
                return redirect('profile')
            else:
                self.handle_form_errors(request, form3)

        return self.render_profile(request, form1, form2, form3, user, user_profile, addresses)

    def render_profile(self, request, form1, form2, form3, user, user_profile, addresses):
        return render(request, PROFILE_TEMPLATE, {
            'form': form1,
            'ChangePasswordForm': form2,
            'CheckoutAddressesForm': form3,
            'user': user,
            'user_profile': user_profile,
            'addresses': addresses
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
                
                
# To check any default address exists

class CheckDefaultAddressView(UserRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        default_address_exists = CheckOutAddresses.objects.filter(user=self.request.user, default=True).exists()
        return JsonResponse({'exists': default_address_exists})
                
                
# To delete addresses

class AddressDeleteView(UserRequiredMixin, DeleteView):
    model = CheckOutAddresses
    template_name = 'customer_profile.html'
    success_url = reverse_lazy('profile')
    
    def get(self, request, *args, **kwargs):
        user = CustomUser.objects.get(id=request.user.id)
        form1 = ProfileForm(instance=user)
        form2 = ChangePasswordForm()
        form3 = CheckoutAddressesForm()
        addresses = CheckOutAddresses.objects.filter(user=user).order_by('-default', '-id')
        user_profile = getattr(user, 'userprofile', None)

        return render(request, PROFILE_TEMPLATE, {
            'form': form1,
            'ChangePasswordForm': form2,
            'CheckoutAddressesForm': form3,
            'user': user,
            'user_profile': user_profile,
            'addresses': addresses
        })
    
    def get_object(self, queryset=None):
        address_id = self.request.POST.get('address_id')
        return get_object_or_404(CheckOutAddresses, id=address_id)
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        address = self.get_object()
        
        if address.default:
            last_address = CheckOutAddresses.objects.filter(user=request.user).exclude(id=address.id).order_by('-created_at').first()
            if last_address:
                last_address.default = True
                last_address.save()
                
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "Address deleted successfully")
        return response
    
    
# To update addresses
    
class AddressFormView(UserRequiredMixin, View):
    def get(self, request, pk): 
        address = get_object_or_404(CheckOutAddresses, id=pk, user=request.user)
        form = CheckoutAddressesForm(instance=address)
        form_html = render_to_string('address_update_form.html', {'form': form, 'address': address}, request=request)
        return JsonResponse({'form_html': form_html}, safe=False)
    
    def post(self, request, pk):
        address = get_object_or_404(CheckOutAddresses, id=pk, user=request.user)
        form = CheckoutAddressesForm(request.POST, instance=address)
        
        if form.is_valid():
            updated_address = form.save(commit=False)
            updated_address.user = self.request.user
            
            remaining_address_count = CheckOutAddresses.objects.filter(user=request.user).count()

            if remaining_address_count == 1:
                updated_address.default = True
            else:
                updated_address.default = updated_address.default 

            updated_address.save()
            return JsonResponse({'success': True, 'message': 'Address updated successfully'})
        else:
            form_html = render_to_string('address_update_form.html', {'form': form, 'address': address}, request=request)
            return JsonResponse({'success': False, 'form_html': form_html})
    
    
# To create or update rating of a product

class RatingManageView(View):
    def post(self, request, subcategory_slug, product_slug, *args, **kwargs):
        product = get_object_or_404(Product, slug=product_slug, subcategory__slug=subcategory_slug)
        
        form = RatingForm(request.POST)
        try:
            rating = Rating.objects.get(product=product, user=request.user)
            form = RatingForm(request.POST, instance=rating)
        except Rating.DoesNotExist:
            form = RatingForm(request.POST)

        if form.is_valid():
            rating = form.save(commit=False)
            rating.product = product
            rating.user = request.user
            rating.save()
            messages.success(request, 'Your rating has been successfully submitted!')
            return redirect('product_detail', subcategory_slug=subcategory_slug, product_slug=product_slug)
        else:
            messages.error(request, 'Rating is required')
            
        return redirect('product_detail', subcategory_slug=subcategory_slug, product_slug=product_slug)

       
# To show product reviews

class ProductReviewListView(ListView):
    model = Rating
    template_name = 'product_reviews.html'
    context_object_name = 'reviews'
    paginate_by = 8

    def get_queryset(self):
        self.product = Product.objects.get(subcategory__slug=self.kwargs['subcategory_slug'], slug=self.kwargs['product_slug'])
        queryset = Rating.objects.filter(product=self.product).exclude(review__isnull=True).exclude(review__exact='').order_by('-created_at')
        
        sort_option = self.request.GET.get('sort', 'most_recent')

        if sort_option == 'most_recent':
            queryset = queryset.order_by('-created_at')
        elif sort_option == 'positive_first':
            queryset = queryset.order_by('-rating')
        elif sort_option == 'negative_first':
            queryset = queryset.order_by('rating')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['product'] = self.product
        ratings_data = calculate_product_ratings(self.product)
        context['average_rating'] = ratings_data['average_rating']
        context['total_ratings'] = ratings_data['total_ratings']
        context['total_reviews'] = ratings_data['total_reviews']
        context['star_range'] = [5, 4, 3, 2, 1]
        context['ratings_data'] = ratings_data['ratings_data']
        
        return context
    
    
# To add and delete products in wishlist
    
class AddWishlistView(View):
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'message': 'User not authenticated', 'status': 'error'}, status=403)

        data = json.loads(request.body)
        product_id = data.get('product_id')
        product = get_object_or_404(Product, id=product_id)

        wishlist_item, created = WishlistItem.objects.get_or_create(user=self.request.user, product=product)
        wishlist_count = WishlistItem.objects.filter(user=self.request.user).count()

        if created:
            return JsonResponse({'message': 'Product added to wishlist!', 'status': 'success', 'wishlist_count': wishlist_count}, status=200)
        else:
            wishlist_item.delete()
            wishlist_count = WishlistItem.objects.filter(user=self.request.user).count()
            return JsonResponse({'message': 'Product removed from wishlist!', 'status': 'removed', 'wishlist_count': wishlist_count}, status=200)
    
    
# To view wishlist page

class WishlistView(ListView):
    model = WishlistItem
    template_name = 'wishlist.html'
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return WishlistItem.objects.filter(user=self.request.user)
        return WishlistItem.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wishlist_items = self.get_queryset()
        
        products = [item.product for item in wishlist_items]
        context['products'] = get_products(products)
        return context
    

# To delete wishlist item

class DeleteWishlistItemView(DeleteView):
    model = WishlistItem
    template_name = 'wishlist.html'
    success_url = reverse_lazy('wishlist_view')
    
    def get_object(self, queryset=None):
        product_id = self.kwargs['pk']
        return WishlistItem.objects.get(user=self.request.user, product_id=product_id)
    

# To save fcm token

class FCMTokenCreateView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        token = data.get('token')
        
        if token:
            user_profile = get_object_or_404(UserProfile, user=self.request.user)
            user_profile.fcm_token = token
            user_profile.save()
            
            return JsonResponse({"status": "success"})
        return JsonResponse({"error": "Invalid request"}, status=400)

        
# To subscribe to a topic

class SubscribeToTopicView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        token = data.get('token')
        topic = data.get('topic')
        
        if token and topic:
            response = messaging.subscribe_to_topic([token], topic)
            
            result = {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'errors': [str(error) for error in response.errors]  
            }
        
            return JsonResponse({'success': True, 'response': result})
        JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

