from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # 1. 메인 페이지
    path('', views.index, name='index'),

    # 2. 회사 소개
    path('about-us/', views.about_us, name='about_us'),

    # 3. 상품 목록 (Shop)
    path('shop/', views.shop, name='shop'),

    # 4. 견적 요청 (이메일 발송)
    path('send-quote/', views.send_quote, name='send_quote'),

    # ======================================================
    # [수정된 부분] 게시판 관련 URL
    # ======================================================
   # 1. 목록 페이지
    path('qna/', views.qna, name='qna'),

    # 2. 글쓰기 페이지
    path('qna/create/', views.join_create, name='join_create'),

    # [추가] 3. 상세 보기 페이지 (게시글 번호 pk 필요)
    path('qna/<int:pk>/', views.qna_detail, name='qna_detail'),

    # [추가] 4. 관리자 답변 작성 (게시글 번호 pk 필요)
    path('qna/<int:pk>/answer/', views.qna_answer_create, name='qna_answer_create'),

    # 5. 관리자 액션 (삭제/고정)
    path('qna/action/<int:pk>/', views.qna_action, name='qna_action'),
    # ======================================================

    # 5. 미니 게임
    path('game/', views.game, name='game'),
    
    # 6. 상품 상세 (필요시)
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
]