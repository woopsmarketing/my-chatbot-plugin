# langchain_title.py
from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI

from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def replace_chars(title: str) -> str:
    """제목에서 따옴표나 # 등을 제거합니다."""
    return title.replace('"', "").replace("#", "")


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.8,
    openai_api_key=OPENAI_API_KEY,
    max_tokens=1000,
)

title_prompt = PromptTemplate(
    input_variables=["keyword"],
    template="""
You are a creative and versatile blog post title generator.
For the given keyword "{keyword}", brainstorm a variety of related themes, subtopics, and concepts.
Then, craft a compelling blog post title that captures the essence of these ideas. 
#Note that the final title:
- Can incorporate the original keyword or its related ideas, but it does not have to include the keyword verbatim.
- Should be creative, engaging, and written in a natural style.
- Must be output as a single, concise line without any additional explanation or formatting.
Output only the final title.
#important:
- Please print in Korean only.
""",
)


title_chain = title_prompt | llm | StrOutputParser() | RunnableLambda(replace_chars)


def generate_blog_title_with_chain(keyword: str) -> str:
    """
    주어진 키워드를 기반으로 LangChain을 이용하여 블로그 제목을 생성하는 함수.

    :param keyword: 제목 생성을 위한 기본 키워드
    :return: 최종적으로 생성된 블로그 제목 (불필요한 문자 제거됨)
    """
    return title_chain.invoke({"keyword": keyword})
