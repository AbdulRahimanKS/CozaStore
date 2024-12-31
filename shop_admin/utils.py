from django.shortcuts import get_object_or_404
from shop_admin.models import UserProfile
from firebase_admin import messaging


# Send new products added notification based on topic
def send_new_product_notification(product_name):
    message = messaging.Message(
        notification=messaging.Notification(
            title="New Product Alert!",
            body=f"Check out our new product: {product_name}!",
        ),
        topic="new_products"
    )
    response = messaging.send(message)
    

# Send refund success notification
def send_refund_success_notifcation(product_name, user):
    user_profile = get_object_or_404(UserProfile, user=user)
    fcm_token = user_profile.fcm_token
    message = messaging.Message(
        notification=messaging.Notification(
            title="Refund Successful!",
            body=f"Your refund request has been approved for the product: {product_name}!",
        ),
        token=fcm_token
    )
    response = messaging.send(message)
    
    