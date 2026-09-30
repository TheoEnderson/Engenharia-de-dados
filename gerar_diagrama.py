import os
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.database import PostgreSQL, MongoDB
from diagrams.programming.framework import Flask
from diagrams.programming.language import Python
from diagrams.aws.analytics import Redshift
from diagrams.onprem.analytics import Metabase

os.makedirs("docs", exist_ok=True)

with Diagram("Arquitetura", show=False, filename="docs/arquitetura", direction="TB"):
    with Cluster("Camada Operacional (OLTP)"):
        app_pg = Flask("Portal Acadêmico")
        pg_db = PostgreSQL("PostgreSQL\nRelacional/Normalizado")
        
        app_mdb = Flask("Sistema de Admissões")
        mongo_db = MongoDB("MongoDB\nNoSQL/Documentos")
        
        app_pg >> Edge(label="Leitura/Escrita") >> pg_db
        app_mdb >> Edge(label="Leitura/Escrita") >> mongo_db

    with Cluster("Camada de Ingestão e Processamento (ETL)"):
        py_etl = Python("Python / Pandas\nScripts ETL")
        hop_etl = Python("Apache Hop\nPipelines .hpl")

    with Cluster("Camada Analítica (OLAP)"):
        dw = Redshift("Data Warehouse\nStar / Snowflake Schema")
        bi = Metabase("Consultas OLAP &\nDashboards Analíticos")

    pg_db >> Edge(label="Extração") >> py_etl
    pg_db >> Edge(label="Extração") >> hop_etl
    mongo_db >> Edge(label="Extração") >> py_etl
    
    py_etl >> Edge(label="Carga Dimensional") >> dw
    hop_etl >> Edge(label="Carga de Fatos") >> dw
    
    dw >> Edge(label="Consumo Analítico") >> bi