# session_manager.py
"""
이 모듈은 클라이언트 요청의 HTTP 헤더("X-Session-Id")에서 세션 ID를 읽어오는 함수를 제공합니다.
쿠키 대신 localStorage를 사용하여 클라이언트에서 세션 ID를 관리하므로,
서버는 HTTP 헤더에서 해당 값을 받아 사용합니다.
"""


def get_session_id_from_header(request) -> str:
    """
    request.headers에서 "X-Session-Id" 값을 읽어 반환합니다.
    만약 값이 없으면 None을 반환합니다.

    Parameters:
        request: FastAPI의 Request 객체

    Returns:
        str or None: HTTP 헤더에 포함된 세션 ID
    """
    session_id = request.headers.get("x-session-id")
    if session_id:
        print(f"[session_manager] Retrieved session_id from header: {session_id}")
    else:
        print("[session_manager] No session_id found in header.")
    return session_id
