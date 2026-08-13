from django.shortcuts import get_object_or_404, render

from .models import Page, Section


def section_view(request, slug):
    section = get_object_or_404(Section, slug=slug, is_published=True)
    pages = section.pages.filter(is_published=True)
    return render(request, "core/section.html", {"section": section, "pages": pages})


def page_view(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    return render(request, "core/page.html", {"page": page})
