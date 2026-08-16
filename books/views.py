from django.shortcuts import render, redirect, get_object_or_404
from .forms import BookForm
from .models import Book
from django.contrib import messages

def home(request):
    return render(request, 'books/home.html')

def book_create(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Kitap başarıyla oluşturulmuştur.")
            return redirect('book-list')
    else:
        form = BookForm()

    return render(request, 'books/book_create.html', {'form': form})

def book_list(request):
    books = Book.objects.select_related('category')
    sort = request.GET.get('sort')
    if sort == 'title':
        books = books.order_by('title')
    elif sort == 'page_count':
        books = books.order_by('page_count')
    return render(request, 'books/book_list.html', {'books': books})

def book_detail(request, pk):
        book = get_object_or_404(Book, pk=pk)

        return render(request, 'books/book_detail.html', {'book': book})
def book_update(request, pk):
    book = get_object_or_404(Book, pk=pk)

    if request.method == 'POST':
        form =BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Kitap başarıyla güncellenmiştir.")
            return redirect('book-list')


    else:
        form = BookForm(instance=book)

    return render(request, 'books/book_update.html', {'form': form})


def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        book.delete()
        messages.success(request, "Kitap başarıyla silinmiştir.")
        return redirect('book-list')

    return render(request, 'books/book_delete.html', {'book': book})

