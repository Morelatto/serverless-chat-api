#!/usr/bin/env python3
"""JWT Authentication Flow - Detailed token validation process."""

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.blank import Blank
from diagrams.onprem.client import User
from diagrams.programming.flowchart import (
    Action,
    Decision,
    Document,
    InputOutput,
    StartEnd,
)

COLORS = {
    "success": "#28a745",
    "error": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8",
    "security": "#6f42c1",
}

with Diagram(
    "JWT Authentication Flow",
    filename="03_authentication_flow",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "12",
        "bgcolor": "white",
        "pad": "0.5",
        "splines": "ortho",
        "ranksep": "1.0",
    },
):
    # Actors
    user = User("User")

    # Start/End points
    start = StartEnd("Request Arrives")
    authenticated = StartEnd("Authenticated")
    rejected = StartEnd("Rejected")

    # Input/Output
    login_request = InputOutput("POST /login\n{user_id: str}")
    token_response = InputOutput("Response:\n{access_token,\ntoken_type: 'bearer'}")
    api_request = InputOutput("Request with\nAuthorization Header")

    # Decision points
    has_header = Decision("Has Auth\nHeader?")
    is_bearer = Decision("Bearer\nScheme?")
    token_valid = Decision("Token\nValid?")
    not_expired = Decision("Not\nExpired?")
    has_sub = Decision("Has 'sub'\nClaim?")

    # Processing actions
    create_token = Action(
        "create_token(user_id)\n- Set 'sub' = user_id\n- Set 'exp' = now + 30min\n- Set 'iat' = now"
    )
    encode_jwt = Action("jwt.encode()\n- Algorithm: HS256\n- Secret: from config")
    extract_header = Action("Extract\nAuthorization")
    remove_bearer = Action("Remove 'Bearer '\nPrefix")
    decode_token = Action("jwt.decode()\n- Verify signature\n- Check algorithm")
    extract_user = Action("Extract user_id\nfrom 'sub' claim")

    # Error documents
    missing_header = Document("401 Unauthorized\nNo Authorization")
    invalid_scheme = Document("401 Unauthorized\nNot Bearer")
    invalid_token = Document("401 Unauthorized\nInvalid Token")
    expired_token = Document("401 Unauthorized\nToken Expired")
    missing_sub = Document("401 Unauthorized\nNo User ID")

    # Security components
    with Cluster("JWT Components"):
        jwt_header = Blank("Header:\n{alg: 'HS256',\ntyp: 'JWT'}")
        jwt_payload = Blank("Payload:\n{sub: user_id,\nexp: timestamp,\niat: timestamp}")
        jwt_signature = Blank("Signature:\nHMAC-SHA256")

    # Login flow (token creation)
    with Cluster("Token Creation (/login endpoint)", graph_attr={"bgcolor": "#e8f5e9"}):
        user >> login_request >> create_token
        create_token >> encode_jwt
        encode_jwt >> Edge(style="dashed") >> jwt_header
        encode_jwt >> Edge(style="dashed") >> jwt_payload
        encode_jwt >> Edge(style="dashed") >> jwt_signature
        encode_jwt >> token_response >> user

    # Blank separator
    blank = Blank("")

    # API request flow (token validation)
    with Cluster("Token Validation (all protected endpoints)", graph_attr={"bgcolor": "#fff3e0"}):
        start >> api_request >> extract_header >> has_header

        # Check header exists
        has_header >> Edge(label="No", color=COLORS["error"]) >> missing_header >> rejected
        has_header >> Edge(label="Yes", color=COLORS["success"]) >> is_bearer

        # Check Bearer scheme
        is_bearer >> Edge(label="No", color=COLORS["error"]) >> invalid_scheme >> rejected
        is_bearer >> Edge(label="Yes", color=COLORS["success"]) >> remove_bearer

        # Decode token
        remove_bearer >> decode_token
        decode_token >> token_valid

        # Validate token
        token_valid >> Edge(label="No", color=COLORS["error"]) >> invalid_token >> rejected
        token_valid >> Edge(label="Yes", color=COLORS["success"]) >> not_expired

        # Check expiration
        not_expired >> Edge(label="No", color=COLORS["error"]) >> expired_token >> rejected
        not_expired >> Edge(label="Yes", color=COLORS["success"]) >> has_sub

        # Check user claim
        has_sub >> Edge(label="No", color=COLORS["error"]) >> missing_sub >> rejected
        has_sub >> Edge(label="Yes", color=COLORS["success"]) >> extract_user

        # Success
        extract_user >> authenticated

    # Protected endpoint example
    with Cluster("Usage in Endpoints", graph_attr={"bgcolor": "#f0f8ff"}):
        endpoint_def = Document(
            "@app.post('/chat')\nasync def chat_endpoint(\n  content: str = Body(...),\n  user_id: str = Depends(get_current_user)\n)"
        )
        authenticated >> Edge(label="user_id available", color=COLORS["info"]) >> endpoint_def
