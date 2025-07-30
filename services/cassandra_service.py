
from cassandra.cluster import Cluster
import cassio
from dotenv import load_dotenv
import os

from env_loader import load_environment

load_environment()

class CassandraManager:
   
    def __init__(self):
        self.CASSANDRA_PORT=os.getenv("CASSANDRA_PORT")
        self.CASSANDRA_USERNAME=os.getenv("CASSANDRA_HOST")
        self.KEYSPACE:str=os.getenv("KEYSPACE")
        self.session=self.initialize_database_session(self.CASSANDRA_PORT,self.CASSANDRA_USERNAME)
        
        
    
    

    def initialize_database_session(self,port,host):
        
        
        
        self.session =  Cluster([self.CASSANDRA_USERNAME],port=port).connect()
        cassio.init(session=self.session, keyspace=self.KEYSPACE)
            
        create_key_space = f"""
        CREATE KEYSPACE IF NOT EXISTS {self.KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 3}};
        """
        self.session.execute(create_key_space)
        create_documents_table = f"""
        CREATE TABLE IF NOT EXISTS {self.KEYSPACE}.documents (
            document_id UUID PRIMARY KEY,
            FILE_name TEXT  -- Text extracted from the PDF
            
        );
        """
        self.session.execute(create_documents_table)
        return self.session

