from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'surname', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    readonly_fields = ('date_joined',)  
    fieldsets = (
        (None, {'fields': ('email', 'password', 'token', 'token_expiration', 'security_code', 'security_code_expiration')}),
        ('Personal info', {'fields': ('first_name', 'surname', 'country', 'countryCode', 'mobile')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'surname', 'country', 'countryCode', 'mobile', 'token', 'token_expiration', 'security_code', 'security_code_expiration', 'password1', 'password2', 'is_staff', 'is_active', 'groups', 'user_permissions'),
        }),
    )
    search_fields = ('email',)
    ordering = ('date_joined',)

admin.site.register(CustomUser, CustomUserAdmin)
