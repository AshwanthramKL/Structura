// BAML prompt template for structured data extraction
// Supports both text and image/PDF extraction

// Define a class to hold the extracted structured data
class StructuredData {
  // This is a placeholder for the dynamic data
  // The actual structure will be determined by the schema passed to the function
  data string
}

// Create a function to extract structured data according to a schema
function extractor(input: union(string, array<image>), schema: string, is_image: boolean = false) -> StructuredData {
  client "openai/gpt-4.1" // Default client, can be overridden at runtime
  prompt #"
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
  "#
} 