import logging
import time
from collections import OrderedDict
from langchain.agents import Tool

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)


from langchain_core.globals import set_llm_cache
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationSummaryMemory
import os
from pathlib import Path
from langchain.retrievers import  EnsembleRetriever


from langchain_community.cache import SQLiteCache

from services.ret_insert_docs import ParentRetriever
from services.sql_agent_service import Sql_agent

set_llm_cache(SQLiteCache(database_path="langchain.db"))






from services.cassandra_service import CassandraManager
from langchain_core.prompts import PromptTemplate
from env_loader import load_environment

load_environment()
class AgentInterface:
    
    def __init__(self,ret:ParentRetriever,
                 name_dir="uploads",cassandra_intra=CassandraManager()
        ):
        self.parent_retriever=ret
        self.logger = None
        self.astra_db_store = None
        self.final_agent = None
        self.setup_logging()
        self.prompt=None
        self.cache = OrderedDict()
        self.cache_ttl = 300
        
        self.UPLOAD_DIR = Path(name_dir) 

        # Create a single Ranker instance properly

        self.cassandraInterface=cassandra_intra



        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("LANGSMITH_API_KEY"),
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
        )
        self.memory_llm=[]
        self.compression_retriever=None


        

        self.combine_documents_chain=None
        self.memory = ConversationSummaryMemory(llm=self.llm,memory_key="chat_history",return_messages=True)

        self.chain=None
        self.rag_tool =None
        self.tools=[
        ]
        self.register_sql_tool("BD_CARS", "VPS_DB_URI_BD_CARS", "VPS_DB_DESC_BD_CARS", "Cars")
        self.register_sql_tool("test_medical", "VPS_DB_URI_test_medical", "VPS_DB_DESC_test_medical", "Medical")

    def register_sql_tool(self,db_key, uri_env, desc_env, name):
        agent = Sql_agent(self.llm, os.getenv(uri_env))
        tool = Tool(
            name=f"SQL Agent - {name} for  {db_key}",
            func=agent.run,
            description=os.getenv(desc_env, f"Tool to access the {name} database"),
        )
        self.tools.append(tool)


    def complete_agent(self):
        from langchain.agents import initialize_agent
        from langchain.agents.agent_types import AgentType
        
        self.rag_tool=Tool(
                name="Deep Answering Agent",
                func=self.chain.invoke,
                description = (
                "This tool is backed by a full Retrieval-Augmented Generation (RAG) agent, optimized for deep and context-aware information retrieval. "
                "It is invoked by the main agent when a query requires in-depth reasoning or highly specific knowledge that cannot be handled by simple "
                "complex and research-intensive tasks."
            )
            )
        self.tools.append(
            self.rag_tool
        )
        self.final_agent=initialize_agent(
                 self.tools,
                llm=self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True
            )   
    
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    def cache_answer(self, question, answer):
        current_time = time.time()
        self.cache[question] = (answer, current_time)
        self.cleanup_cache()
    def cleanup_cache(self):
        current_time = time.time()
        keys_to_delete = [key for key, (_, timestamp) in self.cache.items() if current_time - timestamp >= self.cache_ttl]
        for key in keys_to_delete:
            del self.cache[key]
    
    async def setup_ensemble_retrievers(self):
       

        retrieval=self.parent_retriever.astra_db_store.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 5, 'fetch_k': 50}
        )

        
        ensemble_retriever_new = EnsembleRetriever(retrievers=[self.parent_retriever.parent_retriever, retrieval],
                                        weights=[0.4, 0.6])
        multi_retriever = MultiQueryRetriever.from_llm(
            ensemble_retriever_new
         , llm=self.llm
        )
        
        ensemble_retriever = EnsembleRetriever(retrievers=[ensemble_retriever_new, multi_retriever],
                                        weights=[0.4, 0.6])

        return ensemble_retriever


    def get_cached_answer(self, question):
        current_time = time.time()
        if question in self.cache:
            answer, timestamp = self.cache[question]
            if current_time - timestamp < self.cache_ttl:
                return answer
        return None


           
    def simple_chain(self):
       
        ADDITIONAL_INSTRUCTIONS = os.getenv("ADDITIONAL_INSTRUCTIONS", "")
        self.prompt = ADDITIONAL_INSTRUCTIONS + """
            **Context:**  
            {context}  

            **Chat History:**  
            {chat_history}  

            **Question:**  
            {question}  
            
            Please answer the user in the same language as the question.
            [Answer] 
            """



        chain = (
            {
                "context": self.compression_retriever,
                "chat_history": lambda _: "\n".join(
                    [msg.content for msg in self.memory.load_memory_variables({}).get("chat_history", [])]
                ) if self.memory.load_memory_variables({}).get("chat_history") else "",  # Handle empty history
                "question": RunnablePassthrough()
            }
            | PromptTemplate.from_template(self.prompt)
            | self.llm
            | StrOutputParser() 
        )

        return chain
    



    
    def answer_question(self,question:str
                        ):
        
        self.logger.info(f"Received question: {question}")
        docs=os.listdir(self.UPLOAD_DIR)
        question_enhanced = question + f" The following files may help answer the question accurately: {docs}. If you find a match, use the Deep Answering Tool."


        try:
                
            final_answer = self.final_agent.run(question_enhanced) 
            if (question,final_answer) not in self.memory_llm:
                self.memory_llm.append((question, final_answer))
                
                
               
        except Exception as e:
            self.logger.error(f"Error while answering question: {e}")
            return 
            
        self.memory.save_context({"question": question}, {"answer": f"{final_answer}"})
            
        return final_answer

