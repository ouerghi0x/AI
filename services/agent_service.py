import logging
import time
from collections import OrderedDict

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
            Understand the user’s question fully. 
            If more information is needed to provide a good answer or recommendation, 
            ask the user for clarification or additional details. Provide clear, direct, and natural text responses without hashtags, asterisks, or special formatting. Act as a friendly and helpful shopping assistant guiding the user to find the best product. After answering, ask relevant follow-up questions to learn more about their preferences, budget, salary, or lifestyle. 
            Keep the conversation flowing naturally and engagingly.
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
        question_enhanced +=  "\nAnswer in the same language as the question."

        try:
                
            final_answer = self.chain.invoke(question_enhanced)
        except Exception as e:
            self.logger.error(f"Error while answering question: {e}")
            return 
            
        self.memory.save_context({"question": question}, {"answer": f"{final_answer}"})
            
        return final_answer

