from .models import Member


def ae_access(request):
    """Inject is_ae_or_admin into all template contexts."""
    if not request.user.is_authenticated:
        return {'is_ae_or_admin': False}
    if request.user.is_staff or request.user.is_superuser:
        return {'is_ae_or_admin': True}
    is_ae = Member.objects.filter(
        display_name__iexact=request.user.username, role='ae', is_active=True
    ).exists()
    return {'is_ae_or_admin': is_ae}
