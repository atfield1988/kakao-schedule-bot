"""
카카오톡 챗봇 응답 템플릿 함수

이 모듈은 카카오톡 스킬 응답의 반복적인 JSON 구조를 
템플릿 함수로 추상화하여 코드 중복을 제거합니다. (DRY 원칙)
"""


def simple_text(text):
    """
    단순 텍스트 응답 생성
    
    Args:
        text (str): 사용자에게 표시할 텍스트
    
    Returns:
        dict: 카카오톡 API 2.0 형식의 JSON 응답
    
    Example:
        >>> simple_text("신청이 완료되었습니다")
        {
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {"text": "신청이 완료되었습니다"}
                }]
            }
        }
    """
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": text
                }
            }]
        }
    }


def list_card(header_title, items, buttons):
    """
    ListCard 응답 생성 (페이지네이션용)
    
    Args:
        header_title (str): 카드 헤더 제목
        items (list): 카드 아이템 리스트
            [{
                "title": "제목",
                "description": "설명",
                "action": "block",
                "blockId": "block_id",
                "extra": {...}
            }]
        buttons (list): 하단 버튼 리스트
            [{
                "action": "block",
                "label": "버튼 텍스트",
                "blockId": "block_id",
                "extra": {...}
            }]
    
    Returns:
        dict: 카카오톡 ListCard 응답
    
    Example:
        >>> items = [
        ...     {
        ...         "title": "11월 27일 11시",
        ...         "description": "근무시간: 4시간",
        ...         "action": "block",
        ...         "blockId": "cancel_confirm",
        ...         "extra": {"application_id": 123}
        ...     }
        ... ]
        >>> buttons = [
        ...     {
        ...         "action": "block",
        ...         "label": "다음 페이지 →",
        ...         "blockId": "cancel_list",
        ...         "extra": {"page": 2}
        ...     }
        ... ]
        >>> list_card("신청 내역", items, buttons)
    """
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "listCard": {
                    "header": {
                        "title": header_title
                    },
                    "items": items,
                    "buttons": buttons
                }
            }]
        }
    }


def simple_text_with_quick_replies(text, quick_replies):
    """
    텍스트 + 퀵리플라이 응답 생성
    
    Args:
        text (str): 메시지 텍스트
        quick_replies (list): 퀵리플라이 버튼 리스트
            [{
                "action": "block",
                "label": "버튼 텍스트",
                "blockId": "block_id",
                "extra": {...}
            }]
    
    Returns:
        dict: 카카오톡 응답 (텍스트 + 퀵리플라이)
    """
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {"text": text}
            }],
            "quickReplies": quick_replies
        }
    }


def context_response(text, context_name, lifespan, params):
    """
    컨텍스트를 포함한 응답 생성 (관리자 시간 변경용)
    
    Args:
        text (str): 응답 텍스트
        context_name (str): 컨텍스트 이름 (예: "ModifySchedule")
        lifespan (int): 컨텍스트 유효 기간 (1 = 다음 1번 대화)
        params (dict): 컨텍스트 파라미터
    
    Returns:
        dict: 컨텍스트 포함 응답
    
    Example:
        >>> context_response(
        ...     "새로운 시간을 입력하세요",
        ...     "ModifySchedule",
        ...     1,
        ...     {"schedule_id": 123, "action": "modify_time"}
        ... )
    """
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {"text": text}
            }]
        },
        "context": {
            "values": [{
                "name": context_name,
                "lifespan": lifespan,
                "params": params
            }]
        }
    }
