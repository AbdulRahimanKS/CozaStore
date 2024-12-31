from django.shortcuts import redirect, render
from django.views import View
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from .forms import LoginForm, ForgotPasswordForm, SetPasswordForm, RegisterForm
from django.contrib.auth import login
from django.contrib import messages
from shop_admin.models import CustomUser
from cart.models import Cart, CartItem
from .utils import send_password_reset_email
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.models import Group
from django.contrib.auth import logout


# Authentication using email and password

class LoginView(FormView):
    template_name = 'login.html'
    form_class = LoginForm
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        user = form.user
        login(self.request, user)
        
        if user.user_type == 'Customer':
            self.transfer_cart_items_to_user(user)

        if user.is_superuser:
            return redirect('/admin/')
        elif user.groups.filter(name='Shop').exists():
            return redirect('dashboard')
        elif user.groups.filter(name='Customer').exists():
            return redirect('index')
        else:
            return super().form_valid(form)
        
    def form_invalid(self, form):
        messages.error(self.request, "Invalid email or password")
        return super().form_invalid(form)
    
    def transfer_cart_items_to_user(self, user):
        session_cart_id = self.request.session.get('cart_id')
        
        if session_cart_id:
            session_cart = Cart.objects.get(id=session_cart_id)
            user_cart, created = Cart.objects.get_or_create(user=user)
            for cart_item in CartItem.objects.filter(cart=session_cart):
                existing_cart_item = CartItem.objects.filter(cart=user_cart, product=cart_item.product, sku=cart_item.sku).first()
                
                if existing_cart_item:
                    existing_cart_item.quantity += cart_item.quantity
                    existing_cart_item.save()
                else:
                    cart_item.pk = None
                    cart_item.cart = user_cart
                    cart_item.save()

            session_cart.delete()
            del self.request.session['cart_id']
            
            
# Create user account

class RegisterView(FormView):
    template_name = 'register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save()

        country_code = self.request.POST.get('countryCode', '')
        user.countryCode = country_code
        user.save()

        user_type = form.cleaned_data['user_type']
        group, created = Group.objects.get_or_create(name=user_type)
        user.groups.add(group)

        messages.success(self.request, 'Registration successful. Please login')

        return super().form_valid(form)


# Sending email to reset password

class ForgotPasswordView(FormView):
    template_name = 'forgot_password.html'
    form_class = ForgotPasswordForm
    success_url = reverse_lazy('forgot_pwd')
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            messages.error(self.request, "No user with this email address")
            return self.form_invalid(form)
            
        if send_password_reset_email(user, self.request):
            messages.success(self.request, "Password reset email sent")
        else:
            messages.error(self.request, "Error sending email")
            return self.form_invalid(form)    
        
        return super().form_valid(form)
    

# Reset password

class ResetPasswordView(FormView):
    template_name = 'reset_password.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        self.uidb64 = kwargs.get('uidb64')
        self.token = kwargs.get('token')
        self.user = self.get_user()
        if self.user is None or not self.user.token == self.token:
            messages.error(request, "The link is invalid or has expired")
            return render(request, 'link_expired.html')
        
        if CustomUser.objects.filter(
            security_code_expiration__lt=timezone.now()
        ).update(security_code=None, security_code_expiration=None):
        
            if CustomUser.objects.filter(
                token_expiration__lt=timezone.now()
            ).update(token=None, token_expiration=None):
                
                return render(request, 'link_expired.html')

        return super().dispatch(request, *args, **kwargs)

    def get_user(self):
        try:
            uid = force_str(urlsafe_base64_decode(self.uidb64))
            return CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return None
        
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def form_valid(self, form):
        new_password = form.cleaned_data['new_password']
        self.user.set_password(new_password)
        self.user.token = None
        self.user.token_expiration = None
        self.user.security_code = None
        self.user.security_code_expiration = None
        self.user.save()    
        update_session_auth_hash(self.request, self.user)
        messages.success(self.request, "Your password has been set")
        return super().form_valid(form)
    

# Logout view
 
class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "You have been logged out successfully")
        return redirect('login')

    
