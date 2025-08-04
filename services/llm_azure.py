# Setup the Azure OpenAI chat model

from langchain.chat_models import AzureChatOpenAI
import  os

from env_loader import load_environment
load_environment()
endpoint = "https://moham-mdvx8nav-eastus2.cognitiveservices.azure.com/"
modelName = "gpt-4.1-mini"
apiVersion = "2024-04-01-preview"
deployment = "gpt-4.1-mini"

chat_model = AzureChatOpenAI(
    deployment_name=deployment,                # Your Azure deployment name
    model_name=modelName,            # Model variant (optional, for info)
    openai_api_version=apiVersion,
    openai_api_base=endpoint,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)
