# app/services/introduceAi.py

import uuid
import openai
import json
from  ..createCard.createCard import generate_summary
from dotenv import load_dotenv
import os

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

class ChatBotManager:
    def __init__(self):
        self.sessions = {}

    async def create_session(self, websocket):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "websocket": websocket,
            "context": [],
            "personal_statement": "",
            "initialized": False
        }
        return session_id

    def remove_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

    async def handle_message(self, session_id, message):
        session = self.sessions.get(session_id)
        if not session["initialized"]:
            # 초기화되지 않은 세션이면 사용자 입력을 받아 자기소개서를 생성
            user_input = self.parse_initial_input(message)
            if user_input:
                personal_statement = self.generate_personal_statement(user_input)
                session["personal_statement"] = personal_statement
                session["context"].append({"role": "assistant", "content": personal_statement})
                session["initialized"] = True
                return personal_statement
            else:
                return "필수 정보를 JSON 형식으로 입력해 주세요: title, position, tool, reflection, pdfText"
        else:
            # 이미 생성된 자기소개서에 대한 수정 요청 처리
            if self.is_related_to_personal_statement(message):
                session["context"].append({"role": "user", "content": message})
                updated_statement = self.update_personal_statement(session["context"])
                session["personal_statement"] = updated_statement
                session["context"].append({"role": "assistant", "content": updated_statement})
                return updated_statement
            else:
                return "죄송하지만, 자기소개서와 관련된 질문에만 답변할 수 있습니다."

    def parse_initial_input(self, message):
        # 메시지를 파싱하여 필요한 정보를 추출
        try:
            data = json.loads(message)
            required_fields = ["title", "position","tool", "reflection", "pdfText"]
            if all(field in data for field in required_fields):
                return data
            else:
                return None
        except json.JSONDecodeError:
            return None

    def generate_personal_statement(self, user_input):
        # generate_summary 함수를 사용하여 자기소개서 생성
        summary = generate_summary(user_input)
        return summary

    def update_personal_statement(self, context):
        # OpenAI API를 사용하여 대화 컨텍스트를 기반으로 자기소개서 업데이트
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=context,
            temperature=0.7
        )
        updated_statement = response.choices[0].message["content"]
        return updated_statement

    def is_related_to_personal_statement(self, message):
        # 메시지가 자기소개서 수정과 관련된 내용인지 판별
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=f"다음 문장이 자기소개서 수정과 관련된 내용인지 '예' 또는 '아니오'로 답변하세요:\n\n{message}\n\n답변:",
            max_tokens=1,
            temperature=0
        )
        answer = response.choices[0].text.strip()
        return answer == "예"
