import base64
import io
import json
import traceback
import random
import string
import requests
import time
import datetime
import uuid
import hmac
import hashlib
from datetime import datetime
from rembg import remove 
from PIL import Image
from io import BytesIO
# from coolsms_backend import Coolsms
from django.db import transaction # 재고 트랜잭션용
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives, send_mail
from django.http import JsonResponse
from email.mime.image import MIMEImage
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .forms import ReviewForm
from .models import Product, Order, JoinPost, ProductColor, Answer, Review, ProductOption

SIZE_EXTRA_COST = {'XS': 0, 'S': 0, 'M': 0, 'L': 0, 'XL': 0, '2XL': 1100, '3XL': 1100, '4XL': 2000}

def send_kakao_alimtalk(to_number, customer_name, order_no):
    api_key = "NCSBUF3E5MFH06TL"
    api_secret = "W1XYHUQYL4L5CU3TL4WOFT8NMYR1F7NT"
    client = Coolsms(api_key, api_secret)

    # 전화번호 하이픈 제거
    to_number = to_number.replace('-', '')

    params = {
        'to': to_number,
        'from': '01083595560', # 발신번호 (솔라피에 등록된 번호여야 함)
        'type': 'ATA', # 알림톡
        'text': f"[세모단] 주문이 접수되었습니다.\n주문번호: {order_no}\n{customer_name}님 감사합니다.",
        'kakaoOptions': {
            'pfId': '세모단', # 솔라피에서 발급받은 PFID
            'templateId': 'kxDEoipAao', # 등록한 템플릿 ID
        }
    }
    
    try:
        response = client.send_message(params)
        print("알림톡 전송 성공:", response)
    except Exception as e:
        print("알림톡 전송 실패:", e)

# ... (index, about_us, product_list, product_detail, product_custom_editor는 기존 코드 유지) ...
def index(request):
    # ★ [수정] 랜덤 제거 -> '돈 낸 순서(Priority)'대로 4개 노출
    # priority가 높은 순서대로 정렬하고, 같으면 최신순(-id)으로 정렬해서 상위 4개만 자름
    products = Product.objects.all().order_by('-priority', '-id')[:4]
    
    return render(request, 'products/index.html', {'products': products})
def about_us(request): return render(request, 'products/about_us.html')
# products/views.py

def product_list(request):
    # 1. 검색어 가져오기 (없으면 빈 문자열)
    query = request.GET.get('q', '') 

    # 2. 일단 모든 상품을 가져올 준비를 합니다.
    products = Product.objects.all()

    # 3. 검색어가 있다면? -> 이름에 검색어가 들어간 것만 남깁니다. (필터링)
    if query:
        products = products.filter(name__icontains=query)

    # 4. ★ [핵심] 정렬 적용 (광고 수익 모델)
    # ① priority(우선순위)가 높은 순서대로 먼저 정렬 (광고)
    # ② priority가 같다면, id(최신순)으로 정렬
    products = products.order_by('-priority', '-id')
    
    # 5. 템플릿으로 전달
    # (주의: 사용하시는 템플릿 파일명이 'shop.html'인지 'product_list.html'인지 확인하세요!)
    return render(request, 'products/product_list.html', {
        'products': products, 
        'query': query
    })
def product_detail(request, product_code):
    product = get_object_or_404(Product, code=product_code)
    
    # 1. 재고/사이즈 옵션 가져오기
    # (HTML에서 품절 여부를 표시하기 위해 필요합니다)
    options = product.options.all().order_by('color', 'size')
    
    # 2. 리뷰 가져오기 (최신순)
    reviews = product.reviews.all().order_by('-created_at')
    
    # 3. 리뷰 작성 폼 준비
    review_form = ReviewForm()

    # 4. 한 번에 묶어서 템플릿으로 전달 (return은 맨 마지막에 한 번만!)
    context = {
        'product': product,
        'options': options,      
        'reviews': reviews,
        'review_form': review_form,
    }
    return render(request, 'products/product_detail.html', context)

# products/views.py
# products/views.py

def product_custom_editor(request, product_code):
    # 1. 상품 & 색상 정보 가져오기 (이게 제일 먼저 실행돼야 함)
    product = get_object_or_404(Product, code=product_code)
    # ★ [핵심] 색상 데이터 가져오기 (이게 있어야 이미지가 뜹니다!)
    colors = ProductColor.objects.filter(product=product)

    # 2. [POST 요청] 주문하기/결제하기 버튼을 눌렀을 때만 실행
    if request.method == 'POST':
        try:
            # --- (1) 폼 데이터 가져오기 ---
            customer_name = request.POST.get('customer_name') # name 속성 주의
            customer_phone = request.POST.get('phone')
            customer_addr = request.POST.get('address')
            detail_req = request.POST.get('detail_request', '')
            
            # 옵션 정보
            color = request.POST.get('color_selected', 'default') # shop.html의 hidden input name 확인
            size = request.POST.get('size_detail_text', '') # 사이즈 상세 문자열
            
            # 숫자형 데이터 변환 (에러 방지용 안전 장치)
            try:
                quantity = int(request.POST.get('total_quantity', 1))
            except (ValueError, TypeError):
                quantity = 1
                
            try:
                total_price = int(request.POST.get('total_price', 0))
            except (ValueError, TypeError):
                total_price = product.price

            # 결제 정보
            imp_uid = request.POST.get('imp_uid')
            merchant_uid = request.POST.get('merchant_uid')

            # --- (2) 주문 객체 생성 및 저장 ---
            order = Order.objects.create(
                product=product,
                customer_name=customer_name,
                contact_number=customer_phone, # 모델 필드명이 contact_number 인지 phone 인지 꼭 확인!
                address=customer_addr,
                detail_request=detail_req,
                option_color=color, # 모델 필드명 확인 (color vs option_color)
                option_size=size,   # 모델 필드명 확인 (size vs option_size)
                quantity=quantity,
                total_price=total_price,
                imp_uid=imp_uid,
                merchant_uid=merchant_uid,
                status='결제완료' if imp_uid else '견적요청', # 결제 정보 있으면 완료, 없으면 견적
                created_at=datetime.now()
            )
            
            # --- (3) 알림 발송 (선택 사항) ---
            # send_kakao_alimtalk(...) 

            # ★ 저장 성공하면 홈으로 이동
            return redirect('products:index') 

        except Exception as e:
            print(f"주문 저장 중 오류: {e}")
            # 에러 나면 다시 상품 페이지 보여주기 (멈춤 방지)
            context = {
                'product': product,
                'colors': colors,
                'error': f'주문 처리 중 오류가 발생했습니다: {str(e)}'
            }
            return render(request, 'products/shop.html', context)

    # 3. [GET 요청] 그냥 페이지에 들어왔을 때 (화면 보여주기)
    # ★★★ 이 줄은 if문 바깥(맨 앞, 왼쪽 벽에 붙어서)에 있어야 합니다! ★★★
    context = {
        'product': product,
        'colors': colors,  # <--- ★ 필수! 이게 넘어가야 색상 버튼과 이미지가 생깁니다.
        'initial_price': product.price,
    }
    return render(request, 'products/shop.html', context)

@csrf_exempt
# [1] AI 배경 제거 (최적화 버전)
def remove_background_ai(request):
    if request.method == 'POST':
            data = json.loads(request.body)
            image_data = data.get('image') # base64 문자열

            if not image_data:
                return JsonResponse({'status': 'fail', 'message': '이미지 데이터 없음'})

            # Base64 -> 이미지 변환
            format, imgstr = image_data.split(';base64,') 
            input_image = Image.open(BytesIO(base64.b64decode(imgstr)))

            # AI 처리 (rembg)
            output_image = remove(input_image)

            # 이미지 -> Base64 변환
            buffered = BytesIO()
            output_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return JsonResponse({'status': 'success', 'image': f"data:image/png;base64,{img_str}"})
    
    return JsonResponse({'status': 'fail', 'message': 'POST 요청이 아닙니다.'})
# ======================================================
# ★ [핵심 수정] 이메일 내용이 꽉 찬 주문 생성 함수
# ======================================================
# [주의] 이 함수 위에 import가 꼭 있어야 합니다.
# from django.db import transaction
# from django.contrib import messages
# from .models import ProductOption 

def order_create(request):
    if request.method == 'POST':
        # [기존 코드] 1. 데이터 수신
        customer_name = request.POST.get('customer_name', '-')
        phone = request.POST.get('phone', '-')
        address = request.POST.get('address', '-')
        product_name = request.POST.get('product_name', '')
        color_selected = request.POST.get('color_selected', '') 
        size_detail = request.POST.get('size_detail_text', '') # 예: "L", "XL"
        
        # [기존 코드] 숫자 데이터 처리
        total_qty_str = request.POST.get('total_quantity', '0')
        total_price_str = request.POST.get('total_price', '0')
        total_qty = int(total_qty_str.replace(',', '')) if total_qty_str else 0
        total_price = int(total_price_str.replace(',', '').replace('원', '')) if total_price_str else 0
        
        # [기존 코드] 작업지시서 데이터 받기
        tech_pack_raw = request.POST.get('tech_pack_data', '정보 없음')
        tech_pack = tech_pack_raw.replace('\n', '<br>')

        # [기존 코드] 4면 이미지 데이터
        images_data = {
            'front': request.POST.get('captured_front'),
            'back': request.POST.get('captured_back'),
            'left': request.POST.get('captured_left'),
            'right': request.POST.get('captured_right'),
        }
        
        # [기존 코드] 상품 객체 찾기
        product_obj = Product.objects.filter(name=product_name).first()
        if not product_obj: 
            product_obj = Product.objects.first() 
        
        # ============================================================
        # ★ [추가 기능 1] 재고 확인 및 차감 로직 (주문 생성 전 실행)
        # ============================================================
        try:
            # DB에서 해당 상품의 해당 사이즈 옵션 찾기
            selected_option = ProductOption.objects.filter(product=product_obj, size=size_detail).first()
            
            if selected_option:
                # 1. 재고 부족 체크
                if selected_option.stock < total_qty:
                    messages.error(request, f"죄송합니다. '{size_detail}' 사이즈의 재고가 부족합니다. (남은수량: {selected_option.stock}개)")
                    # 재고가 없으면 주문을 생성하지 않고 에디터 화면으로 돌려보냅니다.
                    return redirect('products:product_custom_editor', product_code=product_obj.code)
                
                # 2. 재고 차감 (트랜잭션으로 안전하게 처리)
                with transaction.atomic():
                    selected_option.stock -= total_qty
                    selected_option.save()
                    
        except Exception as e:
            # 재고 로직에서 에러가 나도 로그만 남기고 주문은 진행시킬지, 막을지 결정해야 합니다.
            # 여기서는 안전을 위해 로그를 찍고 계속 진행합니다.
            print(f"⚠️ 재고 처리 중 오류 발생 (주문은 진행됨): {e}")
        # ============================================================

        # [기존 코드] 주문번호 생성
        user = request.user if request.user.is_authenticated else None
        rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order_no = f"{datetime.now().strftime('%Y%m%d')}-{rand_str}"

        # [기존 코드] 2. DB 저장 (Order 생성)
        order = Order.objects.create(
            user=user,
            product=product_obj,
            order_no=order_no,
            customer_name=customer_name,
            contact_number=phone,
            shipping_address=address,
            quantity=total_qty,
            option_color=color_selected,
            option_size=size_detail,
            total_price=total_price,
            status='견적요청'
        )
        
        # ============================================================
        # ★ [추가 기능 2] 카카오톡 알림 발송 (주문 생성 직후)
        # ============================================================
        try:
            # [수정됨] 위에서 정의한 함수 이름(send_kakao_alimtalk)과 똑같이 맞췄습니다!
            send_kakao_alimtalk(phone, customer_name, order_no)
        except Exception as e:
            print(f"⚠️ 카카오톡 발송 실패: {e}")

        # [기존 코드] 3. 관리자 이메일 구성 (작업지시서 포함)
        subject = f"[주문 접수] {customer_name}님 - {product_name} (No.{order_no})"
        
        html_content = f"""
        <div style="font-family: 'Malgun Gothic', dotum, sans-serif; max-width: 700px; margin: 0 auto; border: 1px solid #ddd; padding: 20px;">
            <h2 style="color: #333; border-bottom: 2px solid #333; padding-bottom: 10px;">SEMODAN 주문서</h2>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 5px; font-weight: bold; width: 120px;">주문번호</td><td>{order_no}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">주문자/단체</td><td>{customer_name}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">연락처</td><td>{phone}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">배송지</td><td>{address}</td></tr>
            </table>
            
            <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; font-size: 16px;">상품 정보</h3>
                <p style="margin: 5px 0;"><strong>상품명:</strong> {product_name} ({color_selected})</p>
                <p style="margin: 5px 0;"><strong>수량/금액:</strong> {total_qty}벌 / {total_price:,}원</p>
                <p style="margin: 5px 0;"><strong>사이즈 상세:</strong> {size_detail}</p>
            </div>

            <div style="border: 1px solid #eee; padding: 15px; margin-bottom: 20px;">
                <h3 style="margin-top: 0; font-size: 16px; color: #d63031;">[작업 지시서 / 로고 규격]</h3>
                <div style="background: #333; color: #fff; padding: 15px; font-size: 14px; line-height: 1.6;">
                    {tech_pack}
                </div>
            </div>

            <h3>디자인 시안 (4면)</h3>
            <p style="font-size: 12px; color: #666;">* 이미지가 보이지 않으면 첨부파일을 확인해주세요.</p>
            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                <div style="text-align:center;"><img src="cid:front_img" style="width:100%; max-width:200px; border:1px solid #eee;"><br>앞면</div>
                <div style="text-align:center;"><img src="cid:back_img" style="width:100%; max-width:200px; border:1px solid #eee;"><br>뒷면</div>
            </div>
            <div style="display: flex; gap: 10px;">
                <div style="text-align:center;"><img src="cid:left_img" style="width:100%; max-width:200px; border:1px solid #eee;"><br>왼팔</div>
                <div style="text-align:center;"><img src="cid:right_img" style="width:100%; max-width:200px; border:1px solid #eee;"><br>오른팔</div>
            </div>
        </div>
        """
        
        # [기존 코드] 4. 메일 객체 생성 및 이미지 첨부
        msg = EmailMultiAlternatives(subject, "HTML을 지원하는 클라이언트에서 확인해주세요.", settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER])
        msg.attach_alternative(html_content, "text/html")

        # [기존 코드] 4면 캡쳐 이미지 첨부 (CID 연결)
        for key, data in images_data.items():
            if data and 'base64,' in data:
                try:
                    img_format, imgstr = data.split(';base64,') 
                    img_decoded = base64.b64decode(imgstr)
                    mime_img = MIMEImage(img_decoded)
                    mime_img.add_header('Content-ID', f'<{key}_img>')
                    msg.attach(mime_img)
                except Exception as e:
                    print(f"이미지 첨부 실패 ({key}): {e}")

        # [기존 코드] 5. 로고 원본 파일 첨부
        if 'logo_file' in request.FILES:
            files = request.FILES.getlist('logo_file') 
            for f in files:
                try: msg.attach(f.name, f.read(), f.content_type)
                except: pass

        # [기존 코드] 전송
        msg.send()
        
        # [기존 코드] 성공 페이지로 이동
        return redirect('products:order_success', order_no=order.order_no)
 
def order_success(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    return render(request, 'products/order_success.html', {'order': order, 'order_no': order.order_no, 'phone': order.contact_number})
def order_check(request):
    # 로그인 유저는 본인 것 확인
    if request.user.is_authenticated:
        my_orders = Order.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'products/order_check.html', {'orders': my_orders, 'is_member': True})
    
    # 비회원 검색 (전화번호)
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        # 전화번호로 검색
        orders = Order.objects.filter(contact_number=phone).order_by('-created_at')
        
        context = {'search': True, 'is_member': False, 'phone_input': phone}
        if orders.exists():
            context['orders'] = orders
        else:
            context['error'] = '해당 전화번호로 조회된 주문이 없습니다.'
            
        return render(request, 'products/order_check.html', context)
        
    return render(request, 'products/order_check.html', {'search': False, 'is_member': False})

def join_list(request):
    # 1. 문의글 가져오기 (최신순)
    # (만약 공지사항 기능을 넣었다면 .order_by('-is_pinned', '-created_at') 등으로 변경 가능)
    posts = JoinPost.objects.all().order_by('-created_at')
    
    # 2. ★ [추가] 베스트 리뷰 가져오기 
    # 조건: 별점 5점(rating=5)인 리뷰 중, 최신순으로 3개만 가져옴
    best_reviews = Review.objects.filter(rating=5).order_by('-created_at')[:3]
    
    return render(request, 'products/join.html', {
        'posts': posts, 
        'best_reviews': best_reviews # 템플릿으로 같이 보냄
    })

def join_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        author_name = request.POST.get('author_name')
        contact = request.POST.get('contact') # 연락처
        password = request.POST.get('password') # 비밀번호 (숫자 4자리)
        is_secret = request.POST.get('is_secret') == 'on'

        # 로그인한 회원이면 author에 저장, 아니면 None
        current_user = request.user if request.user.is_authenticated else None
        
        # 이름이 없으면 '익명' 처리
        if not author_name: 
            author_name = current_user.username if current_user else "익명"

        post = JoinPost.objects.create(
            author=current_user,
            author_name=author_name,
            password=password,      # 비회원 비밀번호 저장
            contact_number=contact, # 연락처 저장
            title=title,
            content=content,
            is_secret=is_secret,
        )
        
        # (이미지 저장 로직이 있다면 여기에 유지)
        
        return redirect('products:join_list') # 'qna' 대신 'join_list'로 통일

    return render(request, 'products/join_create.html')
@login_required(login_url='/common/login/') # 로그인은 필수
def review_create(request, product_code):
    product = get_object_or_404(Product, code=product_code)
    
    # ★ [핵심] "배송완료"된 주문이 있는지 확인 (없으면 튕겨냄)
    has_purchased = Order.objects.filter(
        user=request.user, 
        product=product, 
        status='배송완료' # 배송완료 상태만 리뷰 가능
    ).exists()

    if not has_purchased:
        # 주문 내역이 없으면 에러 메시지와 함께 상품 페이지로 돌려보냄
        # (메시지 띄우기는 자바스크립트나 messages 프레임워크 사용 가능하지만, 일단 리다이렉트)
        return redirect('products:product_custom_editor', product_code=product.code)

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            return redirect('products:product_custom_editor', product_code=product.code)
    else:
        form = ReviewForm()
    
    return render(request, 'products/review_form.html', {'form': form, 'product': product})
def join_answer_create(request, pk):
    post = get_object_or_404(JoinPost, pk=pk) # ★ 여기가 핵심 수정 (Join -> JoinPost)
    
    if request.method == 'POST':
        admin_code = request.POST.get('admin_code') # 입력한 관리자 코드
        content = request.POST.get('content') # 답변 내용
        
        # 관리자 코드 확인 (4678)
        if admin_code == '4678':
            # 답변 저장
            Answer.objects.create(post=post, content=content)
        else:
            # 코드가 틀리면 pass
            pass 
            
    return redirect('products:join_detail', pk=pk)

# products/views.py 맨 아래에 추가

def join_action(request, pk):
    post = get_object_or_404(JoinPost, pk=pk) # 게시글 가져오기
    
    if request.method == 'POST':
        admin_code = request.POST.get('admin_code') # 입력한 비밀번호
        action_type = request.POST.get('action_type') # 기능 종류 (delete 등)
        
        # 관리자 코드(4678)가 맞고, 삭제 요청이면
        if admin_code == '4678' and action_type == 'delete':
            post.delete() # DB에서 삭제
            return redirect('products:qna') # 목록으로 이동
            
    # 비밀번호가 틀리면 다시 상세 페이지로
    return redirect('products:join_detail', pk=pk)

# products/views.py
def policy(request):
    return render(request, 'products/policy.html')
# products/views.py

# 주문 취소 기능
def order_cancel(request, order_no):
    if request.method == 'POST':
        order = get_object_or_404(Order, order_no=order_no)
        
        # 취소 가능 상태인지 확인
        if order.status in ['견적요청', '결제요청', '결제완료', '입금대기']:
            order.status = '주문취소'
            order.save()
            
            # ★ 메일 발송 로직 (강제 실행 및 에러 출력)
            try:
                subject = f"[긴급] 주문 취소 알림 - {order.customer_name}"
                message = f"""
                고객님이 주문을 취소했습니다.
                
                주문번호: {order.order_no}
                고객명: {order.customer_name}
                연락처: {order.contact_number}
                상품명: {order.product.name}
                취소금액: {order.total_price}원
                """
                
                # 보내는 사람: settings에 설정한 네이버/구글 계정
                # 받는 사람: settings에 설정한 네이버/구글 계정 (우진님 본인)
                send_mail(
                    subject, 
                    message, 
                    settings.EMAIL_HOST_USER, 
                    [settings.EMAIL_HOST_USER], # 받는 사람 리스트
                    fail_silently=False # ★ 에러나면 화면에 띄우도록 설정 (디버깅용)
                )
                print("메일 발송 시도 완료") # 터미널 로그 확인용
                
            except Exception as e:
                print(f"메일 발송 에러 발생: {e}") # 터미널에서 이 메시지가 뜨는지 확인하세요

    return redirect('products:order_check')

# 리뷰 작성 기능 (간단 버전)
def review_create(request, product_code):
    product = get_object_or_404(Product, code=product_code)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user if request.user.is_authenticated else None
            # 비회원 리뷰 처리가 복잡하므로 일단 회원만, 혹은 user=None 허용
            review.save()
            return redirect('products:product_custom_editor', product_code=product.code)
    else:
        form = ReviewForm()
    
    return render(request, 'products/review_form.html', {'form': form, 'product': product})

def join_detail(request, pk):
    post = get_object_or_404(JoinPost, pk=pk)
    
    # 비밀글 권한 체크
    if post.is_secret:
        # 1. 관리자(superuser)거나 작성자 본인(로그인한 경우)이면 통과
        if request.user.is_superuser or (request.user.is_authenticated and request.user == post.author):
            pass 
        
        # 2. 비회원이거나 다른 사람이면? -> 비밀번호 입력 확인
        else:
            # 사용자가 입력한 비밀번호 확인 (POST 요청으로 들어옴)
            input_pw = request.POST.get('password_check')
            
            # 입력한 게 없거나 틀리면 -> 비밀번호 입력 화면을 보여줌
            if input_pw != post.password:
                return render(request, 'products/password_check.html', {'post': post})
            
            # 맞으면 통과! (아래 코드로 진행)

    # (답변 가져오기 등 기존 코드 유지)
    return render(request, 'products/join_detail.html', {'post': post})

# [products/views.py] 파일 맨 아래에 추가

def cancel_payment(request, order_no):
    # 1. 주문 정보 가져오기
    order = get_object_or_404(Order, order_no=order_no)
    
    if request.method == 'POST':
        # 2. 포트원 API 키 (관리자 페이지 > 식별코드/API Keys 에서 확인)
        IMP_KEY = '6541577553860413' 
        IMP_SECRET = 'O29AKkw8RGjko9oENqe5BceWWpxhQwQsRk50I42rQ31YednmAdomRAjYY9x620i2fPsxHBjQqyT8FNiZ'

        # 3. 액세스 토큰(Access Token) 발급 받기
        url = "https://api.iamport.kr/users/getToken"
        headers = {'Content-Type': 'application/json'}
        data = {'imp_key': IMP_KEY, 'imp_secret': IMP_SECRET}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            access_token = response.json()['response']['access_token']
        except Exception as e:
            return JsonResponse({'message': '토큰 발급 실패', 'error': str(e)})

        # 4. 결제 취소 요청 보내기
        cancel_url = "https://api.iamport.kr/payments/cancel"
        cancel_headers = {'Authorization': access_token}
        cancel_data = {
            'imp_uid': order.imp_uid,    # 결제 고유번호
            'reason': '고객(또는 관리자) 요청에 의한 취소', # 취소 사유
            'checksum': order.total_price # 취소 금액 검증
        }
        
        cancel_response = requests.post(cancel_url, headers=cancel_headers, data=cancel_data)
        cancel_json = cancel_response.json()

        # 5. 결과 처리
        if cancel_json['code'] == 0:
            # 취소 성공 시 DB 업데이트
            order.status = 'CANCELED' # 모델에 status 필드가 있다면
            order.save()
            return JsonResponse({'message': '환불 처리가 완료되었습니다.'})
        else:
            return JsonResponse({'message': '환불 실패', 'error': cancel_json['message']})

    return JsonResponse({'message': '잘못된 요청입니다.'})