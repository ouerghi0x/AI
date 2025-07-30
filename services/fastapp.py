import multiprocessing
from pydantic import BaseModel
import uvicorn
from fastapi import Depends, FastAPI, Request, Form, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.agent_service import AgentInterface
from services.cassandra_service import CassandraManager
from env_loader import load_environment

load_environment()
import  os

class QuestionRequest(BaseModel):
    """Pydantic model for the incoming question request."""
    user_id: str
    question: str
class FastApp:
    def __init__(self,ret):
        self.cassandra_intra = CassandraManager()
        self.app = FastAPI()
        self.agent = AgentInterface(ret)
        self.origins = [
            os.getenv('ANGULAR_URL'),
            'http://51.210.107.84:4041',
            'http://localhost:4041'
        ]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Store agents per user/session
        self.agents = {}

        self.app.add_event_handler("startup", self.startup_event)
        self.app.add_event_handler("shutdown", self.shutdown_event)
        self.app.add_api_route("/send_message/", self.send_message, methods=["POST"])

    async def startup_event(self):
        print("Starting App ...")

    async def shutdown_event(self):
        print("Shutting down app...")
        # Cleanup all agents
        self.agent=None
        self.agents.clear()



    async def create_agent_for_user(self):
        """
        Initialize a new AgentInterface instance for a user.
        This can be customized per user if needed.
        """
        agent = self.agent
        agent.compression_retriever=await agent.setup_ensemble_retrievers()
        agent.chain = agent.simple_chain()
        agent.complete_agent()
        return agent

    async def send_message(self, request: Request, question:QuestionRequest):
        """
        Receive question and user_id from the client.
        Create or reuse an agent instance for the user.
        """
        user_id=question.user_id
        if not question.user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Create agent for user if not exists
        if user_id not in self.agents:
            self.agents[user_id] =await  self.create_agent_for_user()

        agent = self.agents[user_id]

        # Assuming agent.answer_question is sync, otherwise await it
        answer = agent.answer_question(question.question)
        return {"answer": answer}

    def run(self):
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=8001,
            workers=multiprocessing.cpu_count()
        )
        server = uvicorn.Server(config)
        server.run()



