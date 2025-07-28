
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

import os
from env_loader import load_environment

load_environment()


def Sql_agent(llm,db_uri):
    if db_uri is None:
        raise ValueError("DATABASE_URL environment variable not set.")
    try:
        db = SQLDatabase.from_uri(db_uri)
    except Exception as e:
        print(f"Error connecting to the database: {e} {db_uri}")
        db = SQLDatabase.from_uri("postgresql+psycopg2://agent:agent%402023@localhost:5432/store")
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent = create_sql_agent(llm=llm, toolkit=toolkit, verbose=True)
    return agent

#agent = Sql_agent(llm)

# Query in natural language
#response = agent.run("List all products purchased by Bob Smith and their quantities.")
