from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Case, When, Value, CharField
from django.core.mail import send_mail
from django.conf import settings
from .models import Product, Inventory, ProductImage, Announcement, JoinPost, JoinAnswer, JoinPostImage

# ==========================================
# 1. 메인 / 기본 페이지들
# ==========================================

def index(request):
    """홈 페이지 (메인 화면)"""
    product_names_order = ['반팔 앞판', '반팔 뒷판', '바람막이 앞판', '바람막이 뒷판']
    
    ordering = Case(*[When(name=name, then=Value(i)) for i, name in enumerate(product_names_order)], 
                    default=Value(len(product_names_order)), 
                    output_field=CharField())
    
    all_products = Product.objects.filter(name__in=product_names_order).order_by(ordering)[:4]
    
    if not all_products:
        all_products = Product.objects.all().order_by('-id')[:4]

    return render(request, 'products/index.html', {'all_products': all_products})


def about_us(request):
    """회사 소개 페이지"""
    return render(request, 'products/about_us.html')


def shop(request):
    """상품 전체 목록 (SHOP) 페이지"""
    all_products = Product.objects.all().order_by('-id')
    return render(request, 'products/shop.html', {'all_products': all_products})


def game(request):
    """미니 게임 페이지"""
    return render(request, 'products/game.html')


def product_detail(request, pk):
    """상품 상세 페이지"""
    product = get_object_or_404(Product, pk=pk)
    images = ProductImage.objects.filter(product=product).order_by('id')
    
    try:
        inventory = Inventory.objects.get(product=product)
    except Inventory.DoesNotExist:
        inventory = None
        
    context = {
        'product': product,
        'images': images,
        'inventory': inventory,
    }
    return render(request, 'products/product_detail.html', context)


# ==========================================
# 2. Q&A 게시판 (JOIN) 관련 기능
# ==========================================

ADMIN_CODE = "4678"  # 관리자 코드
USER_CODES = [       # 일반 회원 코드
    "1001", "2002", "3003", "4004", "5005", 
    "6006", "7007", "8008", "9009", "7777"
]

def qna(request):
    """Q&A 목록 보기"""
    posts = JoinPost.objects.all().order_by('-is_pinned', '-created_at')
    return render(request, 'products/join.html', {'posts': posts})


def qna_detail(request, pk):
    """Q&A 상세 보기"""
    post = get_object_or_404(JoinPost, pk=pk)
    return render(request, 'products/join_detail.html', {'post': post})


def join_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        author_name = request.POST.get('author_name')
        input_code = request.POST.get('access_code')
        
        # [중요] 여러 장의 이미지를 리스트로 가져옴
        images = request.FILES.getlist('images') 

        if (input_code == ADMIN_CODE) or (input_code in USER_CODES):
            if title and content and author_name:
                # 1. 게시글 먼저 저장
                post = JoinPost.objects.create(
                    title=title,
                    content=content,
                    author_name=author_name,
                    is_pinned=(input_code == ADMIN_CODE)
                )
                
                # 2. 이미지들 반복문으로 저장
                for img in images:
                    JoinPostImage.objects.create(post=post, image=img)

                return redirect('products:qna')
        else:
            return render(request, 'products/join_create.html', {'error': '작성 코드가 올바르지 않습니다.'})

    return render(request, 'products/join_create.html')

def qna_answer_create(request, pk):
    if request.method == 'POST':
        post = get_object_or_404(JoinPost, pk=pk)
        content = request.POST.get('content')
        admin_code = request.POST.get('admin_code')
        if admin_code == ADMIN_CODE:
            JoinAnswer.objects.create(post=post, content=content)
        return redirect('products:qna_detail', pk=pk)
    return redirect('products:qna')


def qna_action(request, pk):
    if request.method == 'POST':
        post = get_object_or_404(JoinPost, pk=pk)
        input_code = request.POST.get('admin_code')
        action_type = request.POST.get('action_type')
        if input_code == ADMIN_CODE:
            if action_type == 'delete':
                post.delete()
                return redirect('products:qna')
            elif action_type == 'pin':
                post.is_pinned = not post.is_pinned
                post.save()
        return redirect('products:qna')
    return redirect('products:qna')

# ==========================================
# 3. 이메일 견적 발송 기능
# ==========================================

def send_quote(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        product_name = request.POST.get('product_type')
        selected_locations = request.POST.get('selected_locations') 
        quantity = request.POST.get('quantity')
        special_requests = request.POST.get('special_requests', '없음')
        raw_price = request.POST.get('total_price', '0')
        discount_rate = request.POST.get('discount_rate')

        try:
            total_price_formatted = f"{int(raw_price):,}" 
        except ValueError:
            total_price_formatted = raw_price

        subject = f"[견적요청] {product_name} ({phone})"
        
        message = f"""
        [TR Clothing Store] 새로운 견적 요청이 도착했습니다!

        ========================================
        1. 📞 고객 연락처 : {phone}
        2. 👕 상품명      : {product_name}
        3. 📦 주문 수량   : {quantity}벌
        4. 📍 선택 위치   : {selected_locations} 
        5. 🎟️ 적용 할인율 : {discount_rate}%
        ----------------------------------------
        📝 전할 말 (특이사항):
        {special_requests}
        ----------------------------------------
        💰 최종 예상 금액: {total_price_formatted}원
        ========================================
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            print("이메일 발송 성공!")
        except Exception as e:
            print(f"이메일 발송 실패: {e}")

        return redirect('products:shop')
    
    return redirect('products:shop')