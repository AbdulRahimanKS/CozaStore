from django import forms
from .models import CustomUser
from .country_choices import COUNTRY_CHOICES
from django.contrib.auth import authenticate


# Authentication using email and password

class LoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'id': 'email',
            'autocomplete': 'off'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'id': 'pwd',
            'autocomplete': 'new-password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        user = authenticate(email=email, password=password)

        if user is None:
            raise forms.ValidationError("Invalid email or password")
        
        self.user = user
        return cleaned_data


# Create user account

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'New password', 'autocomplete': 'new-password'})
    )
    password2 = forms.CharField(
        label='Repeat Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat password', 'autocomplete': 'off'})
    )
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'input-4'})
    )
    agree_terms = forms.BooleanField(
        required=True,
        label='Agree to terms and conditions'
    )

    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'First name'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'input-2', 'autocomplete': 'off'}),
        required=True
    )
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        widget=forms.Select(attrs={'class': 'input-3 country_style', 'id': 'inputCountry'}),
        required=True
    )
    mobile = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'placeholder': 'Mobile number', 'class': 'input-3 mobile_style'}),
        required=True
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'surname', 'email', 'country', 'mobile', 
            'user_type', 'agree_terms'
        ]
        widgets = {
            'surname': forms.TextInput(attrs={'placeholder': 'Surname'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            if CustomUser.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
                raise forms.ValidationError("Email is already registered")
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            if not mobile.isdigit():
                self.add_error('mobile', "Mobile number must contain only digits")
            elif len(mobile) != 10:
                self.add_error('mobile', "Mobile number must be exactly 10 digits long")

        return mobile

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

# Sending email to reset password

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email', 'autocomplete': 'off'}))


# Reset password

class SetPasswordForm(forms.Form):
    security_code = forms.CharField(
        required=True,
        label='Security Code',
        widget=forms.TextInput(attrs={'placeholder': 'Enter security code', 'autocomplete': 'new-security-code'})
    )
    new_password = forms.CharField(
        required=True,
        label='New Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter new password', 'autocomplete': 'new-password'})
    )
    confirm_password = forms.CharField(
        required=True,
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password', 'autocomplete': 'off'})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_security_code(self):
        security_code = self.cleaned_data.get('security_code')

        if self.user and security_code:
            if self.user.security_code != security_code:
                raise forms.ValidationError("Invalid security code")

            if not self.user.is_security_code_valid():
                raise forms.ValidationError("The security code has expired")
        
        return security_code

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
        
        return cleaned_data
