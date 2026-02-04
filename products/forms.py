from django import forms
from allauth.account.forms import SignupForm
from .models import Profile, Review, Order, JoinPost, Partnership

# 1. 입점 문의 폼
class PartnershipForm(forms.ModelForm):
    class Meta:
        model = Partnership
        fields = ['brand_name', 'business_number', 'manager_name', 'contact', 'email', 'location', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6, 'placeholder': '입점하고 싶은 제품이나 브랜드 소개, 혹은 궁금한 점을 자유롭게 적어주세요.'}),
        }

# 2. Q&A 비밀글 폼
class JoinForm(forms.ModelForm):
    class Meta:
        model = JoinPost
        fields = ['title', 'author_name', 'contact_number', 'password', 'is_secret', 'content']
        widgets = {
            'password': forms.PasswordInput(attrs={'placeholder': '비밀글 체크 시 필수 입력'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_secret = cleaned_data.get('is_secret')
        password = cleaned_data.get('password')

        if is_secret and not password:
            self.add_error('password', "비밀글로 설정하려면 비밀번호를 입력해야 합니다.")
        
        return cleaned_data

# 3. 주문 폼
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['quantity', 'size', 'customer_email', 'shipping_address', 'contact_number']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1, 'value': 1, 'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-select'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '주문 내역을 받을 이메일'}),
            'shipping_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '배송지 주소'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '연락처 (- 없이 입력)'}),
        }

# 4. 회원가입 폼
class CustomSignupForm(SignupForm):
    first_name = forms.CharField(label='이름', max_length=30, widget=forms.TextInput(attrs={'placeholder': '실명을 입력해주세요'}))
    phone = forms.CharField(label='연락처', max_length=20, widget=forms.TextInput(attrs={'placeholder': '010-0000-0000'}))
    address = forms.CharField(label='주소', max_length=255, widget=forms.TextInput(attrs={'placeholder': '배송지 주소를 입력해주세요'}))

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.save()
        Profile.objects.create(
            user=user,
            phone=self.cleaned_data['phone'],
            address=self.cleaned_data['address']
        )
        return user

# 5. 리뷰 폼
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '리뷰를 남겨주세요!'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }