from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # 1. 메인 & 소개 (기존 기능 유지)
    path('', views.index, name='index'),
    path('about/', views.about_us, name='about_us'),

    # 2. 쇼핑몰 흐름 (리스트 & 상세)
    path('shop/', views.product_list, name='product_list'),
    path('shop/<str:product_code>/', views.product_detail, name='product_detail'),
    
    # [에디터 페이지] 
    # (주의: views.py에 'product_custom_editor' 함수가 있어야 합니다. 
    # 만약 에러나면 views.shop으로 이름을 바꿔보세요)
    path('shop/<str:product_code>/custom/', views.product_custom_editor, name='product_custom_editor'),

    # ★ 3. 핵심 기능 (AI & 주문) - 여기가 제일 중요합니다!
    # 자바스크립트가 이 주소('remove_background_ai/')를 찾아갑니다.
    path('remove_background_ai/', views.remove_background_ai, name='remove_background_ai'),
    
    path('order/create/', views.order_create, name='order_create'),
    path('order/success/<str:order_no>/', views.order_success, name='order_success'),
    path('order/check/', views.order_check, name='order_check'),

    # 4. 문의게시판 (기존 기능 유지)
    path('qna/', views.join_list, name='qna'), 
    path('qna/create/', views.join_create, name='join_create'),
    path('qna/<int:pk>/', views.join_detail, name='join_detail'),
    path('qna/answer/create/<int:pk>/', views.join_answer_create, name='join_answer_create'),
    path('review/create/<int:product_pk>/', views.review_create, name='review_create'),
    path('qna/action/<int:pk>/', views.join_action, name='join_action'),
    # products/urls.py
    path('policy/', views.policy, name='policy'), # 이거 추가
    # products/urls.py
    path('review/create/<str:product_code>/', views.review_create, name='review_create'), # 리뷰 작성
    path('qna/', views.join_list, name='join_list'),
    path('order/cancel/<str:order_no>/', views.cancel_payment, name='cancel_payment'),
]