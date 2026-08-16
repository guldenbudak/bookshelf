from django.db import models
from django.forms import ModelForm


class Category(models.Model):
    name = models.CharField(max_length=50,unique=True)
    def __str__(self):
        return self.name

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='books',
    )
    page_count = models.PositiveIntegerField()
    is_read = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cover = models.ImageField(upload_to='covers/',blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title




