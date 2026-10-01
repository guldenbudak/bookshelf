from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def geri_don(request, varsayilan_url_adi, **kwargs):
    """Formdaki 'next' alanına döner; yoksa verilen sayfaya gider.

    Adresin kendi sitemize ait olduğunu doğrulamadan yönlendirmek, kullanıcıyı
    başka bir siteye taşımak için kullanılabilirdi (open redirect).
    """
    hedef = request.POST.get('next')
    if hedef and url_has_allowed_host_and_scheme(
        hedef, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(hedef)
    return redirect(varsayilan_url_adi, **kwargs)
