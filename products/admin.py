from django.contrib import admin
from .models import Product, ProductColor, ProductOption, Order, JoinPost, Profile, Review

# 1. 색상 옵션 (이미지)
class ProductColorInline(admin.StackedInline): 
    model = ProductColor
    extra = 1
    verbose_name = "색상 옵션 (4면 이미지)"
    verbose_name_plural = "색상 옵션 추가"

# 2. ★ [핵심] 사이즈 & 재고 옵션 (엑셀처럼 입력)
class ProductOptionInline(admin.TabularInline):
    model = ProductOption
    extra = 1
    fields = ['color', 'size', 'stock']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'priority', 'code']
    search_fields = ('name', 'code')
    list_editable = ['priority']
    ordering = ['-priority', '-id']
    
    # ★ 색상과 재고 입력칸을 동시에 보여줍니다
    inlines = [ProductColorInline, ProductOptionInline] 
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'code', 'original_price', 'price', 'description', 'image', 'detail_image')
        }),
    )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # 1. 목록에 보여줄 항목들 (주문번호, 고객명, 상품명, 가격, 상태, 날짜)
    list_display = ['order_no', 'customer_name', 'product', 'total_price', 'status', 'created_at']
    
    # 2. ★ 목록에서 바로 '상태(status)'를 수정할 수 있게 만듦
    list_editable = ['status']
    
    # 3. 우측에 필터 생성 (상태별, 날짜별로 모아보기)
    list_filter = ['status', 'created_at']
    
    # 4. 검색창 생성 (주문번호, 이름, 연락처로 검색 가능)
    search_fields = ['order_no', 'customer_name', 'contact_number']
    
    # 5. 날짜 기준 내림차순 정렬 (최신 주문이 위로)
    ordering = ['-created_at']
    list_editable = ['status']
    
admin.site.register(Review)
admin.site.register(JoinPost)
admin.site.register(Profile)