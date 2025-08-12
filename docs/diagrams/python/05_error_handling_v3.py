#!/usr/bin/env python3
"""Error Handling Matrix - Professional monitoring icons."""

from diagram_helpers import COLORS, cluster_style
from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.management import Cloudwatch, SystemsManager
from diagrams.aws.network import ElasticLoadBalancing
from diagrams.aws.security import Shield
from diagrams.aws.storage import SimpleStorageServiceS3Bucket as S3
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Nginx
from diagrams.programming.flowchart import StartEnd

with Diagram(
    "Error Handling Matrix",
    filename="05_error_handling_v3",
    show=False,
    direction="TB",
    graph_attr={
        "fontsize": "11",
        "bgcolor": "white",
        "pad": "0.5",
        "rankdir": "TB",
        "nodesep": "0.3",
        "ranksep": "0.5",
        "splines": "ortho",
    },
):
    # Request entry point
    request = StartEnd("Request")

    # Error Detection Points using proper service icons
    with Cluster("Detection Points", graph_attr=cluster_style("monitor")):
        auth_point = Shield("Auth")
        rate_point = ElasticLoadBalancing("Rate")
        validate_point = SystemsManager("Validate")
        llm_point = Lambda("LLM")
        storage_point = S3("Storage")

    # Error Responses using monitoring icons
    with Cluster("Client Errors", graph_attr=cluster_style("error")):
        err_400 = Nginx("400")
        err_401 = Shield("401")
        err_429 = ElasticLoadBalancing("429")

    with Cluster("Server Errors", graph_attr=cluster_style("api")):
        err_500 = Prometheus("500")
        err_503 = Grafana("503")

    # Response Monitoring
    with Cluster("Response Headers", graph_attr=cluster_style("monitor")):
        headers = Cloudwatch("Headers")
        request_id = SystemsManager("Request-ID")
        retry_after = Grafana("Retry-After")

        headers >> Edge(style="invis") >> request_id >> Edge(style="invis") >> retry_after

    # Retry Strategy (visual cascade)
    with Cluster("Retry Strategy", graph_attr=cluster_style("cache")):
        retry_1 = Lambda("1")
        retry_2 = Lambda("2")
        retry_3 = Lambda("3")

        # Exponential backoff shown visually
        retry_1 >> Edge(color=COLORS["warning"], style="dashed") >> retry_2
        retry_2 >> Edge(color=COLORS["warning"], style="dashed") >> retry_3

    # Connect detection points to errors with semantic colors
    # Auth → 401
    auth_point >> Edge(color=COLORS["error"], style="bold", penwidth="2") >> err_401

    # Rate → 429
    rate_point >> Edge(color=COLORS["warning"], style="bold", penwidth="2") >> err_429

    # Validation → 400
    validate_point >> Edge(color=COLORS["validate"], style="bold", penwidth="2") >> err_400

    # LLM → 503
    llm_point >> Edge(color=COLORS["external"], style="bold", penwidth="2") >> err_503

    # Storage → 503
    storage_point >> Edge(color=COLORS["database"], style="bold", penwidth="2") >> err_503

    # Any → 500 (rare, dotted)
    for point in [auth_point, rate_point, validate_point, llm_point, storage_point]:
        point >> Edge(color=COLORS["muted"], style="dotted", penwidth="1") >> err_500

    # Connect flow
    request >> auth_point
    auth_point >> Edge(color=COLORS["success"], penwidth="2") >> rate_point
    rate_point >> Edge(color=COLORS["success"], penwidth="2") >> validate_point
    validate_point >> Edge(color=COLORS["success"], penwidth="2") >> llm_point
    llm_point >> Edge(color=COLORS["success"], penwidth="2") >> storage_point

    # Server errors trigger retry
    err_503 >> Edge(color=COLORS["info"], style="dashed") >> retry_1

    # All errors include headers
    for err in [err_400, err_401, err_429, err_500, err_503]:
        err >> Edge(color=COLORS["muted"], style="dotted") >> headers
