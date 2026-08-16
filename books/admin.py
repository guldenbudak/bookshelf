from django.contrib import admin
from .models import Category,Book

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

class BookAdmin(admin.ModelAdmin):
    list_filter = ['category','is_read',]
    list_display = ['title','author','page_count']

admin.site.register(Category,CategoryAdmin)
admin.site.register(Book,BookAdmin)


