from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)  
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):

    USER_TYPE_CHOICES = (
        ('Customer', 'Customer'),
        ('Shop', 'Shop'),
    )

    first_name = models.CharField(max_length=30, blank=False)
    surname = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)
    country = models.CharField(max_length=50, blank=False)
    countryCode = models.CharField(max_length=15, blank=False)
    token = models.CharField(max_length=100, null=True, blank=True)
    token_expiration = models.DateTimeField(null=True, blank=True)
    security_code = models.CharField(max_length=6, null=True, blank=True)
    security_code_expiration = models.DateTimeField(null=True, blank=True)
    mobile = models.CharField(max_length=15, blank=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='Customer')

    def is_security_code_valid(self):
        if self.security_code and self.security_code_expiration:
            return timezone.now() <= self.security_code_expiration
        return False

    def is_token_valid(self):
        if self.token and self.token_expiration:
            return timezone.now() <= self.token_expiration
        return False

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'mobile']

    class Meta:
        verbose_name = 'Custom User'
        verbose_name_plural = 'Custom Users'

    def __str__(self):
        return self.email
    
