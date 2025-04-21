import os
import base64
import requests
import xmlrpc.client
from wordpress_xmlrpc import Client
from wordpress_xmlrpc.methods import media


def upload_image_to_wordpress(
    wp_url: str, wp_username: str, wp_password: str, keyword: str
) -> tuple:
    """
    워드프레스 XML-RPC 엔드포인트로 이미지를 업로드합니다.

    :param wp_url: 워드프레스 xmlrpc.php의 URL (예: "https://example.com/xmlrpc.php")
    :param wp_username: 워드프레스 사용자 이름
    :param wp_password: 워드프레스 비밀번호
    :param keyword: 이미지 파일명 구성에 사용할 키워드 (예: "sports")
    :return: (image_id, image_url) 업로드 성공 시 반환. 실패 시 (None, None).
    """
    print(f"[DEBUG] Uploading image to WordPress for domain: {wp_url}")
    wp_client = Client(wp_url, wp_username, wp_password)
    image_path = f"{keyword}.png"
    with open(image_path, "rb") as img:
        data = {
            "name": f"{keyword}.png",
            "type": "image/png",
            "bits": xmlrpc.client.Binary(img.read()),
            "overwrite": True,
        }
    try:
        response = wp_client.call(media.UploadFile(data))
        image_url = response["url"]
        image_id = response["id"]
        print("이미지 업로드 성공:", image_url, image_id)
        os.remove(image_path)
        return image_id, image_url
    except Exception as e:
        print("이미지 업로드 실패:", e)
        return None, None


def create_tag(wp_api_url: str, username: str, app_password: str, keyword: str) -> int:
    """
    주어진 키워드를 기반으로 태그를 생성하거나, 태그가 이미 존재하면 해당 태그의 ID를 반환합니다.

    :param wp_api_url: 워드프레스 REST API 기본 URL (예: "https://example.com/wp-json/wp/v2")
    :param username: 워드프레스 사용자 이름
    :param app_password: 워드프레스 앱 비밀번호
    :param keyword: 생성할 태그의 이름 (예: "sports")
    :return: 태그의 ID (정수) 또는 실패 시 None
    """
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode())
    headers = {
        "Authorization": f"Basic {token.decode('utf-8')}",
        "Content-Type": "application/json",
    }
    data = {"name": keyword}
    response = requests.post(f"{wp_api_url}/tags", headers=headers, json=data)
    if response.status_code == 201:
        tag_id = response.json()["id"]
        print(f"태그 생성 성공: {tag_id}")
        return tag_id
    elif response.status_code == 400 and response.json().get("code") == "term_exists":
        tag_id = response.json()["data"]["term_id"]
        print(f"이미 존재하는 태그를 사용합니다: {tag_id}")
        return tag_id
    else:
        print("태그 생성 실패:", response.content)
        return None


def upload_blog_post_to_wordpress(
    title: str,
    content: str,
    wp_api_url: str,
    username: str,
    app_password: str,
    image_id: int,
    keyword: str,
):
    """
    워드프레스 REST API를 사용하여 블로그 포스트를 업로드합니다.

    :param title: 포스트 제목
    :param content: 포스트 본문 (HTML 포함)
    :param wp_api_url: 워드프레스 REST API의 URL (예: "https://example.com/wp-json/wp/v2")
    :param username: 워드프레스 사용자 이름
    :param app_password: 워드프레스 앱 비밀번호
    :param image_id: 업로드된 이미지의 ID (없을 경우 0)
    :param keyword: (선택 사항) 추후 태그 등록에 사용할 키워드, 현재는 주석 처리되어 있음.
    :return: 업로드한 포스트의 ID (정수) 또는 None (실패 시)
    """
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode())
    headers = {
        "Authorization": f"Basic {token.decode('utf-8')}",
        "Content-Type": "application/json",
    }
    data = {
        "title": title,
        "content": content,
        "status": "publish",
        "featured_media": image_id if image_id else 0,
    }
    try:
        response = requests.post(f"{wp_api_url}/posts", headers=headers, json=data)
        response.raise_for_status()
        if response.status_code == 201:
            print("블로그 포스트 업로드 성공!")
            return response.json()["id"]
        else:
            print("업로드 실패:", response.content)
            return None
    except requests.exceptions.RequestException as e:
        print("요청 에러:", e)
        return None
