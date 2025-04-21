# chat.py
"""
이 모듈은 챗봇 대화 응답을 생성하고, 각 세션(session_id)별로 대화 내역을
ConversationSummaryBufferMemory를 통해 관리하는 기능을 제공합니다.

주의:
- 이 메모리 저장소는 백엔드의 인메모리(session_memories)에서 관리되므로,
  서버(또는 프로세스)가 재시작되면 해당 대화 기록은 초기화됩니다.
- 영속성이 필요하면 Redis나 데이터베이스와 같은 외부 저장소를 도입해야 합니다.
"""

import os
import dotenv

# 환경변수 로드: OPENAI_API_KEY를 포함하여 필요한 변수들을 불러옵니다.
dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY 환경 변수를 설정하세요.")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.chains.conversation.base import ConversationChain
from rag import RagPipeline


# 1) RAG 파이프라인을 한 번만 초기화
pipeline = RagPipeline(
    index_path="faiss_index",
    openai_api_key=OPENAI_API_KEY,
    k=3,  # 검색할 청크 수
)

session_memories = {}


def get_or_create_memory(session_id: str) -> ConversationSummaryBufferMemory:
    """
    주어진 session_id에 해당하는 대화 메모리가 없으면 새로 생성하고,
    있으면 기존 메모리를 반환합니다.

    Parameters:
        session_id (str): 클라이언트의 고유 세션 ID

    Returns:
        ConversationSummaryBufferMemory: 해당 세션의 대화 메모리 객체
    """
    if session_id not in session_memories:
        session_memories[session_id] = ConversationSummaryBufferMemory(
            llm=pipeline.llm,
            max_token_limit=300,  # 토큰 제한 (필요에 따라 조정)
            return_messages=True,  # 전체 메시지 기록 반환 (디버깅용)
            memory_key="chat_history",
        )
        print(
            f"[chat.py] New ConversationSummaryBufferMemory created for session_id: {session_id}"
        )
    else:
        print(
            f"[chat.py] Existing ConversationSummaryBufferMemory found for session_id: {session_id}"
        )
    # 디버깅: 현재 해당 session_id에 저장된 대화 내역 확인
    current_memory = session_memories[session_id]
    print(f"[chat.py] Current memory for session_id {session_id}: {current_memory}")
    return current_memory


def get_chat_response(question: str, session_id: str) -> str:
    """
    사용자의 질문과 세션 ID를 바탕으로, 해당 세션의 대화 메모리를 이용해 응답을 생성합니다.
    ConversationSummaryBufferMemory를 사용하여 최근 대화 내용은 그대로, 이전 대화 내용은 요약하여 관리합니다.

    Parameters:
        question (str): 사용자가 보낸 질문
        session_id (str): 클라이언트의 고유 세션 ID

    Returns:
        str: 생성된 챗봇 응답 (양 끝 공백 제거)
    """
    print(
        f"[chat.py] get_chat_response() called with question: '{question}' and session_id: {session_id}"
    )
    memory = get_or_create_memory(session_id)
    # ConversationChain을 생성하면, 메모리에 저장된 대화(요약 + 최근 버퍼)를 활용합니다.
    chat_history = memory.load_memory_variables({})["chat_history"]
    # RAG 체인 실행
    answer = pipeline.run(question, chat_history)

    # 메모리에 저장
    memory.save_context({"input": question}, {"output": answer})

    return answer
