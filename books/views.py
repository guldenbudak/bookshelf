from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from .forms import BookForm
from .models import Book
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import approved_required


def sahibi_olmali(book, user):
    """Kitabı yalnızca sahibi düzenleyip silebilir; değilse 403 döner."""
    if book.owner != user:
        raise PermissionDenied("Bu kitap sana ait değil.")


def home(request):
    return render(request, 'books/home.html')

@login_required
@approved_required
def book_create(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            # Sahip formdan gelmiyor; kullanıcı başkasının adına kitap
            # ekleyemesin diye oturumdaki kullanıcıdan alınıyor.
            book = form.save(commit=False)
            book.owner = request.user
            book.save()
            messages.success(request, "Kitap başarıyla oluşturulmuştur.")
            return redirect('book-list')
    else:
        form = BookForm()

    return render(request, 'books/book_create.html', {'form': form})

@login_required
@approved_required
def book_list(request):
    books = Book.objects.select_related('category')
    sort = request.GET.get('sort')
    if sort == 'title':
        books = books.order_by('title')
    elif sort == 'page_count':
        books = books.order_by('page_count')
    return render(request, 'books/book_list.html', {'books': books})

@login_required
@approved_required
def book_detail(request, pk):
        book = get_object_or_404(Book, pk=pk)

        return render(request, 'books/book_detail.html', {'book': book})
@login_required
@approved_required
def book_update(request, pk):
    book = get_object_or_404(Book, pk=pk)
    sahibi_olmali(book, request.user)

    if request.method == 'POST':
        form =BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Kitap başarıyla güncellenmiştir.")
            return redirect('book-list')


    else:
        form = BookForm(instance=book)

    return render(request, 'books/book_update.html', {'form': form})



@login_required
@approved_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    sahibi_olmali(book, request.user)

    if request.method == 'POST':
        book.delete()
        messages.success(request, "Kitap başarıyla silinmiştir.")
        return redirect('book-list')

    return render(request, 'books/book_delete.html', {'book': book})

