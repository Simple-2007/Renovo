from .models import Section


def site_nav(request):
    """Меню разделов доступно во всех шаблонах."""
    return {
        "nav_sections": Section.objects.filter(
            is_published=True, show_in_menu=True, parent__isnull=True,
        )
    }
