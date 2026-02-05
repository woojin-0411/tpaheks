import re

def clean_css_file(filepath):
    # 파일을 UTF-8로 읽어옵니다.
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 유니코드 오류 문자(U+FFFD 등)나 제어 문자를 공백으로 대체합니다.
    # 네모네모는 보통 U+FFFD (Replacement Character)로 표시됩니다.
    
    # 1. U+FFFD 문자를 공백으로 대체
    cleaned_content = content.replace('\ufffd', ' ')
    
    # 2. 기타 보이지 않는 제어 문자를 공백으로 대체 (필요 시)
    cleaned_content = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned_content)

    # 정리된 내용을 덮어씁니다.
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"File '{filepath}' cleaned successfully.")

# --- 스크립트 실행 부분 추가 ---
if __name__ == "__main__":
    # 프로젝트 경로에 맞게 style.css 파일 경로를 지정합니다.
    # config/static/style.css 파일에 대해 정리 작업을 실행합니다.
    css_filepath = 'config/static/style.css'
    clean_css_file(css_filepath)

# 사용 예시:
# clean_css_file('config/static/style.css')