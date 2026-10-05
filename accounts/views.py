from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.decorators.http import require_POST

from django.db import transaction

from books.models import Book
from bookshelf.shortcuts import geri_don

from .decorators import approved_required, is_approved
from .forms import ProfileForm, ProfileSettingsForm, RegisterForm, SocialLinkFormSet
from .models import AccountApproval, FriendRequest


class RegisterView(View):
    template_name = 'account/register.html'

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Kaydın alındı. Hesabın yönetici onayından sonra aktifleşecek."
            )
            return redirect('login')

        return render(request, self.template_name, {'form': form})


class PendingView(LoginRequiredMixin, View):
    """Onayı beklemede olan ya da reddedilen kullanıcıya durumunu gösterir."""

    template_name = 'account/pending.html'

    def get(self, request):
        approval = AccountApproval.objects.filter(user=request.user).first()

        if approval and approval.status == AccountApproval.Status.APPROVED:
            return redirect('home')

        return render(request, self.template_name, {'approval': approval})


@login_required
def profile_detail(request, username=None):
    """Kullanıcı adı verilmezse kendi profilini, verilirse başkasınınkini gösterir."""

    if username is None:
        profile_user = request.user
    else:
        profile_user = get_object_or_404(User, username=username)

    is_own_profile = profile_user == request.user
    viewer_approved = is_approved(request.user)

    # Onay bekleyen kullanıcı yalnızca kendi profilini görebilir.kullanıcı kendisi değilse ve yönetici onayından geçmediyse
    if not is_own_profile and not viewer_approved:
        return redirect('pending')

    profile = profile_user.profile

    is_friend = not is_own_profile and request.user.profile.is_friend_with(profile)
    can_see_books = is_own_profile or is_friend or profile.settings.books_public

    # Kitaplar yalnızca görme yetkisi varsa sorgulanıyor; yoksa veritabanına
    # hiç gidilmiyor.
    if can_see_books:
        books = (
            Book.objects.owned_by(profile_user)
            .with_related()
            .with_favorites(request.user)
        )
        # Profil sahibinin favorileri, ziyaretçinin de görmeye yetkili olduğu
        # kitaplarla sınırlanıyor: favoriler, erişilemeyen bir kitabı görmenin
        # arka kapısı olmamalı. Görülemeyenler listelenmiyor; bu sayfadaki
        # kayıtlar ziyaretçinin kendi verisi değil, yer tutucu göstermek
        # ona bir şey anlatmaz, yalnızca gizli kayıt sayısını sızdırır.
        favorites = (
            Book.objects.favorited_by(profile_user)
            .visible_to(request.user)#bu satır sayesinde biz erişmememiz gereken kitaba erişmiyoruz.
            .with_related()
            .with_favorites(request.user)
        )
    else:
        books = []
        favorites = []

    return render(request, 'account/profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'is_own_profile': is_own_profile,
        'is_friend': is_friend,
        'can_see_books': can_see_books,
        'books': books,
        'favorites': favorites,
        'can_edit': is_own_profile and viewer_approved,
        'sent_request': FriendRequest.objects.filter(
            from_user=request.user, to_user=profile_user,
            status=FriendRequest.Status.PENDING,
        ).first(),
        'received_request': FriendRequest.objects.filter(
            from_user=profile_user, to_user=request.user,
            status=FriendRequest.Status.PENDING,
        ).first(),
    })


@login_required
@approved_required
def profile_edit(request):
    """Profil, ayarlar ve sosyal bağlantılar tek sayfada birlikte kaydedilir."""

    profile = request.user.profile

    if request.method == 'POST':
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        settings_form = ProfileSettingsForm(request.POST, instance=profile.settings)
        link_formset = SocialLinkFormSet(request.POST, instance=profile)

        # all([...]) üçünü de doğrular; "and" olsaydı ilki hatalıyken
        # diğerlerinin hataları hesaplanmaz ve ekranda görünmezdi.
        if all([profile_form.is_valid(), settings_form.is_valid(), link_formset.is_valid()]):
            # Biri kaydedilip diğeri patlarsa profil yarım kalmasın.
            with transaction.atomic():
                profile_form.save()
                settings_form.save()
                link_formset.save()

            messages.success(request, "Profilin güncellendi.")
            return redirect('my-profile')
    else:
        profile_form = ProfileForm(instance=profile)
        settings_form = ProfileSettingsForm(instance=profile.settings)
        link_formset = SocialLinkFormSet(instance=profile)

    return render(request, 'account/profile_edit.html', {
        'profile_form': profile_form,
        'settings_form': settings_form,
        'link_formset': link_formset,
    })


@login_required
@approved_required
@require_POST
def friend_request_send(request, username):
    to_user = get_object_or_404(User, username=username)
    profile = request.user.profile

    # Veritabanı da engelliyor; buradaki kontrol kullanıcıya mesaj göstermek için.
    if to_user == request.user:
        messages.error(request, "Kendine arkadaşlık isteği gönderemezsin.")
        return geri_don(request, 'my-profile')

    if profile.is_friend_with(to_user.profile):
        messages.info(request, f"{to_user.username} ile zaten arkadaşsınız.")
        return geri_don(request, 'profile-detail', username=username)

    with transaction.atomic():
        # Karşı taraf bize zaten istek göndermişse ikimiz de istiyoruz demektir.
        karsi_istek = FriendRequest.objects.filter(
            from_user=to_user, to_user=request.user,
            status=FriendRequest.Status.PENDING,
        ).first()

        if karsi_istek:
            karsi_istek.status = FriendRequest.Status.ACCEPTED
            karsi_istek.save()
            profile.friends.add(to_user.profile)
            messages.success(
                request,
                f"{to_user.username} sana zaten istek göndermişti, artık arkadaşsınız."
            )
            return geri_don(request, 'profile-detail', username=username)

        # Aynı yön için tek satır olabildiğinden, reddedilmiş bir istek
        # yeniden gönderilirken yeni satır açılmaz, bu satır tekrar beklemeye alınır.
        istek, yeni_mi = FriendRequest.objects.get_or_create(
            from_user=request.user, to_user=to_user,
        )

        if yeni_mi:
            messages.success(request, f"{to_user.username} kullanıcısına istek gönderildi.")
        elif istek.status == FriendRequest.Status.PENDING:
            messages.info(request, "Bu kullanıcıya zaten bir isteğin var, cevap bekleniyor.")
        else:
            istek.status = FriendRequest.Status.PENDING
            istek.save()
            messages.success(request, f"{to_user.username} kullanıcısına istek tekrar gönderildi.")

    return geri_don(request, 'profile-detail', username=username)


@login_required
@approved_required
@require_POST
def friend_request_accept(request, pk):
    # to_user filtresi, isteği yalnızca alıcısının kabul edebilmesini sağlar.
    istek = get_object_or_404(
        FriendRequest, pk=pk, to_user=request.user,
        status=FriendRequest.Status.PENDING,
    )

    with transaction.atomic():
        istek.status = FriendRequest.Status.ACCEPTED
        istek.save()
        request.user.profile.friends.add(istek.from_user.profile)

    messages.success(request, f"{istek.from_user.username} ile arkadaş oldunuz.")
    return geri_don(request, 'friends')


@login_required
@approved_required
@require_POST
def friend_request_reject(request, pk):
    istek = get_object_or_404(
        FriendRequest, pk=pk, to_user=request.user,
        status=FriendRequest.Status.PENDING,
    )
    istek.status = FriendRequest.Status.REJECTED
    istek.save()

    messages.info(request, f"{istek.from_user.username} kullanıcısının isteği reddedildi.")
    return geri_don(request, 'friends')


@login_required
@approved_required
@require_POST
def friend_remove(request, username):
    other = get_object_or_404(User, username=username)

    with transaction.atomic():
        # Simetrik ilişki olduğu için Django iki yöndeki satırı da siler.
        request.user.profile.friends.remove(other.profile)
        # Eski istek kayıtları "accepted" kalmasın; aksi hâlde yeniden
        # istek gönderildiğinde durum tutarsız görünür.
        FriendRequest.objects.filter(
            from_user__in=[request.user, other], to_user__in=[request.user, other],
            status=FriendRequest.Status.ACCEPTED,
        ).update(status=FriendRequest.Status.REJECTED)

    messages.info(request, f"{other.username} arkadaşlıktan çıkarıldı.")
    return geri_don(request, 'friends')


@login_required
@approved_required
def friends_list(request):
    profile = request.user.profile

    return render(request, 'account/friends.html', {
        'friends': profile.get_friends(),
        'incoming': FriendRequest.objects.filter(
            to_user=request.user, status=FriendRequest.Status.PENDING,
        ).select_related('from_user__profile'),
        'outgoing': FriendRequest.objects.filter(
            from_user=request.user, status=FriendRequest.Status.PENDING,
        ).select_related('to_user__profile'),
    })


@login_required
@approved_required
def user_search(request):
    sorgu = request.GET.get('q', '').strip()
    profile = request.user.profile
    sonuclar = []

    if sorgu:
        sonuclar = (
            User.objects.filter(username__icontains=sorgu)
            .exclude(pk=request.user.pk)
            .select_related('profile')
            .order_by('username')[:20]
        )

    return render(request, 'account/user_search.html', {
        'sorgu': sorgu,
        'sonuclar': sonuclar,
        'arkadas_idleri': set(profile.friends.values_list('user_id', flat=True)),
        'istek_gonderilenler': set(
            FriendRequest.objects.filter(
                from_user=request.user, status=FriendRequest.Status.PENDING,
            ).values_list('to_user_id', flat=True)
        ),
        'istek_gelenler': set(
            FriendRequest.objects.filter(
                to_user=request.user, status=FriendRequest.Status.PENDING,
            ).values_list('from_user_id', flat=True)
        ),
    })
