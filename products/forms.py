from django import forms
from allauth.account.forms import SignupForm
# ★ [중요] Profile 옆에 Review를 꼭 추가해야 합니다!
from .models import Profile, Review 

# 1. 기존 회원가입 폼 (그대로 유지)
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

# 2. ★ [새로 추가] 리뷰 작성 폼
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '리뷰를 남겨주세요!'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }