# products/models.py
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# 1. 상품 (Product)
class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='상품명')
    description = models.TextField(verbose_name='상품 설명')
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='가격 (원)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    class Meta:
        verbose_name = '상품'
        verbose_name_plural = '상품 목록'
    def __str__(self):
        return self.name

# 2. 재고 (Inventory)
class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, verbose_name='상품', primary_key=True)
    stock_quantity = models.IntegerField(default=0, verbose_name='재고 수량')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='최종 업데이트')
    class Meta:
        verbose_name = '재고'
        verbose_name_plural = '재고 관리'
    def __str__(self):
        return f"{self.product.name} - 재고: {self.stock_quantity}"

# 3. 상품 상세 이미지 (ProductImage)
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='상품')
    image = models.ImageField(upload_to='products/details/%Y/%m/%d/', verbose_name='상세 이미지')
    order = models.PositiveIntegerField(default=1, verbose_name='표시 순서')
    class Meta:
        verbose_name = '상세 이미지'
        verbose_name_plural = '상세 이미지 목록'
        ordering = ['product', 'order']
    def __str__(self):
        return f"{self.product.name} - 이미지 #{self.order}"

# 4. 공고 (Announcement)
class Announcement(models.Model):
    title = models.CharField(max_length=200, verbose_name='공고 제목')
    short_description = models.CharField(max_length=300, verbose_name='한줄 소개')
    content = models.TextField(verbose_name='상세 내용')
    image = models.ImageField(upload_to='announcements/%Y/%m/', verbose_name='썸네일', blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name='모집중 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    class Meta:
        verbose_name = '모집 공고'
        verbose_name_plural = '모집 공고 관리'
        ordering = ['-created_at']
    def __str__(self):
        return self.title

# ====================================================
# [수정됨] 5. Q&A 게시판 모델
# ====================================================
class JoinPost(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    author_name = models.CharField(max_length=20, default="익명")
    is_pinned = models.BooleanField(default=False)
    
    # [삭제됨] image 필드는 여기서 지웁니다! (아래 JoinPostImage 모델에서 관리)
    
    created_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return self.title

# [새로 추가] 게시글에 첨부된 다중 이미지
class JoinPostImage(models.Model):
    post = models.ForeignKey(JoinPost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='qna_images/')
    
    def __str__(self):
        return f"이미지 - {self.post.title}"

class JoinAnswer(models.Model):
    post = models.ForeignKey(JoinPost, on_delete=models.CASCADE, related_name='answers')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    def __str__(self):
        return f"답변: {self.content[:10]}"

# ----------------------------------------------------
# 시그널
# ----------------------------------------------------
@receiver(post_save, sender=Product)
def create_inventory(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.create(product=instance)
@receiver(post_save, sender=Product)
def save_inventory(sender, instance, **kwargs):
    try:
        instance.inventory.save()
    except Inventory.DoesNotExist:
        pass