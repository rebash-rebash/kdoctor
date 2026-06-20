from typing import List
from pydantic import BaseModel, Field
import ollama

# 1. Maintain your exact production-grade data schema
class LogAnalysis(BaseModel):
    service_name: str = Field(description="The microservice or component that threw the error.")
    severity: str = Field(description="CRITICAL, WARNING, or INFO based on the impact.")
    root_cause_summary: str = Field(description="A concise, 1-sentence breakdown of why the failure occurred.")
    impacted_dependencies: List[str] = Field(description="List of database, internal APIs, or cloud services impacted.")
    suggested_remediation: str = Field(description="Exact SRE action items to resolve this specific stack trace.")

def analyze_stack_trace_local(raw_log: str):
    # Call the local Ollama daemon
    response = ollama.chat(
        model='llama3',
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert SRE automated triage engine. "
                    "Analyze the raw logs provided by the engineer. "
                    "Extract structural data facts without adding fluff or conversational filler."
                )
            },
            {
                "role": "user",
                "content": f"Raw Log Data:\n{raw_log}"
            }
        ],
        # Force the local model to match your strict Pydantic structure
        format=LogAnalysis.model_json_schema(),
        options={
            "temperature": 0.0 # Force deterministic output
        }
    )
    
    # Ollama returns a raw JSON string under response['message']['content']
    raw_content = response['message']['content']
    
    # Safely convert the string into your validated Pydantic object
    parsed_object = LogAnalysis.model_validate_json(raw_content)
    
    return parsed_object, response

if __name__ == "__main__":
    sample_malfunctioning_log = """
    2026-06-17T10:14:22.891Z [auth-service] ERROR c.b.auth.jwt.TokenValidator - Verification failed
    java.net.ConnectException: Connection refused (Connection refused)
        at java.base/nio.channels.SocketChannel.checkConnect(Native Method)
        at java.base/nio.channels.SocketChannel.finishConnect(SocketChannel.java:789)
        at org.postgresql.core.v3.ConnectionFactoryImpl.openConnectionImpl(ConnectionFactoryImpl.java:311)
        ... 12 common frames omitted
    CAUSED BY: org.postgresql.util.PSQLException: Connection to localhost:5432 refused. Check that the hostname and port are correct and that the postmaster is accepting TCP/IP connections.
    2026-06-17T10:14:23.001Z [auth-service] WARN c.b.auth.FallbackHandler - Falling back to local hardcoded cache. Auth latency degrading.
    """

    print("Sending trace to Local Ollama SRE Engine...\n")
    analysis_result, raw_resp = analyze_stack_trace_local(sample_malfunctioning_log)
    
    # Output the structured fields
    print(f"Service Detected: {analysis_result.service_name}")
    print(f"Severity:         {analysis_result.severity}")
    print(f"Root Cause:       {analysis_result.root_cause_summary}")
    print(f"Dependencies:     {analysis_result.impacted_dependencies}")
    print(f"Remediation:      {analysis_result.suggested_remediation}\n")
    
    # Local token verification metrics
    print(f"Prompt Tokens Evaluated: {raw_resp.get('prompt_eval_count', 'N/A')}")
    print(f"Response Tokens Created: {raw_resp.get('eval_count', 'N/A')}")

