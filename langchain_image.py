# langchain.py
"""
LangChain 기반 콘텐츠 생성 모듈
- 블로그 제목과 본문(및 결론) 생성을 위한 체인을 구성합니다.
- 기존 main.py에서 호출하여 사용하도록 함수 인터페이스를 제공합니다.
"""
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from dotenv import load_dotenv
import os
import time
from openai import OpenAI
import requests
from PIL import Image
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


def make_filename(keyword: str) -> str:
    return f"{keyword}.png"


def save_image_locally(image_url: str, filename: str) -> str:
    """
    주어진 이미지 URL로부터 이미지를 다운로드하여 로컬 파일로 저장한 후,
    저장한 파일 경로를 반환합니다.
    """
    response = requests.get(image_url, stream=True)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        print(f"이미지 로컬에 저장 완료: {filename}")
        return filename
    else:
        print("이미지 다운로드 실패")
        return None


def compress_and_resize_image_in_place(
    image_path: str, target_size: tuple = (512, 512), quality: int = 75
) -> str:
    """
    로컬에 저장된 이미지를 지정된 크기로 리사이즈하고 압축한 후,
    처리된 이미지 경로를 반환합니다.
    """
    try:
        img = Image.open(image_path)
        img = img.resize(target_size, Image.LANCZOS)
        img.save(image_path, "PNG", optimize=True, quality=quality)
        print(f"이미지 압축 및 크기조정 완료: {image_path}")
        return image_path
    except Exception as e:
        print("이미지 압축 실패:", e)
        return None


image_prompt = PromptTemplate(
    input_variables=["keyword"],
    template="""
    keyword: {keyword}
    Create an image that captures the essence of the given keyword(s) in a clear and appealing way. 
    Focus on a simple, balanced composition with neutral tones and soft details that emphasize the meaning of the keyword(s). 
    The design should be universally acceptable, safe, and free from any overly sensitive or controversial elements.
    """,
)


def generate_image_with_dalle(keyword, client, max_attempts=3):
    """
    LangChain 스타일 커스텀 체인 방식의 이미지 생성 함수.
    DALL·E API 호출 시 content_policy_violation 오류 발생 시,
    프롬프트 템플릿을 수정하여 재시도합니다.

    :param keyword: 이미지 생성에 사용할 키워드
    :param client: OpenAI API 클라이언트 객체 (client.images.generate 등 사용)
    :param max_attempts: 재시도 최대 횟수
    :return: 생성된 이미지 URL (성공 시)
    :raises RuntimeError: 모든 시도가 실패했을 경우
    """

    for attempt in range(1, max_attempts + 1):
        prompt_text = image_prompt.format(keyword=keyword)
        try:
            response = client.images.generate(
                model="dall-e-2",
                prompt=prompt_text.strip(),
                n=1,
                size="512x512",
                quality="standard",
            )
            image_url = response.data[0].url
            print(f"[{attempt}회차] 이미지 생성 완료, URL: {image_url}")
            return image_url
        except Exception as e:
            error_msg = str(e)
            print(f"[{attempt}회차] 이미지 생성 실패 → {error_msg}")
            # content_policy_violation 감지 시 템플릿 수정
            if "content_policy_violation" in error_msg.lower():
                print(
                    "→ content_policy_violation 감지, 프롬프트를 더 안전하게 수정 후 재시도합니다."
                )
                # 프롬프트 템플릿 업데이트: 보다 추상적이고 안전한 표현
                prompt_text = image_prompt.format(keyword=keyword)
                # 잠시 대기 후 재시도 (API rate limit 등을 고려)
                time.sleep(1)
            else:
                raise e
    raise RuntimeError(f"이미지 생성 실패: 모든 재시도 불가 (keyword='{keyword}')")


# 전체 이미지 파이프라인을 처리하는 간단한 함수
def full_image_pipeline(keyword: str) -> str:
    # OpenAI 클라이언트 생성 (텍스트 생성과 달리 이미지 생성은 openai 패키지의 OpenAI를 사용)
    # from openai import OpenAI  # 여기서는 기존 openai 패키지 사용

    client = OpenAI(api_key=api_key)

    # 1. 이미지 생성
    image_url = generate_image_with_dalle(keyword, client)

    # 2. 파일명 생성 (예: 키워드에 기반하여 "여자.png")
    filename = f"{keyword}.png"

    # 3. 이미지 다운로드 및 저장
    saved_path = save_image_locally(image_url, filename)
    if saved_path is None:
        raise RuntimeError("이미지 저장 실패")

    # 4. 이미지 압축 및 리사이즈
    final_path = compress_and_resize_image_in_place(saved_path)
    if final_path is None:
        raise RuntimeError("이미지 압축/리사이즈 실패")

    return final_path


if __name__ == "__main__":
    result_path = full_image_pipeline("여자")
    print("최종 이미지 파일 경로:", result_path)
