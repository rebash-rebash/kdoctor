import os
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# 1. Maintain your exact production-grade data schema
class LogAnalysis(BaseModel):
    service_name: str = Field(description="The microservice or component that threw the error.")
    severity: str = Field(description="CRITICAL, WARNING, or INFO based on the impact.")
    root_cause_summary: str = Field(description="A concise, 1-sentence breakdown of why the failure occurred.")
    impacted_dependencies: List[str] = Field(description="List of database, internal APIs, or cloud services impacted.")
    suggested_remediation: str = Field(description="Exact SRE action items to resolve this specific stack trace.")

# 2. Initialize the modern Gemini client (automatically picks up GEMINI_API_KEY env var)
client = genai.Client()

def analyze_stack_trace_gemini(raw_log: str) -> LogAnalysis:
    # We use gemini-2.5-flash as it is lightning fast and perfect for structured task automation
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"Raw Log Data:\n{raw_log}",
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are an expert SRE automated triage engine. "
                "Analyze the raw logs provided by the engineer. "
                "Extract structural data facts without adding fluff or conversational filler."
            ),
            # Force deterministic outputs
            temperature=0.0,
            # Enforce the rigid Pydantic JSON output structure
            response_mime_type="application/json",
            response_schema=LogAnalysis,
        ),
    )
    
    # The SDK automatically validates the JSON string and parses it directly into your Pydantic object
    return response.parsed, response.usage_metadata

if __name__ == "__main__":
    # Sample malfunctioning log
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

    print("Sending trace to Gemini SRE Engine...\n")
    analysis_result, usage = analyze_stack_trace_gemini(sample_malfunctioning_log)
    
    # Output the structured fields
    print(f"Service Detected: {analysis_result.service_name}")
    print(f"Severity:         {analysis_result.severity}")
    print(f"Root Cause:       {analysis_result.root_cause_summary}")
    print(f"Dependencies:     {analysis_result.impacted_dependencies}")
    print(f"Remediation:      {analysis_result.suggested_remediation}")
    print(f"Prompt Token Count: {usage.prompt_token_count}")
    print(f"Candidates Token Count: {usage.candidates_token_count}")

