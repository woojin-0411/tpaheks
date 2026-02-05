from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

# 1. 상품 기본 정보
class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="상품명")
    code = models.CharField(max_length=50, unique=True, verbose_name="상품코드")
    original_price = models.IntegerField(default=0, verbose_name="정가")
    price = models.IntegerField(verbose_name="판매가")
    description = models.TextField(blank=True, verbose_name="상품설명 (짧은)")
    priority = models.IntegerField(default=0, verbose_name="노출 우선순위 (높을수록 상단)")
    image = models.ImageField(upload_to='products/', verbose_name="대표 썸네일")
    detail_image = models.ImageField(upload_to='products/details/', blank=True, null=True, verbose_name="상세페이지 (공통)")

    def __str__(self):
        return self.name
    
    def get_discount_rate(self):
        if self.original_price > self.price:
            return int((self.original_price - self.price) / self.original_price * 100)
        return 0

# ★ [핵심] 상품 옵션 (사이즈 & 재고 관리)
class ProductOption(models.Model):
    # ★ related_name='options' 부분이 핵심입니다!
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='options') 
    color = models.CharField(max_length=50, verbose_name="색상")
    size = models.CharField(max_length=20, verbose_name="사이즈")
    stock = models.IntegerField(default=0, verbose_name="재고수량")

    def __str__(self):
        return f"{self.product.name} - {self.color} / {self.size}"

# 2. 색상 옵션
class ProductColor(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='colors')
    color_name = models.CharField(max_length=50, verbose_name="색상명")
    image_front = models.ImageField(upload_to='products/views/', verbose_name="앞면")
    image_back = models.ImageField(upload_to='products/views/', blank=True, null=True, verbose_name="뒷면")
    image_left = models.ImageField(upload_to='products/views/', blank=True, null=True, verbose_name="왼팔")
    image_right = models.ImageField(upload_to='products/views/', blank=True, null=True, verbose_name="오른팔")

    def __str__(self):
        return f"{self.product.name} - {self.color_name}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, verbose_name='연락처')
    address = models.CharField(max_length=255, verbose_name='주소')

class Order(models.Model):
    STATUS_CHOICES = [
        ('결제대기', '결제대기'),
        ('결제완료', '결제완료'),
        ('제작중', '제작중'),
        ('배송중', '배송중'),
        ('배송완료', '배송완료'),
        ('주문취소', '주문취소'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    order_no = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=100, default="-", verbose_name="주문자")
    contact_number = models.CharField(max_length=20)
    shipping_address = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    # [핵심] 이 'size' 필드가 없어서 에러가 났던 겁니다!
    size = models.CharField(max_length=10, verbose_name="사이즈", default="FREE")
    option_color = models.CharField(max_length=50, blank=True)
    option_size = models.TextField(blank=True) # 선택한 사이즈 (S, M 등)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='결제대기', 
        verbose_name="주문상태"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.IntegerField(default=0)
    # 요청사항 필드가 없다면 추가 (views.py에서 쓰임)
    requests = models.TextField(blank=True, null=True, verbose_name="요청사항")
    customer_email = models.EmailField(max_length=100, blank=True, null=True, verbose_name="고객 이메일")
    carrier = models.CharField(max_length=50, blank=True, null=True, verbose_name="택배사") # 예: CJ대한통운
    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="송장번호")
    def __str__(self):
        return f"{self.order_no} - {self.customer_name}"

class JoinPost(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    author_name = models.CharField(max_length=50)
    password = models.CharField(max_length=4, blank=True, null=True, verbose_name="비밀번호")
    contact_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="연락처")
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_secret = models.BooleanField(default=False, verbose_name="비밀글")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Review(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)
    content = models.TextField()
    image = models.ImageField(upload_to='reviews/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    like_count = models.IntegerField(default=0, verbose_name="추천수")

    class Meta:
        ordering = ['-like_count', '-created_at']

class Answer(models.Model):
    post = models.ForeignKey(JoinPost, on_delete=models.CASCADE, related_name='answers')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

# [수정] Partnership 모델 업데이트
class Partnership(models.Model):
    brand_name = models.CharField(max_length=100, verbose_name="업체명(브랜드명)")
    # 1. [신규] 사업자 번호 추가
    business_number = models.CharField(max_length=20, verbose_name="사업자 등록번호", blank=True, null=True) 
    
    manager_name = models.CharField(max_length=50, verbose_name="담당자 이름")
    contact = models.CharField(max_length=50, verbose_name="연락처")
    email = models.EmailField(verbose_name="이메일")
    location = models.CharField(max_length=200, verbose_name="업체 위치")
    description = models.TextField(verbose_name="입점 희망 제품/설명")
    
    # 대표 사진 (한 장)
    image = models.ImageField(upload_to='partnership/main/', blank=True, null=True, verbose_name="대표 사진")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.brand_name
    
    class Meta:
        verbose_name = "입점 문의"
        verbose_name_plural = "입점 문의 목록"

# 2. [신규] 상세 사진들을 저장할 별도 모델 (여러 장 가능하게 함)
class PartnershipImage(models.Model):
    partnership = models.ForeignKey(Partnership, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='partnership/details/', verbose_name="상세 사진")

    def __str__(self):
        return f"{self.partnership.brand_name} - 상세사진"