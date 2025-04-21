from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from pydantic import BaseModel, EmailStr
import os, dotenv, smtplib
from email.message import EmailMessage
import random

# LangChain 관련
from langchain_openai import ChatOpenAI  # pip install langchain-openai
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationSummaryBufferMemory
from fastapi.middleware.cors import CORSMiddleware


# pbn_builder 모듈에서 빌드 함수 import
from pbn_builder import build_sample_pbn
from chat import get_chat_response, get_or_create_memory
from session_manager import get_session_id_from_header
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from langchain_teddynote import logging

# 서버실행 uvicorn app:app --reload --port 8000 --ssl-keyfile=localhost-key.pem --ssl-certfile=localhost.pem

dotenv.load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY 환경 변수를 설정하세요.")

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

# 1) FastAPI 인스턴스
app = FastAPI()

# CORS 설정: 개발 단계에서는 모든 도메인을 허용
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 배포 후엔 ["https://내도메인.com"] 처럼 제한
#     allow_methods=["*"],
#     allow_headers=["*"],
#     allow_credentials=True,  # 반드시 추가
# )


class CustomCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            # 브라우저가 preflight 요청을 보낼 때
            headers = {
                "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
                "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                "Access-Control-Allow-Headers": "content-type,x-session-id",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Private-Network": "true",
            }
            return StarletteResponse(status_code=200, headers=headers)
        # 일반 요청
        response = await call_next(request)
        # 일반 요청에도 Origin과 Credentials 헤더를 설정
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


app.add_middleware(CustomCORSMiddleware)


# 리드 데이터 스키마 (양식 제출용)
class Lead(BaseModel):
    email: EmailStr
    telegram: str = None
    site: str
    keyword: str = None


# 요청 바디 스키마
class Ask(BaseModel):
    question: str


# 6) 엔드포인트
@app.post("/chat")
async def chat_endpoint(req: Ask, request: Request, response: Response):
    """
    /chat 엔드포인트는 클라이언트로부터 질문을 받고,
    HTTP 헤더("X-Session-Id")에서 세션 ID를 읽어 이전 대화 맥락을 유지하여 응답을 생성합니다.
    """
    # 프로젝트 이름을 입력합니다.
    logging.langsmith("Plugin Chatbot")
    # 클라이언트 쿠키에서 session id를 가져오거나 생성합니다.
    session_id = get_session_id_from_header(request)
    print(
        f"[app.py] /chat endpoint called. Session ID: {session_id}, Question: {req.question}"
    )

    try:
        # chat.py에서 정의한 get_chat_response() 함수를 호출하여 대화 응답 생성
        # session_id를 전달하여 동일 사용자의 대화 기록이 유지되도록 합니다.
        answer = get_chat_response(req.question, session_id)
        print(f"[app.py] /chat response: {answer}")
        return {"answer": answer}
    except Exception as e:
        print(f"[app.py] Error in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lead/submit")
async def lead_submit(lead: Lead, request: Request, background_tasks: BackgroundTasks):
    # 1) 세션 아이디 얻기
    session_id = get_session_id_from_header(request)

    # 2) 해당 세션의 메모리 가져오기 (없으면 새로 생성)
    memory = get_or_create_memory(session_id)

    # 3) 양식 데이터를 한 문장으로 조합
    init_context = (
        f"【나의 정보】\n"
        f"- 이메일: {lead.email}\n"
        f"- Telegram: {lead.telegram or '없음'}\n"
        f"- 사이트: {lead.site}\n"
        f"- 키워드: {lead.keyword or '없음'}"
    )

    # 4) 메모리에 “사용자 →” 형태로 저장
    memory.save_context(
        {"input": init_context},
        {"output": ""},  # 초기에는 봇의 응답이 없으므로 빈 문자열
    )

    # 5) 기존 작업(백그라운드 빌드) 수행
    background_tasks.add_task(build_sample_pbn, lead)

    return {"status": "ok", "message": "요청이 접수되었습니다. 챗봇이 곧 열립니다."}


# @app.options("/lead/submit")
# def options_lead_submit(response: Response):
#     """
#     /lead/submit 엔드포인트에 대한 Preflight 요청 처리
#     """
#     response.headers["Access-Control-Allow-Origin"] = "https://majortoto789.com"
#     response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
#     response.headers["Access-Control-Allow-Headers"] = "content-type,x-session-id"
#     response.headers["Access-Control-Allow-Credentials"] = "true"
#     # 추가: Private Network Access 허용
#     response.headers["Access-Control-Allow-Private-Network"] = "true"
#     return Response(status_code=200)
