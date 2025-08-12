#!/usr/bin/env python3
"""JWT Authentication Flow - Professional icons, no emojis."""

from diagram_helpers import (
    COLORS,
    auth_edge,
    cluster_style,
    error_edge,
    success_edge,
)
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.management import Cloudwatch
from diagrams.aws.network import ElasticLoadBalancing
from diagrams.aws.security import (
    CertificateManager,
    SecretsManager,
    Shield,
)
from diagrams.aws.security import (
    IdentityAndAccessManagementIam as IAM,
)
from diagrams.onprem.client import User
from diagrams.onprem.monitoring import Grafana
from diagrams.onprem.security import Trivy
from diagrams.programming.flowchart import InputOutput, StartEnd
from diagrams.programming.framework import FastAPI

with Diagram(
    "JWT Authentication Flow",
    filename="03_authentication_flow_v3",
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
    # JWT Token Structure (visual, no text)
    with Cluster("JWT Token", graph_attr=cluster_style("auth")):
        jwt_token = CertificateManager("JWT")
        secret_key = SecretsManager("Secret")
        jwt_token >> Edge(style="invis") >> secret_key

    # Login Flow (Token Creation)
    with Cluster("Login", graph_attr=cluster_style("api")):
        user = User("")
        login_endpoint = FastAPI("/login")
        token_generator = Lambda("Generate")
        token_response = CertificateManager("Token")

        user >> login_endpoint >> token_generator >> token_response
        token_generator >> auth_edge() >> jwt_token

    # Request Flow (Token Validation)
    with Cluster("API Request", graph_attr=cluster_style("business")):
        request = InputOutput("Request")

        # Validation chain using proper security icons
        auth_shield = Shield("")  # Has token?
        iam_check = IAM("")  # Valid format?
        trivy_validate = Trivy("")  # Signature valid?
        grafana_time = Grafana("")  # Not expired?
        cloudwatch = Cloudwatch("")  # Extract user_id

        # Success/Error endpoints
        success = StartEnd("OK")
        unauthorized = Shield("401")

    # Connect validation chain with colored edges (no labels)
    request >> auth_shield
    auth_shield >> success_edge() >> iam_check
    auth_shield >> error_edge() >> unauthorized

    iam_check >> success_edge() >> trivy_validate
    iam_check >> error_edge() >> unauthorized

    trivy_validate >> success_edge() >> grafana_time
    trivy_validate >> error_edge() >> unauthorized

    grafana_time >> success_edge() >> cloudwatch
    grafana_time >> error_edge() >> unauthorized

    cloudwatch >> success_edge() >> success
    cloudwatch >> error_edge() >> unauthorized

    # Protected Endpoint
    with Cluster("Protected", graph_attr=cluster_style("cache")):
        protected_api = FastAPI("/chat")
        rate_limiter = ElasticLoadBalancing("Rate")
        success >> Edge(color=COLORS["success"]) >> rate_limiter >> protected_api
