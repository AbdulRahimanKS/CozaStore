from shop_admin.models import UserProfile, Notification


def user_profile(request):
    if request.user.is_authenticated:
        user = request.user
        try:
            user_nav = user.userprofile
            profile_image = user_nav.profile_image.url if user_nav.profile_image else ''
            return {
                'user_nav': {
                    'username': f"{user.first_name} {user.surname}",
                    'job': user_nav.job_title,
                    'profile_image': profile_image
                }
            }
        except UserProfile.DoesNotExist:
            return {
                'user_nav': {
                    'username': f"{user.first_name} {user.surname}",
                    'job': '',
                    'profile_image': ''
                }
            }
    return {
        'user_nav': {
            'username': '',
            'job': '',
            'profile_image': ''
        }
    }
    

def notifications(request):
    if request.user.is_authenticated:
        sliced_notifications = Notification.objects.filter(admin=request.user, is_read=False).order_by('-created_at')[:3]
        total_notifications = len(Notification.objects.filter(admin=request.user, is_read=False))
        return {'sliced_notifications': sliced_notifications, 'total_notifications': total_notifications}
    return {'notifications': []}

