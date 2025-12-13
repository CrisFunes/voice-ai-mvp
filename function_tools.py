"""
Function Tools - Claude Function Calling Definitions
"""
from typing import Dict, List
from pydantic import BaseModel, Field

class SearchClientInput(BaseModel):
    """Input for search_client function"""
    company_name: str = Field(description="Company name to search for")

class GetAccountantInput(BaseModel):
    """Input for get_accountant function"""
    accountant_id: int = Field(description="Accountant ID")

class BookAppointmentInput(BaseModel):
    """Input for book_appointment function"""
    client_name: str = Field(description="Client name")
    accountant_name: str = Field(description="Accountant name")
    date: str = Field(description="Date in format YYYY-MM-DD")
    time: str = Field(description="Time in format HH:MM")

# Function definitions for Claude
FUNCTION_DEFINITIONS = [
    {
        "name": "search_client",
        "description": "Search for client in database by company name",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The company name to search for"
                }
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "get_office_hours",
        "description": "Get office opening hours",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    # Add more functions...
]