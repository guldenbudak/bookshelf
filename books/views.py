from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import BookForm, CommentForm
from .models import Book, Comment, Favorite
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import approved_required
from bookshelf.shortcuts import geri_don


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

SAYFA_BASINA = 12


def sirala(books, sort):
    """Listeleri aynı şekilde sıralar; /books/ ve /feed/ ortak kullanıyor.

    Varsayılan sıra da açıkça veriliyor: annotate() eklenen sorgularda
    Django modeldeki Meta.ordering'i kesin saymaz ve sayfalama tutarsız
    olabilir — aynı kitap iki sayfada birden görünebilirdi.
    """
    if sort == 'title':
        return books.order_by('title', 'pk')
    if sort == 'page_count':
        return books.order_by('page_count', 'pk')
    return books.order_by('-created_at', 'pk')


def sayfala(request, books):
    """Listeyi sayfalara böler.

    get_page, geçersiz veya aralık dışı sayfa numaralarını hata vermeden
    ele alır: harf gelirse ilk sayfayı, çok büyük bir sayı gelirse son
    sayfayı döndürür.
    """
    return Paginator(books, SAYFA_BASINA).get_page(request.GET.get('page'))


@login_required
@approved_required
def book_list(request):
    """Kullanıcının kendi kitapları."""
    books = Book.objects.owned_by(request.user).with_related().with_favorites(request.user)
    books = sirala(books, request.GET.get('sort'))

    return render(request, 'books/book_list.html', {'books': sayfala(request, books)})


@login_required
@approved_required
def book_feed(request):
    """Arkadaşların kitapları."""
    books = Book.objects.from_friends_of(request.user).with_related().with_favorites(request.user)
    books = sirala(books, request.GET.get('sort'))

    return render(request, 'books/book_feed.html', {'books': sayfala(request, books)})


@login_required
@approved_required
def book_detail(request, pk):
    # Arama tüm tabloda değil, kullanıcının görmeye yetkili olduğu kitaplar
    # arasında yapılıyor. Yetkisi yoksa kitap "yok" sayılır ve 404 döner.
    book = get_object_or_404(
        Book.objects.visible_to(request.user).with_related().with_favorites(request.user),
        pk=pk,
    )

    return render(request, 'books/book_detail.html', detay_baglami(request, book))


def detay_baglami(request, book, comment_form=None):
    """Kitap detay sayfasının içeriği.

    Yorum formu hatalıyken sayfayı yeniden basmak gerektiği için ayrı
    fonksiyona alındı; iki yerden aynı bağlam üretiliyor.
    """
    return {
        'book': book,
        # Silinen yorumlar da listeleniyor; şablon onları "Bu yorum silindi"
        # olarak gösteriyor.
        'comments': book.comments.select_related('author__profile'),
        'comment_form': comment_form if comment_form is not None else CommentForm(),
    }


@login_required
@approved_required
@require_POST
def comment_create(request, pk):
    """Görülebilen her kitaba yorum yazılabilir; sahibi olmak gerekmez."""
    book = get_object_or_404(
        Book.objects.visible_to(request.user).with_related().with_favorites(request.user),
        pk=pk,
    )

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.book = book
        comment.author = request.user
        comment.save()
        messages.success(request, "Yorumun eklendi.")
        return redirect('book-detail', pk=pk)

    # Hatalıysa yazdığı metin kaybolmasın diye sayfa dolu formla basılıyor.
    return render(request, 'books/book_detail.html', detay_baglami(request, book, form))


@login_required
@approved_required
def comment_update(request, pk):
    """Yorumu yalnızca yazarı düzenleyebilir."""
    comment = get_object_or_404(
        Comment.objects.select_related('book'),
        pk=pk,
        book__in=Book.objects.visible_to(request.user),
    )

    if not comment.can_edit(request.user):
        raise PermissionDenied("Bu yorum sana ait değil.")

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, "Yorumun güncellendi.")
            return redirect('book-detail', pk=comment.book_id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'books/comment_update.html', {
        'form': form,
        'comment': comment,
    })


@login_required
@approved_required
@require_POST
def comment_delete(request, pk):
    """Yorumu yazarı siler; kitabın sahibi de moderasyon için silebilir."""
    comment = get_object_or_404(
        Comment.objects.select_related('book'),
        pk=pk,
        book__in=Book.objects.visible_to(request.user),
    )

    if not comment.can_delete(request.user):
        raise PermissionDenied("Bu yorumu silme yetkin yok.")

    # Satır kaldırılmıyor, yalnızca işaretleniyor (soft delete).
    comment.is_deleted = True
    comment.save()

    messages.info(request, "Yorum silindi.")
    return geri_don(request, 'book-detail', pk=comment.book_id)


@login_required
@approved_required
@require_POST
def favorite_toggle(request, pk):
    """Favorilerde varsa çıkarır, yoksa ekler."""
    # Yalnızca görebildiği bir kitabı favorileyebilir; göremediği kitabın
    # numarasını deneyen kullanıcı 404 alır.
    book = get_object_or_404(Book.objects.visible_to(request.user), pk=pk)

    # get_or_create, aynı kitabın ikinci kez eklenmesini de engeller:
    # kayıt zaten varsa yenisi açılmaz, var olan bulunur.
    favori, yeni_mi = Favorite.objects.get_or_create(user=request.user, book=book)

    if yeni_mi:
        messages.success(request, f"{book.title} favorilerine eklendi.")
    else:
        favori.delete()
        messages.info(request, f"{book.title} favorilerinden çıkarıldı.")

    return geri_don(request, 'book-detail', pk=pk)


@login_required
@approved_required
def favorite_list(request):
    """Kullanıcının favorileri.

    Arkadaşlıktan çıkılmış bir kitabın favori kaydı silinmez; listede
    erişilemez olarak gösterilir. Arkadaşlık geri kurulursa kart normale döner.
    """
    favoriler = (
        Favorite.objects
        .filter(user=request.user)
        .select_related('book__category', 'book__owner')
    )

    gorunur_idler = set(
        Book.objects.visible_to(request.user).values_list('id', flat=True)
    )
    favori_sayilari = dict(
        Book.objects.filter(favorited_by__user=request.user)
        .annotate(sayi=Count('favorited_by', distinct=True))
        .values_list('id', 'sayi')
    )

    kayitlar = []
    for favori in favoriler:
        erisilebilir = favori.book_id in gorunur_idler
        book = favori.book
        if erisilebilir:
            # Şablondaki kart bu iki değeri bekliyor.
            book.favori_sayisi = favori_sayilari.get(book.id, 0)
            book.favorimde = True
        kayitlar.append({'book': book, 'erisilebilir': erisilebilir})

    return render(request, 'books/favorite_list.html', {'kayitlar': kayitlar})
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

