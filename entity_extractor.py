from document_db import DocumentItem
from config import Config
from openrouter import OpenRouter
import json

SYSTEM_PROMPT = """
You are an expert Information Extraction AI. Your goal is to build a high-quality Knowledge Graph. 

INPUT: You will receive a raw text snippet from a web page. 

INSTRUCTIONS: 
1. Extract clearly identifiable entities (Nodes). 
2. Extract meaningful relationships between them (Edges). 
3. Normalize entities where possible (e.g., convert "J. Musk" and "Elon Musk" to just "Elon Musk"). 
4. Ignore generic entities (e.g., "the company", "users", "software", "he", "it"). 
5. Output strict JSON format. 

SCHEMA DEFINITION: 
{ "nodes": [ {"id": "Exact Name", "label": "Type (Person, Organization, Location, Product, Concept, Event, etc)"} ], "edges": [ {"source": "Source Node ID", "target": "Target Node ID", "relation": "ALL_CAPS_VERB_PHRASE"} ] } 

CONSTRAINTS: 
- 'id' must be unique in the list. 
- 'relation' should be short and descriptive (e.g. "FOUNDED", "ACQUIRED", "LOCATED_IN"). 
- Do not output markdown code blocks (```json). Just the raw JSON string.

"""

class EntityExtractor:
    def __init__(self, config: Config):
        self.config = config

    def extract_entities(self, doc_item: DocumentItem):
        if not doc_item.content:
            raise ValueError("Document item must have content")

        with OpenRouter(api_key=self.config.openrouter_api_key()) as client:
            response = client.chat.send(
                model=self.config.entity_extractor_model(),
                max_tokens=10000,
                # Make deterministic
                temperature=0.0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract entities from the following document:\n{doc_item.content}"}
                ]
            )
            content = response.choices[0].message.content

            return json.loads(content)
            
        
        