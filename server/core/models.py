from django.db import models
from django.urls import reverse


class Section(models.Model):
    """Раздел корпоративного сайта. Поддерживает вложенность."""

    title = models.CharField("название", max_length=150)
    slug = models.SlugField("адрес", max_length=150, unique=True)
    parent = models.ForeignKey(
        "self", verbose_name="родительский раздел", null=True, blank=True,
        on_delete=models.CASCADE, related_name="children",
    )
    order = models.PositiveIntegerField("порядок", default=0)
    show_in_menu = models.BooleanField("показывать в меню", default=True)
    is_published = models.BooleanField("опубликован", default=True)

    class Meta:
        verbose_name = "раздел"
        verbose_name_plural = "разделы"
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:section", args=[self.slug])


class Page(models.Model):
    """Страница внутри раздела."""

    section = models.ForeignKey(
        Section, verbose_name="раздел", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="pages",
    )
    title = models.CharField("заголовок", max_length=200)
    slug = models.SlugField("адрес", max_length=200, unique=True)
    lead = models.TextField("краткое описание", blank=True)
    body = models.TextField("содержимое", blank=True, help_text="Допускается HTML-разметка")
    order = models.PositiveIntegerField("порядок", default=0)
    is_published = models.BooleanField("опубликована", default=True)
    updated_at = models.DateTimeField("изменена", auto_now=True)

    class Meta:
        verbose_name = "страница"
        verbose_name_plural = "страницы"
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:page", args=[self.slug])
