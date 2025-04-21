# rag.py
import os
from typing import Any, List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.vectorstores import FAISS


class RagPipeline:
    """
    FAISS 기반 RAG(추출형 QA) 파이프라인을 캡슐화합니다.
    1) LLM, 임베딩, FAISS 인덱스 로드
    2) History‑aware Retriever 구성
    3) QA Combine 체인 생성
    4) run() 메서드로 질문 + 대화 기록을 넣으면 'answer' 문자열을 반환
    """

    def __init__(
        self,
        index_path: str,
        openai_api_key: str,
        k: int = 3,
        llm_model_name: str = "gpt-4o-mini",
        embed_model_name: str = "text-embedding-3-small",
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ):
        # 1) LLM
        self.llm = ChatOpenAI(
            model_name=llm_model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=openai_api_key,
        )

        # 2) 임베딩 & FAISS 로드
        self.embeddings = OpenAIEmbeddings(
            model=embed_model_name, openai_api_key=openai_api_key
        )
        self.db = FAISS.load_local(
            index_path, self.embeddings, allow_dangerous_deserialization=True
        )
        base_retriever = self.db.as_retriever(
            search_type="similarity", search_kwargs={"k": k}
        )

        # 3) 히스토리 어웨어 리트리버
        rephrase_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "대화 히스토리와 새 질문을 독립적 질문으로 변환하세요."),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        self.history_retriever = create_history_aware_retriever(
            self.llm, base_retriever, rephrase_prompt
        )

        # 4) QA 체인
        qa_system = "다음 문서(context)를 참고해 질문에 답해주세요. \n\n" "{context}"
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        combine_docs_chain = create_stuff_documents_chain(
            llm=self.llm, prompt=qa_prompt
        )

        # 5) 최종 RAG 체인
        self.chain = create_retrieval_chain(self.history_retriever, combine_docs_chain)

    def run(self, question: str, chat_history: List[Any]) -> str:
        """
        질문과 대화 기록(chat_history)을 넣으면 RAG를 통해 답변만 반환합니다.
        """
        result = self.chain.invoke(
            {
                "input": question,
                "chat_history": chat_history or [],
            }
        )
        # 반환값 dict 에서 'answer' 키를 꺼내고, 없으면 전체 반환
        answer = (
            result.get("answer") or result.get("output") or result.get("result") or ""
        )
        return answer.strip()
