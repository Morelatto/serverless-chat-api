#!/usr/bin/env python3
"""JWT Authentication - YOUR ACTUAL Implementation."""

from custom_icons import (
    JWT,
    DictCache,
    FastAPI,
    Handler,
    Jose,
    Middleware,
    Pydantic,
    Slowapi,
)
from diagram_helpers import COLORS, cluster_style
from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import User
from diagrams.programming.language import Python

with Diagram(
    "JWT Authentication - Actual Implementation",
    filename="03_authentication_flow_real",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.3",
        "nodesep": "0.4",
        "ranksep": "0.8",
        "splines": "ortho",
    },
):
    # User/Client
    user = User("Client")

    # Login Flow - What ACTUALLY happens in your code
    with Cluster("Login Endpoint (No Password!)", graph_attr=cluster_style("auth")):
        login_endpoint = FastAPI("/login")
        create_token_func = Python("create_token()")
        jose_lib = Jose("python-jose")
        jwt_token = JWT("30min token")

        # Your actual flow: user_id → create_token() → JWT
        user >> login_endpoint
        login_endpoint >> create_token_func
        create_token_func >> jose_lib
        jose_lib >> jwt_token

    # Chat Request Flow - Your REAL implementation
    with Cluster("Protected /chat Endpoint", graph_attr=cluster_style("api")):
        chat_request = FastAPI("/chat")
        slowapi_limit = Slowapi("@limiter")
        depends = Python("Depends()")
        get_current_user = Middleware("get_current_user()")

        # Your actual middleware chain
        user >> Edge(label="Bearer token") >> chat_request
        chat_request >> slowapi_limit
        slowapi_limit >> depends
        depends >> get_current_user

    # Token Validation - What YOUR code does
    with Cluster("JWT Validation (middleware.py)", graph_attr=cluster_style("business")):
        extract_bearer = Python("Header()")
        decode_jwt = Jose("jwt.decode()")
        validate_exp = Python("check exp")
        extract_user = Python("payload['sub']")

        # Your actual validation steps
        get_current_user >> extract_bearer
        extract_bearer >> decode_jwt
        decode_jwt >> validate_exp
        validate_exp >> extract_user

    # Error Handling - YOUR exception classes
    with Cluster("Your Error Handlers", graph_attr=cluster_style("error")):
        unauthorized = Handler("AuthError\n401")
        rate_limited = Handler("RateLimit\n429")
        validation_err = Pydantic("ValidationError\n422")

        # Your actual error paths
        extract_bearer >> Edge(color=COLORS["error"], label="No token") >> unauthorized
        decode_jwt >> Edge(color=COLORS["error"], label="Invalid") >> unauthorized
        validate_exp >> Edge(color=COLORS["error"], label="Expired") >> unauthorized
        slowapi_limit >> Edge(color=COLORS["warning"], label="Too many") >> rate_limited

    # Success Path
    with Cluster("Process Request", graph_attr=cluster_style("cache")):
        chat_service = Python("ChatService")
        cache_check = DictCache("in-memory")

        extract_user >> Edge(color=COLORS["success"]) >> chat_service
        chat_service >> cache_check
