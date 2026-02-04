from pathlib import Path
import os
from django.urls import reverse_lazy # lazy하게 URL을 참조하기 위해 추가

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Pathlib 기반으로 BASE_DIR을 정의하여 경로 관리를 더 현대적인 방식으로 변경합니다.
# 현재 정의 방식(os.path.dirname)도 유효하나, Pathlib을 활용하면 더 Pythonic합니다.
BASE_DIR = Path(__file__).resolve().parent.parent 
# 만약 위의 Pathlib 정의가 오류를 일으킨다면, 기존 코드를 사용하세요:
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-3x8w-r_8^p3@h8s!$p*d+p-e^y-e^w-g-^e^y-e^w-g' 

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['3.37.205.155', 'semodan.com', 'www.semodan.com', '127.0.0.1', 'localhost']

# Application definition
# ----------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'django.contrib.sites',
    # --- 우리가 새로 만든 앱 등록 ---
    'products', 
    
    # --- allauth 기본 앱 ---
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    
    # ★ 소셜 로그인 제공자 추가
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.naver',
    'allauth.socialaccount.providers.kakao',
    
    # --- Django Humanize: {{ price|intcomma }} 사용을 위해 필수 ---
    'django.contrib.humanize',
    # --------------------------------
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # --- allauth 필수 미들웨어 ---
    'allauth.account.middleware.AccountMiddleware',
    # ----------------------------
]
ROOT_URLCONF = 'config.urls'

# config/settings.py

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # [수정] 아래 줄을 이렇게 바꾸세요 (템플릿 폴더를 명시)
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # 데이터베이스 경로: os.path.join()은 안전합니다.
        # BASE_DIR이 Path 객체로 정의되었다면 BASE_DIR / 'db.sqlite3'로 사용할 수 있습니다.
        # 현재는 이전 오류 방지를 위해 os.path.join을 유지합니다.
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]
# Internationalization (한국어/서울 설정)
LANGUAGE_CODE = 'ko-kr' 
TIME_ZONE = 'Asia/Seoul' 
USE_I18N = True
USE_TZ = True


# ======================================================================
# 최종 정적 파일(Static Files) 및 미디어 파일(Media Files) 설정
# ======================================================================

# 1. 정적 파일 (CSS, JS, 미리 준비된 이미지) 설정
STATIC_URL = '/static/'

# 개발 환경에서 static 파일을 찾을 위치 (우리의 파일 위치)
# [수정]: BASE_DIR을 사용하여 경로를 명확히 지정합니다. config/static 폴더를 참조합니다.
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'config', 'static'), 
]



# 2. 미디어 파일 (관리자가 업로드한 상품 이미지) 설정
MEDIA_URL = '/media/'

# 관리자가 업로드하는 파일들이 서버의 어디에 저장될지 설정 (디스크 경로)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 3. allauth 필수 설정
# ----------------------------------------------------------------------
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

LOGIN_REDIRECT_URL = reverse_lazy('products:shop') 
ACCOUNT_LOGOUT_REDIRECT_URL = reverse_lazy('products:index') 

# [수정됨] 이메일 관련 설정 끄기
# ACCOUNT_EMAIL_REQUIRED = False          # 이메일 필수 아님
# ACCOUNT_USERNAME_REQUIRED = True        # 아이디는 필수
ACCOUNT_EMAIL_VERIFICATION = 'none'     # 이메일 인증 안 함

# 로그인 수단: 아이디(username)로만 로그인
ACCOUNT_LOGIN_METHODS = {'username'} 

# 회원가입 입력 항목: 이메일 빼고 'username'만 남김
ACCOUNT_SIGNUP_FIELDS = ['username']

SOCIALACCOUNT_LOGIN_ON_GET = True
# ----------------------------------------------------------------------
# 4. 카카오 소셜 로그인 설정
# ----------------------------------------------------------------------
# 4. 카카오 소셜 로그인 설정 (수정됨)
SOCIALACCOUNT_PROVIDERS = {
    'kakao': {
        # [중요] 여기에 'account_email'이 있으면 절대 안 됩니다!
        # 카카오 설정 화면에 있는 ID 그대로 'profile_nickname'과 'profile_image'만 적어야 합니다.
        'SCOPE': ['profile_nickname', 'profile_image'], 
    }
}
# [settings.py 파일 하단]

# ==========================================
# ★ 이메일 설정 (Google Gmail로 변경)
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # 구글 서버 주소
EMAIL_PORT = 587               # 구글 포트 번호 (TLS)
EMAIL_USE_TLS = True           # 보안 연결 켜기
EMAIL_USE_SSL = False          # (TLS를 쓰므로 SSL은 끔)

# 보내는 사람 이메일 (여기에 semodaninfo 주소를 적으세요)
EMAIL_HOST_USER = 'semodaninfo@gmail.com'

EMAIL_HOST_PASSWORD = 'fake_number' 

# (선택) 기본 보내는 사람 이름 설정
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

SITE_ID = 1

# [추가] collectstatic 명령어를 위한 경로 설정
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 인증 백엔드 설정
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend', # 일반 로그인
    'allauth.account.auth_backends.AuthenticationBackend', # 소셜 로그인
]

# 로그인 후 이동할 페이지
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# 이메일 인증 설정 (선택사항: 'mandatory'로 하면 이메일 인증 필수)
ACCOUNT_EMAIL_VERIFICATION = 'none'

ACCOUNT_FORMS = {
    'signup': 'products.forms.CustomSignupForm',
}

# 회원가입 시 커스텀 폼 사용 설정
ACCOUNT_FORMS = {'signup': 'products.forms.CustomSignupForm'}

ACCOUNT_AUTHENTICATION_METHOD = 'username' 
ACCOUNT_EMAIL_REQUIRED = False

DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760
