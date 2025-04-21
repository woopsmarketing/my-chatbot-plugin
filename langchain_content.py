import re
import time
from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

content_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.8,
    openai_api_key=OPENAI_API_KEY,
    max_tokens=4096,
)


###############################################
# 1. 마크다운을 HTML로 변환하는 유틸리티 함수
###############################################
def format_markdown_to_html(text: str) -> str:
    """
    입력된 텍스트 내 마크다운 형식을 간단한 HTML 태그로 치환합니다.
    또한, 코드 블록을 나타내는 ``` 태그나 "markdown" 등 불필요한 문구를 제거합니다.
    """
    # 1) “` 와 같이 보이는 경우 (유니코드 좌측 큰따옴표와 백틱이 결합된 경우)
    text = re.sub(r"[“`]`", "", text)
    text = re.sub(r"`", "", text)

    # 2) 일반적인 코드 블럭 구분자 ``` (백틱 세 개)
    text = re.sub(r"```", "", text)

    # ② 'markdown'이라는 단어가 단독으로 나타나는 부분 제거 (대소문자 무시)
    text = re.sub(r"(?i)markdown", "", text)
    # 헤더 치환
    text = re.sub(r"###### (.*)", r"<h6>\1</h6>", text)
    text = re.sub(r"##### (.*)", r"<h5>\1</h5>", text)
    text = re.sub(r"#### (.*)", r"<h4>\1</h4>", text)
    text = re.sub(r"### (.*)", r"<h3>\1</h3>", text)
    text = re.sub(r"## (.*)", r"<h2>\1</h2>", text)
    text = re.sub(r"# (.*)", r"<h1>\1</h1>", text)

    # 굵게 표시
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
    # 줄바꿈 치환
    text = re.sub(r"(?<!</p>)\n(?!<p>)", r"<br>", text)

    # 문단 태그로 감싸기
    paragraphs = text.split("\n")
    paragraphs = [f"<p>{p.strip()}</p>" for p in paragraphs if p.strip()]
    return "\n".join(paragraphs)


###############################################
# 2. 초기 본문 생성 체인 (결론 제외)
###############################################
initial_content_prompt = PromptTemplate(
    input_variables=["title", "keyword"],
    template="""
You are a skilled Korean content writer.
Based on the following details, please write a detailed and informative blog post content excluding any conclusion section.
Title: {title}
Keyword: {keyword}

Requirements:
- Only write in Korean.
- Incorporate subheadings, examples, and tips.
- Do NOT include words like '결론', '마무리', or '끝으로' in the body.
- Provide roughly 300-400 words of content.
Output only the blog post content (without the conclusion).
""",
)
initial_content_chain = initial_content_prompt | content_llm | StrOutputParser()

###############################################
# 3. 추가 본문 생성 체인 (분량 보완)
###############################################
additional_content_prompt = PromptTemplate(
    input_variables=["existing_content", "word_count"],
    template="""
The current blog post content is approximately {word_count} words.
Based on the existing content below, please continue writing additional content in Korean.

Requirements:
1. Write in Markdown format
2. Begin your output with a new primary section heading using Markdown h2 (i.e., start with "##" followed by the title of the new section, for example "## 새로운 내용").
3. After the main heading, develop the content in cohesive paragraphs. If needed, naturally introduce subordinate section headings using h3 (i.e., "###") to further organize the content.
4. Avoid excessive or redundant use of headings; use only one new h2 heading and only as many h3 headings as needed to logically structure the new material.
5. Do NOT repeat subheadings or details from the existing content, and do NOT include any concluding or summary phrases.
6. Focus on providing fresh perspectives, specific examples, and concrete data that build naturally on the existing content.
7. Only write in Korean.
Existing Content:
{existing_content}

Please continue writing additional content (in Korean) that flows naturally from the above.

""",
)

additional_content_chain = additional_content_prompt | content_llm | StrOutputParser()

###############################################
# 4. 결론 생성 체인
###############################################

result_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.8,
    openai_api_key=OPENAI_API_KEY,
    max_tokens=1024,
)

conclusion_prompt = PromptTemplate(
    input_variables=["existing_content"],
    template="""
Based on the blog post content provided below, write a conclusion (in Korean).

Requirements:
1. Write in Markdown format
2. You may introduce the conclusion with a single main heading (##) using terms like '결론', '마무리', or '끝으로'.
3. Summarize key points from the existing content in 1~2 paragraphs. 
4. Do NOT introduce new subheadings beyond the main conclusion heading. 
5. Keep it concise and coherent, directly following from the existing content.
6. Only write in Korean.
Existing Content:
{existing_content}

Write only the conclusion section in Korean, following these rules.
""",
)

conclusion_chain = conclusion_prompt | result_llm | StrOutputParser()


###############################################
# 5. 전체 블로그 본문 생성 함수
###############################################
def generate_long_blog_content_with_chain(
    title: str, keyword: str, desired_word_count: int = 800
) -> str:
    """
    입력받은 제목과 키워드를 기반으로 블로그 본문(결론 제외)을 생성하고,
    원하는 단어 수에 도달할 때까지 추가 본문을 보완한 후, 최종적으로 결론을 생성하여 합칩니다.

    :param title: 블로그 포스트 제목
    :param keyword: 블로그 포스트와 관련된 키워드
    :param desired_word_count: 최종 본문(결론 포함)을 위한 최소 단어 수 목표 (default=600)
    :return: 최종 블로그 포스트 HTML 콘텐츠
    """
    # (A) 초기 본문 생성
    content = initial_content_chain.invoke({"title": title, "keyword": keyword})

    # (B) 추가 본문 생성 (desired_word_count에 도달할 때까지 반복)
    current_word_count = len(content.split())
    while current_word_count < desired_word_count:
        additional = additional_content_chain.invoke(
            {"existing_content": content, "word_count": str(current_word_count)}
        )
        content += "\n" + additional
        current_word_count = len(content.split())

    # (C) 결론 생성
    conclusion = conclusion_chain.invoke({"existing_content": content})

    # (D) 최종 콘텐츠 합치기
    final_content = content + "\n\n" + conclusion
    final_content = format_markdown_to_html(final_content)
    return final_content


def insert_anchor_text(content: str, keyword: str, client_site_url: str) -> str:
    """
    콘텐츠 내에서 지정한 키워드가 처음 등장하는 부분을 찾아 앵커 태그로 감싼 결과를 반환합니다.
    만약 키워드를 찾지 못하면 콘텐츠 앞에 앵커 텍스트를 추가합니다.

    :param content: 원본 콘텐츠 (문자열)
    :param keyword: 앵커 태그를 적용할 기준 키워드
    :param client_site_url: 앵커 텍스트의 링크 URL
    :return: 앵커태그가 적용된 콘텐츠 문자열
    """
    anchor = f'<a href="{client_site_url}" target="_blank" rel="noopener">{keyword}</a>'
    # 정규 표현식을 사용하여 단어 경계(\b)를 포함한 패턴으로 첫 번째 발생만 교체합니다.
    pattern = r"\b" + re.escape(keyword) + r"\b"
    new_content, count = re.subn(pattern, anchor, content, count=1, flags=re.IGNORECASE)
    if count == 0:
        # 키워드를 찾지 못한 경우, 콘텐츠 앞에 앵커 텍스트를 추가합니다.
        new_content = anchor + " " + content
    return new_content
