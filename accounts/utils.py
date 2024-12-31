import secrets
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.tokens import default_token_generator

def send_password_reset_email(user, request):
    token = default_token_generator.make_token(user)
    user.token = token
    user.token_expiration = timezone.now() + timedelta(minutes=10)
    user.save()
    
    security_code = secrets.randbelow(900000) + 100000
    user.security_code = str(security_code)
    user.security_code_expiration = timezone.now() + timedelta(minutes=10)
    user.save()
    
    subject = "Reset Your Password"
    email_template_name = 'verify_mail.html'
    c = {
        "email": user.email,
        "domain": request.META['HTTP_HOST'],
        "site_name": "CozaStore",
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": token,
        "security_code": security_code,
        "protocol": 'https' if request.is_secure() else 'http',
    }
    verification_link = f"{c['protocol']}://{c['domain']}/accounts/pwd_reset/{c['uid']}/{c['token']}/"
    c["verification_link"] = verification_link
    
    email_body = render_to_string(email_template_name, c)
    plain_message = strip_tags(email_body)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=email_body,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
