# pbn_builder.py
import random
import os
import smtplib
from email.message import EmailMessage
import re
from fastapi import HTTPException

# 필요한 외부 모듈과 함수를 import (실제 경로에 맞게 수정)
from langchain_image import full_image_pipeline
from langchain_title import generate_blog_title_with_chain
from langchain_content import generate_long_blog_content_with_chain, insert_anchor_text
from wordpress_functions import upload_image_to_wordpress, upload_blog_post_to_wordpress

# 환경 변수들은 보통 app.py에서 load_dotenv() 호출 후 사용할 수 있음.
# 예시로 os.getenv 로 사용. (app.py에서 dotenv.load_dotenv()를 호출해야 함)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")


def send_pbn_email(to_email: str, site: str, keyword: str, pbn_link: str):
    """
    양식에 입력된 사이트와 키워드를 이용해 이메일 제목과 본문을 구성하여 전송.
    제목: "{사이트주소} - '{키워드}' 샘플 백링크입니다."
    본문에는 사이트 주소, 키워드, 생성된 PBN 백링크 주소가 포함됩니다.
    """
    subject = f"{site} - '{keyword}' 샘플 백링크입니다."
    body = f"""{site}
키워드: {keyword}

위 사이트에 대한 샘플 PBN백링크 1개를 구축완료하였습니다.

결과:
{pbn_link}
"""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        print("이메일 전송 성공")
    except Exception as e:
        raise Exception(f"메일 전송 중 오류 발생: {e}")


def build_sample_pbn(lead):
    """
    백그라운드에서 PBN 백링크를 구축하는 함수.
    1. DB에서 PBN 사이트 목록을 가져와 무작위로 선택
    2. 입력된 키워드(없으면 기본값 "SampleKeyword")로 콘텐츠 및 제목 생성
    3. 이미지 생성, 업로드 및 워드프레스에 포스트 업로드 진행
    4. 생성된 샘플 백링크를 이메일로 전송
    """
    try:
        # 1. PBN 사이트 목록에서 무작위 선택 (controlDB 모듈의 함수)
        from controlDB import get_all_pbn_sites

        pbn_sites = get_all_pbn_sites()
        if not pbn_sites:
            print("PBN 사이트 정보가 없습니다.")
            return
        pbn_site = random.choice(pbn_sites)
        pbn_site_id, pbn_url, pbn_user, pbn_pass, pbn_app_pass = pbn_site

        # 2. 키워드 및 콘텐츠 생성
        keyword = lead.keyword if lead.keyword else "SampleKeyword"
        full_image_pipeline(keyword=keyword)
        title = generate_blog_title_with_chain(keyword)
        content = generate_long_blog_content_with_chain(
            title, keyword, desired_word_count=800
        )
        content = insert_anchor_text(content, keyword, lead.site)

        # 3. 이미지 및 포스트 업로드
        wp_xmlrpc_url = f"{pbn_url}xmlrpc.php"
        wp_api_url = f"{pbn_url}wp-json/wp/v2"
        image_id, wp_image_url = upload_image_to_wordpress(
            wp_xmlrpc_url, pbn_user, pbn_pass, keyword
        )
        if not image_id:
            print("이미지 업로드 실패")
            return
        image_tag = f'<img src="{wp_image_url}" alt="{keyword}" title="{keyword}" loading="lazy">'
        content = image_tag + "\n\n" + content

        post_id = upload_blog_post_to_wordpress(
            title, content, wp_api_url, pbn_user, pbn_app_pass, image_id, keyword
        )
        if not post_id:
            print("포스트 업로드 실패")
            return

        sample_backlink = f"{pbn_url}/?p={post_id}"
        print(f"샘플 백링크: {sample_backlink}")

        # 4. 이메일 전송
        send_pbn_email(lead.email, lead.site, keyword, sample_backlink)

        # 필요한 추가 DB 기록 작업도 여기서 가능 (예: add_post)
    except Exception as e:
        print("PBN 백링크 구축 중 오류:", e)
