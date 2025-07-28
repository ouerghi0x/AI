from transformers import AutoModel, AutoTokenizer

# This will cache both the model and tokenizer
AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
