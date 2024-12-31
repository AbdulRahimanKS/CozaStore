from django.db import models
from accounts.models import CustomUser


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=50, blank=True, default='')
    company = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=50, blank=True,default='')
    about = models.TextField(blank=True, default='')
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    LinkedIn = models.CharField(max_length=250, blank=True, default='')
    Facebook = models.CharField(max_length=250, blank=True, default='')
    Instagram = models.CharField(max_length=250, blank=True, default='')
    fcm_token = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.email
    

class PinCode(models.Model):
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    pin_code = models.CharField(max_length=8, blank=False)
    country = models.CharField(max_length=200, blank=False)
    city = models.CharField(max_length=200, blank=False)
    state = models.CharField(max_length=200, blank=False)
    delivery_days = models.PositiveIntegerField(blank=False)
    delivery_charge = models.PositiveIntegerField(blank=False)

    class Meta:
        unique_together = ('created_by', 'pin_code')

    def __str__(self):
        return f'{self.created_by} - {self.pin_code}'


class Notification(models.Model):
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f'Notification for {self.admin.first_name}: {self.message}'
    
    