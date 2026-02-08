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
from django.db.models import Q
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
from .forms import ReviewForm,OrderForm, JoinForm, PartnershipForm
from .models import Product, Order, JoinPost, ProductColor, Answer, Review, ProductOption, Partnership, PartnershipImage
from django.http import HttpResponse
from django.core.mail import EmailMessage
import mimetypes

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

# [views.py]의 order_create 함수를 이걸로 통째로 바꾸세요!

# views.py 파일을 열고 order_create 함수를 이걸로 통째로 교체하세요!

def order_create(request):
    if request.method == 'POST':
        try:
            # --------------------------------------------------------
            # 1. 데이터 수신 (기존과 동일)
            # --------------------------------------------------------
            customer_name = request.POST.get('customer_name', '-')
            phone = request.POST.get('phone', '-')
            address = request.POST.get('address', '-')
            customer_email = request.POST.get('customer_email', '') # 이메일 받기

            product_name = request.POST.get('product_name', '')
            color_selected = request.POST.get('color_selected', '') 
            size_detail = request.POST.get('size_detail_text', '') 
            
            # 숫자 데이터 처리
            total_qty_str = request.POST.get('total_quantity', '0')
            total_price_str = request.POST.get('total_price', '0')
            try:
                total_qty = int(total_qty_str.replace(',', ''))
                total_price = int(total_price_str.replace(',', '').replace('원', ''))
            except:
                total_qty = 1
                total_price = 0
            
            # 작업지시서 데이터 (관리자용)
            tech_pack_raw = request.POST.get('tech_pack_data', '정보 없음')
            tech_pack = tech_pack_raw.replace('\n', '<br>')

            # 4면 이미지 데이터 (관리자용)
            images_data = {
                'front': request.POST.get('captured_front'),
                'back': request.POST.get('captured_back'),
                'left': request.POST.get('captured_left'),
                'right': request.POST.get('captured_right'),
            }
            
            # 상품 객체 찾기
            product_obj = Product.objects.filter(name=product_name).first()
            if not product_obj: product_obj = Product.objects.first() 
            
            # --------------------------------------------------------
            # 2. 재고 확인 및 차감
            # --------------------------------------------------------
            try:
                selected_option = ProductOption.objects.filter(product=product_obj, size=size_detail).first()
                if selected_option:
                    if selected_option.stock < total_qty:
                        messages.error(request, f"재고 부족 (남은수량: {selected_option.stock}개)")
                        return redirect('products:product_custom_editor', product_code=product_obj.code)
                    
                    with transaction.atomic():
                        selected_option.stock -= total_qty
                        selected_option.save()
            except Exception as e:
                print(f"⚠️ 재고 처리 오류: {e}")

            # --------------------------------------------------------
            # 3. 주문 저장 (DB)
            # --------------------------------------------------------
            user = request.user if request.user.is_authenticated else None
            rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            order_no = f"{datetime.now().strftime('%Y%m%d')}-{rand_str}"

            order = Order.objects.create(
                user=user,
                product=product_obj,
                order_no=order_no,
                customer_name=customer_name,
                contact_number=phone,
                customer_email=customer_email,
                shipping_address=address,
                quantity=total_qty,
                option_color=color_selected,
                option_size=size_detail,
                total_price=total_price,
                status='견적요청'
            )

            # ========================================================
            # ★ [메일 발송 1] 고객에게 보내는 "심플한 안내 메일"
            # ========================================================
            # ========================================================
            # ★ [메일 발송 1] 고객에게 보내는 메일 (이미지 첨부 기능 추가됨)
            # ========================================================
            if customer_email:
                try:
                    subject_cust = f"[세모단] {customer_name}님, 주문이 정상 접수되었습니다."
                    html_cust = f"""
                    <div style="padding:20px; border:1px solid #ddd; max-width:600px;">
                        <h2 style="color:#ff6b00;">SEMODAN</h2>
                        <h3>{customer_name}님, 주문해주셔서 감사합니다.</h3>
                        <p>고객님의 주문이 정상적으로 접수되었습니다.</p>
                        <p>디자인하신 <strong>시안 이미지는 첨부파일</strong>로 확인하실 수 있습니다.</p>
                        <hr>
                        <p><strong>주문번호:</strong> {order_no}</p>
                        <p><strong>상품명:</strong> {product_name}</p>
                        <p><strong>결제금액:</strong> {total_price:,}원</p>
                        <hr>
                        <p>현재 담당자가 내용을 확인하고 있습니다.<br>
                        빠르게 제작하여 배송해 드리겠습니다.</p>
                    </div>
                    """
                    
                    # 1. 이메일 객체 생성 (EmailMultiAlternatives 사용)
                    msg = EmailMultiAlternatives(subject_cust, "주문이 접수되었습니다.", settings.EMAIL_HOST_USER, [customer_email])
                    msg.attach_alternative(html_cust, "text/html") # HTML 본문 설정

                    # 2. ★ 이미지 파일 변환 및 첨부 (핵심!)
                    for view_name, base64_data in images_data.items():
                        if base64_data and "base64," in base64_data:
                            try:
                                # "data:image/jpeg;base64,..." 헤더 제거
                                img_format, imgstr = base64_data.split(';base64,') 
                                ext = img_format.split('/')[-1] # png, jpeg 등 확장자 추출
                                
                                # Base64 디코딩 (문자열 -> 이미지 파일 데이터)
                                file_data = base64.b64decode(imgstr)
                                
                                # 메일에 첨부 (파일명, 데이터, MIME타입)
                                # 예: front_design.png
                                msg.attach(f'{view_name}_design.{ext}', file_data, f'image/{ext}')
                            except Exception as e:
                                print(f"이미지 첨부 중 오류({view_name}): {e}")

                    # 3. 전송
                    msg.send(fail_silently=True)
                    print("✅ 고객용 메일 발송 성공 (이미지 첨부됨)")

                except Exception as e:
                    print(f"❌ 고객용 메일 실패: {e}")


            # ========================================================
            # ★ [메일 발송 2] 관리자(나)에게 보내는 "상세 작업지시서" (기존 코드 복원)
            # ========================================================
            try:
                subject_admin = f"[주문 접수] {customer_name}님 - {product_name} (No.{order_no})"
                
                # 관리자용 상세 HTML (테이블 + 작업지시서 포함)
                html_admin = f"""
                <div style="font-family: 'Malgun Gothic', sans-serif; max-width: 700px; border: 1px solid #333; padding: 20px;">
                    <h2 style="background:#333; color:#fff; padding:10px;">SEMODAN 주문서 (관리자용)</h2>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; border: 1px solid #ddd;">
                        <tr><td style="padding: 8px; border:1px solid #ddd; font-weight: bold; background:#f0f0f0;">주문번호</td><td style="padding: 8px; border:1px solid #ddd;">{order_no}</td></tr>
                        <tr><td style="padding: 8px; border:1px solid #ddd; font-weight: bold; background:#f0f0f0;">주문자</td><td style="padding: 8px; border:1px solid #ddd;">{customer_name} ({phone})</td></tr>
                        <tr><td style="padding: 8px; border:1px solid #ddd; font-weight: bold; background:#f0f0f0;">이메일</td><td style="padding: 8px; border:1px solid #ddd;">{customer_email}</td></tr>
                        <tr><td style="padding: 8px; border:1px solid #ddd; font-weight: bold; background:#f0f0f0;">배송지</td><td style="padding: 8px; border:1px solid #ddd;">{address}</td></tr>
                        <tr><td style="padding: 8px; border:1px solid #ddd; font-weight: bold; background:#f0f0f0;">주문내역</td><td style="padding: 8px; border:1px solid #ddd;">
                            {product_name} / {color_selected}<br>
                            <strong>{size_detail}</strong> (총 {total_qty}벌)
                        </td></tr>
                        <tr><td style="padding: 8px; border:1px solid #ddd; font-weight: bold; background:#f0f0f0;">결제금액</td><td style="padding: 8px; border:1px solid #ddd; color:red; font-weight:bold;">{total_price:,}원</td></tr>
                    </table>

                    <div style="background: #fff3cd; padding: 15px; border: 1px solid #ffeeba; margin-bottom: 20px;">
                        <h3 style="margin-top: 0; font-size: 16px; color: #856404;">[작업 지시서 (Tech Pack)]</h3>
                        <div style="font-size: 14px; line-height: 1.6;">{tech_pack}</div>
                    </div>

                    <h3>디자인 시안 (4면)</h3>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <div style="text-align:center; border:1px solid #eee; padding:5px;"><img src="cid:front_img" style="width:150px;"><br>앞면</div>
                        <div style="text-align:center; border:1px solid #eee; padding:5px;"><img src="cid:back_img" style="width:150px;"><br>뒷면</div>
                        <div style="text-align:center; border:1px solid #eee; padding:5px;"><img src="cid:left_img" style="width:150px;"><br>왼팔</div>
                        <div style="text-align:center; border:1px solid #eee; padding:5px;"><img src="cid:right_img" style="width:150px;"><br>오른팔</div>
                    </div>
                </div>
                """

                # 관리자에게만 발송
                msg = EmailMultiAlternatives(subject_admin, "HTML 메일입니다.", settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER])
                msg.attach_alternative(html_admin, "text/html")

                # 이미지 첨부 (CID 방식 - 관리자 메일에만 첨부하면 됨)
                for key, data in images_data.items():
                    if data and 'base64,' in data:
                        try:
                            img_format, imgstr = data.split(';base64,') 
                            img_decoded = base64.b64decode(imgstr)
                            mime_img = MIMEImage(img_decoded)
                            mime_img.add_header('Content-ID', f'<{key}_img>')
                            msg.attach(mime_img)
                        except: pass
                
                # 로고 파일 첨부
                if 'logo_file' in request.FILES:
                    for f in request.FILES.getlist('logo_file'):
                        msg.attach(f.name, f.read(), f.content_type)

                msg.send() # 관리자 전송!
                print("✅ 관리자용 상세 메일 발송 성공")

            except Exception as e:
                print(f"❌ 관리자용 메일 실패: {e}")
            
            # --------------------------------------------------------
            # 4. 완료 페이지로 이동
            # --------------------------------------------------------
            return redirect('products:order_success', order_no=order.order_no)

        except Exception as e:
            print(f"🚫 주문 생성 중 에러 발생: {e}")
            return redirect('products:index')
        
def order_success(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    return render(request, 'products/order_success.html', {'order': order, 'order_no': order.order_no, 'phone': order.contact_number})

def order_check(request):
    # 1. 로그인 유저는 본인 것 확인
    if request.user.is_authenticated:
        my_orders = Order.objects.filter(user=request.user).order_by('-created_at')
        return render(request, 'products/order_check.html', {'orders': my_orders, 'is_member': True})

    # 2. 비회원 조회
    if request.method == 'POST':
        # [수정 포인트] html에서 'phone'으로 보내든 'contact_number'로 보내든 둘 다 받음
        raw_number = request.POST.get('phone') or request.POST.get('contact_number')
        name = request.POST.get('name') # 이름 입력칸이 있다면 가져옴

        if raw_number:
            # 하이픈 제거
            clean_number = raw_number.replace('-', '').strip()
            
            # 하이픈 포함 버전 생성
            if len(clean_number) == 11:
                hyphen_number = f"{clean_number[:3]}-{clean_number[3:7]}-{clean_number[7:]}"
            else:
                hyphen_number = clean_number

            # 조회 (이름 필드가 화면에 없으면 번호로만 조회하도록 처리)
            if name:
                orders = Order.objects.filter(
                    Q(customer_name=name) & 
                    (Q(contact_number=clean_number) | Q(contact_number=hyphen_number))
                ).order_by('-created_at')
            else:
                # 이름 입력칸이 화면에 없을 경우 번호로만 검색
                orders = Order.objects.filter(
                    Q(contact_number=clean_number) | Q(contact_number=hyphen_number)
                ).order_by('-created_at')

            return render(request, 'products/order_check.html', {'orders': orders})

    return render(request, 'products/order_check.html')

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

# products/views.py

def join_create(request):
    if request.method == 'POST':
        # 1. 데이터 수집 (HTML의 name 속성과 일치시켜야 합니다)
        name = request.POST.get('author_name', '익명') # HTML에 author_name으로 되어있음
        title = request.POST.get('title')
        content = request.POST.get('content')
        password = request.POST.get('password', '').strip()
        is_secret = request.POST.get('is_secret') == 'on'
        
        # 입점 문의 데이터 (파트너십에서 보낼 경우)
        phone = request.POST.get('contact', '').strip()
        if not phone:
            phone = "미입력"
        category = request.POST.get('category')
        hope_price = request.POST.get('hope_price')

        # 비밀번호 기본값 설정
        if not password:
            password = "0411"

        # 2. 내용 구성 (입점 정보가 있다면 합치기)
        extra_info = ""
        if category or phone != "미입력" or hope_price:
            extra_info = f"[카테고리: {category}]\n[연락처: {phone}]\n[희망단가: {hope_price}]\n\n"
        
        combined_content = f"{extra_info}{content}".strip()

        # 3. DB 저장 (딱 한 번만 실행)
        try:
            JoinPost.objects.create(
                author=request.user if request.user.is_authenticated else None,
                author_name=name,
                title=title if title else f"{name}님의 문의입니다.",
                content=combined_content,
                password=password,
                is_secret=is_secret
            )
        except Exception as e:
            print(f"DB 저장 실패: {e}")

        # 4. 관리자 메일 발송asdf
        subject = f"[세모단 문의 알림] {name}님의 글: {title}"
        send_mail(subject, combined_content, settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER], fail_silently=True)

        return redirect('products:qna')

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
        
        # 관리자 코드 확인 (0411)
        if admin_code == '0411':
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
        if admin_code == '0411' and action_type == 'delete':
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

# 1. [신규] 주문 상세 페이지 (배송 정보 크게 보기)
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # 주문자 본인인지 확인하는 로직 (세션 등으로 확인 권장)
    # if request.user.email != order.customer_email: ... 
    
    return render(request, 'products/order_detail.html', {'order': order})

# 2. [신규] 입점 문의 페이지 (이메일 발송 포함)
# products/views.py
# products/views.py

def partnership(request):
    if request.method == 'POST':
        form = PartnershipForm(request.POST, request.FILES)
        files = request.FILES.getlist('detail_images') 
        
        if form.is_valid():
            try:
                # 1. DB 저장
                partnership = form.save() 
                for f in files:
                    PartnershipImage.objects.create(partnership=partnership, image=f)
                
                # 2. 이메일 내용 작성
                subject = f"[입점문의] {partnership.brand_name} (담당: {partnership.manager_name})"
                message = f"""
                업체명: {partnership.brand_name}
                사업자번호: {partnership.business_number}
                담당자: {partnership.manager_name}
                연락처: {partnership.contact}
                이메일: {partnership.email}
                위치: {partnership.location}
                
                내용:
                {partnership.description}
                """
                
                # 3. 이메일 객체 생성 및 파일 첨부
                email = EmailMessage(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [settings.EMAIL_HOST_USER],
                )
                
                if partnership.image:
                    partnership.image.open('rb')
                    mime_type, _ = mimetypes.guess_type(partnership.image.name)
                    if mime_type is None: mime_type = 'application/octet-stream'
                    email.attach(partnership.image.name, partnership.image.read(), mime_type)

                for f in files:
                    f.seek(0)
                    mime_type, _ = mimetypes.guess_type(f.name)
                    if mime_type is None: mime_type = 'application/octet-stream'
                    email.attach(f.name, f.read(), mime_type)
                
                # 4. 전송 (실패해도 유저에겐 성공한 척 보여주고, 서버 로그에만 남김)
                email.send(fail_silently=False)
                
            except Exception as e:
                # [배포용 수정] 에러가 나면 서버(터미널)에만 출력하고, 고객에겐 그냥 넘어감
                print(f"❌ 이메일 전송 실패: {e}")
                # 필요하다면 여기에 'messages.error(request, ...)' 등을 추가할 수 있음

            # 성공하든 메일만 실패하든 목록으로 이동
            return redirect('products:product_list') 
            
        else:
            # 폼 입력 실수 시 다시 작성 페이지로 (에러 내용은 form 안에 들어있음)
            return render(request, 'products/partnership.html', {'form': form})
            
    else:
        form = PartnershipForm()
    
    return render(request, 'products/partnership.html', {'form': form})


def join_detail(request, pk):
    post = get_object_or_404(JoinPost, pk=pk)
    
    # 비밀글이 아니면 -> 비밀번호 체크 없이 바로 통과!
    if not post.is_secret:
        return render(request, 'products/join_detail.html', {'post': post})
    
    # 비밀글이면 -> 비밀번호 입력 페이지로 (기존 로직 유지)
    # (기존에 작성하신 비밀번호 체크 로직이 있다면 여기 연결)
    if request.method == 'POST':
        input_password = request.POST.get('password')
        if input_password == post.password:
            return render(request, 'products/join_detail.html', {'post': post})
        else:
            return render(request, 'products/join_password.html', {'post': post, 'error': '비밀번호가 일치하지 않습니다.'})
            
    return render(request, 'products/join_password.html', {'post': post})

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
