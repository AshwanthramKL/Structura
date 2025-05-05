// BAML prompt template for structured data extraction
// Supports both text and image/PDF extraction

prompt extractor {
  description = "Extract structured data from text or images according to a schema"
  
  parameters {
    input {
      type = union(string, array<image>)
      description = "The text to extract from, or an array of images"
    }
    
    schema {
      type = string
      description = "The BAML schema definition for extraction"
    }
    
    is_image {
      type = boolean
      description = "Whether the input is an image/PDF"
      default = false
    }
  }
  
  instruction {
    system = """
    You are a structured data extraction assistant. Your task is to extract structured data from 
    the provided content according to the schema definition. Follow these rules carefully:
    
    1. Only extract information that is explicitly mentioned in the content
    2. If a field is required by the schema but not found in the content, use null or an appropriate empty value
    3. Follow the types specified in the schema (string, number, boolean, etc.) precisely
    4. For arrays, extract all relevant items from the content
    5. For nested objects, maintain the structure as specified in the schema
    6. Return valid JSON that conforms exactly to the schema
    7. Do not add any fields not defined in the schema
    8. For dates and numbers, use the formats specified in the schema
    9. If certain information is ambiguous, choose the most likely interpretation based on context
    
    Return ONLY the extracted JSON object, without any explanations, comments, or markdown formatting.
    """
    
    user = """
    {{#if is_image}}
    Extract structured data from the following {{input.length}} page(s) according to the schema.
    
    {{#each input as |image index|}}
    ## Page {{add index 1}}
    {{ image }}
    {{/each}}
    {{else}}
    Extract structured data from the following text according to the schema.
    
    ## Text Content
    {{input}}
    {{/if}}
    
    ## Schema Definition
    ```
    {{schema}}
    ```
    
    Extract the data as a single valid JSON object that conforms to the schema.
    """
  }
} 