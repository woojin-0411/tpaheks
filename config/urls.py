from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    
    # ★ 여기가 핵심입니다! 
    # 빈칸('')으로 두면 -> http://127.0.0.1:8000/shop/ 으로 접속
    # 'products/'를 넣으면 -> http://127.0.0.1:8000/products/shop/ 으로 접속
    path('', include('products.urls')), 
]

# 이미지 파일 경로 설정 (이게 있어야 사진이 보임)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)