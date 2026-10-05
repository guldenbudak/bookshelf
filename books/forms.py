from django import forms
from .models import Book, Category, Comment


class ManualBookForm(forms.Form):
    title = forms.CharField(max_length=200)
    author = forms.CharField(max_length=100)
    category = forms.ModelChoiceField(queryset=Category.objects.all())
    page_count = forms.IntegerField()
    is_read = forms.BooleanField(required=False)
    rating = forms.IntegerField(required=False)

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'category',
            'page_count',
            'is_read',
            'rating',
            'cover'
        ]

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        if rating is not None:
            if rating < 1 or rating > 5:
                raise forms.ValidationError('Puan 1 ile 5 arasında olmalıdır.')
        return rating


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        # Yazar ve kitap formdan gelmez; view'da oturumdaki kullanıcıdan ve
        # adresten alınır, böylece kimse başkası adına yorum yazamaz.
        fields = ('text',)
        labels = {'text': 'Yorumun'}
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Bu kitap hakkında ne düşünüyorsun?',
            }),
        }
        error_messages = {
            'text': {'required': "Yorum boş olamaz."},
        }
