from django.contrib import admin
from .models import Product, Inventory, ProductImage 
# products/admin.py (기존 코드 아래에 추가)
from .models import Announcement
# ----------------------------------------------------
# 1. Inline 정의: 상품 등록/수정 시 재고를 함께 관리하기 위한 설정
# ----------------------------------------------------
class InventoryInline(admin.StackedInline):
    # Inventory 모델을 Product 모델 내부에 통합하여 보여줍니다.
    model = Inventory
    # 재고 수량 필드만 표시
    fields = ['stock_quantity'] 
    max_num = 1  # 하나의 상품에는 하나의 재고만 존재해야 합니다.
    can_delete = False
# ----------------------------------------------------
# 1.1. Inline 정의: 상품 등록/수정 시 상세 이미지를 함께 관리하기 위한 설정
# ----------------------------------------------------
# TabularInline을 사용하여 이미지를 테이블 형태로 보여줍니다. (더 컴팩트함)
class ProductImageInline(admin.TabularInline):
    # ProductImage 모델을 Product 모델 내부에 통합하여 보여줍니다.
    model = ProductImage
    # 최소 1장의 이미지는 필수로 업로드하도록 설정 (대표 이미지 역할)
    extra = 1 
    # 최대 5장까지 업로드 가능하도록 제한 (원하는 숫자로 조정 가능)
    max_num = 5
        # 이미지 파일 필드만 표시
    fields = ['image', 'order']
# ----------------------------------------------------
# 2. Product 모델의 최종 Admin 설정 (Inventory 통합)
# ----------------------------------------------------
class ProductAdminWithInventory(admin.ModelAdmin):
    # 목록 페이지에 표시할 필드: 이름, 가격, 재고(메서드를 통해 가져옴)
    list_display = ('name', 'price', 'get_stock', 'created_at') 
    # 검색 가능 필드
    search_fields = ('name', 'description')
    # 필터 옵션
    list_filter = ('created_at',)
    
    # 상품 등록/수정 페이지에 InventoryInline과 ProductImageInline을 모두 추가합니다.
    inlines = [InventoryInline, ProductImageInline] # <--- 이 부분을 수정/추가해야 함

    # 목록에서 재고 수량을 직접 보여주기 위한 커스텀 메서드
    def get_stock(self, obj):
        # 재고 정보가 있다면 수량을 반환, 없다면 N/A를 반환
        return obj.inventory.stock_quantity if hasattr(obj, 'inventory') else 'N/A'
    get_stock.short_description = '현재 재고'

# ----------------------------------------------------
# 3. 모델 등록 (중복 제거)
# ----------------------------------------------------
# Product 모델을 최종 설정 클래스(ProductAdminWithInventory)로 한 번만 등록합니다.
admin.site.register(Product, ProductAdminWithInventory)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'short_description', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'content')