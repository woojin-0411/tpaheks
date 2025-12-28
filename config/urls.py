from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ----------------------------------------------------------------------
# Project URLs (최상위 주소 설정)
# ----------------------------------------------------------------------
urlpatterns = [
    # 1. 관리자 페이지
    path('admin/', admin.site.urls),
    
    # 2. 소셜 로그인 (카카오 등) - allauth 앱 연결
    path('accounts/', include('allauth.urls')),
    
    # 3. 우리 쇼핑몰/게시판 기능 - products 앱으로 모두 위임!
    # (join 관련 주소도 products/urls.py 안에 있으니 여기선 따로 안 적어도 됩니다)
    path('', include('products.urls')), 
]

# ----------------------------------------------------------------------
# 개발 환경에서 미디어 파일 (이미지) 서빙 설정
# ----------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)