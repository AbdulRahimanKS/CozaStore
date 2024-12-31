from django.contrib import admin
from .models import UserProfile, PinCode, Notification

admin.site.register([UserProfile, PinCode, Notification])
