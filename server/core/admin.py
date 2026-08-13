from django.contrib import admin

from .models import Page, Section


class PageInline(admin.TabularInline):
    model = Page
    extra = 0
    fields = ("title", "slug", "order", "is_published")
    prepopulated_fields = {"slug": ("title",)}
    show_change_link = True


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "parent", "order", "show_in_menu", "is_published")
    list_filter = ("is_published", "show_in_menu")
    list_editable = ("order", "show_in_menu", "is_published")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PageInline]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "section", "slug", "order", "is_published", "updated_at")
    list_filter = ("is_published", "section")
    list_editable = ("order", "is_published")
    search_fields = ("title", "slug", "body")
    prepopulated_fields = {"slug": ("title",)}
