// BAML prompt template for structured data extraction
// Supports both text and image/PDF extraction

// Define a placeholder class that will be extended at runtime
class DynamicResult {
  id string @description("Identifier - this will be the name of the class")
  @@dynamic // Mark as dynamic to allow extension at runtime
}

// Create a function to extract structured data according to a schema
function Extractor(input: string | image[], schema: string, is_image: bool) -> DynamicResult {
  client "openai/gpt-4o"
  prompt #"
    You are a structured data extraction assistant. Your task is to extract structured data from 
    the provided content according to the schema definition. Follow these rules carefully:
    
    INSTRUCTIONS:
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
    
    {% if is_image %}
    Extract structured data from the following image(s) according to the schema following the instructions mentioned above.
    
    {% for image in input %}
    ## Image {{ loop.index }}
    {{ image }}
    {% endfor %}
    {% else %}
    Extract structured data from the following text according to the schema following the instructions mentioned above.
    <text>
    {{ input }}
    </text>
    {% endif %}
    
    {{ ctx.output_format }}
    
    Extract the data as a single valid JSON object that conforms to the schema.
  "#
} 



test Test1 {
  functions [Extractor]
  type_builder {
    // Defines a new type available only within this test block.
    dynamic class DynamicResult {
    quote string @description(#"
      A one line philosophical quote that you think resonates with this input
    "#)
    }
  }

  args {
    input #"
      John Doe

      Education
      - University of California, Berkeley
        - B.S. in Computer Science
        - 2020

      Skills
      - Python
      - Java
      - C++
    "#
    schema ""
    is_image false
  }
}