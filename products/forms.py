from django import forms
from .models import Rating, CheckOutAddresses


# Checkout addresses

class CheckoutAddressesForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
    class Meta:
        model = CheckOutAddresses
        fields = ['name', 'mobile', 'locality', 'address', 'city', 'state', 'pin_code', 'landmark', 'alternate_phone', 'default', 'address_type']
        widgets = {
            'name': forms.TextInput(attrs={'id':"name", 'class': 'form-control', 'placeholder': 'Name'}),
            'mobile': forms.TextInput(attrs={'id':"mobile2", 'class': 'form-control', 'placeholder': '10-digit mobile number'}),
            'pin_code': forms.TextInput(attrs={'id':"pin_code", 'class': 'form-control', 'placeholder': 'Pincode'}),
            'locality': forms.TextInput(attrs={'id':"locality", 'class': 'form-control', 'placeholder': 'Locality'}),
            'address': forms.Textarea(attrs={'id':"address2", 'class': 'form-control', 'placeholder': 'Address (Area and Street)', 'rows': 3}),
            'city': forms.TextInput(attrs={'id':"city2", 'class': 'form-control', 'placeholder': 'City/District/Town'}),
            'state': forms.TextInput(attrs={'id':"state", 'class': 'form-control', 'placeholder': 'State'}),
            'landmark': forms.TextInput(attrs={'id':"landmark", 'class': 'form-control', 'placeholder': 'Landmark (Optional)'}),
            'alternate_phone': forms.TextInput(attrs={'id':"alternate_phone", 'class': 'form-control', 'placeholder': 'Alternate Phone (Optional)'}),
            'address_type': forms.RadioSelect(choices=CheckOutAddresses.ADDRESS_TYPE_CHOICES, attrs={'id': "address_type", 'class': 'form-check-input'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        mobile = cleaned_data.get('mobile')
        alternate_phone = cleaned_data.get('alternate_phone')
        pin_code = self.cleaned_data.get('pin_code')

        if mobile:
            if not mobile.isdigit():
                self.add_error('mobile', "Mobile number must contain only digits")
            elif len(mobile) != 10:
                self.add_error('mobile', "Mobile number must be exactly 10 digits long")

        if alternate_phone:
            if not alternate_phone.isdigit():
                self.add_error('alternate_phone', "Alternate phone number must contain only digits")
            elif len(alternate_phone) != 10:
                self.add_error('alternate_phone', "Alternate phone number must be exactly 10 digits long")
                
        if not pin_code.isdigit():
            self.add_error('pin_code', "Pin code must be a 6-digit number")

        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
        return instance
    
        
class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'review']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'type': 'number', 'class': 'form-control', 'id': 'rating-input'}),
            'review': forms.Textarea(attrs={'rows': 4, 'id':'review', 'placeholder': 'Write your review here...', 'class': 'form-control'})
        }
    

        
        
